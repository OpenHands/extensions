"""Select requested PR heads and delegate each review to a sandboxed agent."""

import json
import os
import sys
from functools import cached_property
from urllib.parse import quote

import main as workflow
from agent_conversation import AgentConversationDispatcher
from github_client import GitHubRepository, run_repositories
from maintainer_handoff import (
    HandoffConfigurationError,
    parse_maintainers,
    request_maintainer_review,
)

# The head-eligibility gate. Scheduled discovery classifies only the checks
# GitHub reports as required for the pull request, read through the GraphQL
# `isRequired` signal, so an optional workflow that fails before creating any
# check run cannot block a head whose required checks pass. An explicit
# `all-hands-bot` review request is the intake-policy exception and bypasses the
# gate entirely. A completed required run blocks unless its conclusion is
# explicitly non-blocking, so an unrecognized conclusion fails closed rather than
# approving silently, and a required run that has not completed means waiting,
# never approval. When the required set cannot be read, the gate falls back to
# every current-head check and workflow run, so a red head still blocks.
CHECK_GATE_MARKER = "<!-- openhands-review-gate:"
NON_BLOCKING_CHECK_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})
# The gate is deterministic; this disclosure is what tells a reader no model ran.
WORKFLOW_DISCLOSURE = "no AI was used to generate this comment"


class ReviewIntake:
    """The per-scan bound on new review conversations, shared across repositories.

    A scheduled scan drains every eligible pull request, but starting an agent
    for each one at once exhausted the OSS Agent Canvas VM, so a small maximum
    caps what a single scan may start. The maximum is per scan and shared by
    every configured repository rather than reset per repository, and it bounds
    the conversations a scan *starts*: a delivery that only deduplicates, or
    reports an already-running conversation, reuses a runtime and consumes no
    slot. Candidates are drained oldest reviewer-request first, then by
    repository and pull-request number, so a scan over more candidates than the
    maximum allows starts the oldest and a later scan reaches the remainder.
    """

    def __init__(self):
        # The budget lives on the intake so a scan that drains repository by
        # repository still counts its conversations against one shared maximum.
        self._pending = []
        self._maximum = None
        self._started = 0

    def register(self, record):
        """Queue one eligible candidate for this scan's bounded drain."""
        self._pending.append(record)

    def drain(self):
        """Start the oldest pending conversations, up to the per-scan maximum.

        The budget is held on the intake, so a scan that drains repository by
        repository still counts its conversations against one shared maximum. A
        candidate whose dispatch raises is reported and skipped without
        consuming a slot, so the candidates behind it are still considered.
        """
        pending, self._pending = self._pending, []
        if not pending:
            return
        if self._maximum is None:
            self._maximum = pending[0]["config"].get(
                "max_new_per_run", workflow.MAX_NEW_PER_RUN
            )
        failures = []
        for record in sorted(
            pending,
            key=lambda item: (
                item["created_at"],
                item["repository"],
                item["number"],
            ),
        ):
            if self._started >= self._maximum:
                break
            try:
                result = record["start"]()
            except Exception as exc:  # noqa: BLE001 - one PR must not block the scan
                failures.append(record["number"])
                print(
                    f"Failed to submit {record['repository']} PR "
                    f"#{record['number']}: {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
                continue
            if result["disposition"] == "created":
                self._started += 1
        if failures:
            raise RuntimeError(
                "Reviewer scan failed for PRs: "
                + ", ".join(f"#{number}" for number in failures)
            )


class PullRequestReviewer(GitHubRepository):
    name = "github-pr-reviewer"
    # The shared intake the shipped entrypoint creates once per scheduled scan,
    # so the per-run maximum spans every configured repository. It is None for a
    # run() invoked on its own (tests, one-off scans), which then bounds its own
    # conversations with a private intake instead.
    scan_intake = None

    @property
    def intake(self):
        """The intake this run registers eligible candidates with.

        The shipped entrypoint sets `scan_intake` once, so every repository in a
        scan shares one budget and the drain happens after all repositories have
        been scanned. A run() with no shared intake uses its own, created lazily
        so it exists whether or not __init__ ran.
        """
        if self.scan_intake is not None:
            return self.scan_intake
        intake = self.__dict__.get("_intake")
        if intake is None:
            intake = self.__dict__["_intake"] = ReviewIntake()
        return intake

    @cached_property
    def github_login(self):
        return self.api("GET", "/user")["login"]

    @cached_property
    def trigger_reviewer(self):
        return self.config.get("trigger_reviewer", "all-hands-bot").lower()

    @staticmethod
    def _event_payload():
        """Return the GitHub webhook payload, or None for a scheduled run."""
        raw = os.environ.get("AUTOMATION_EVENT_PAYLOAD")
        if not raw:
            return None
        outer = json.loads(raw)
        payload = (outer.get("event") or {}).get("payload")
        return payload if isinstance(payload, dict) else None

    def _latest_reviewer_request(self, number):
        matching = [
            event
            for event in self.gh_pages(f"/issues/{number}/events")
            if event.get("event") == "review_requested"
            and ((event.get("requested_reviewer") or {}).get("login") or "").lower()
            == self.trigger_reviewer
            and event.get("id") is not None
        ]
        if not matching:
            return None
        return max(
            matching,
            key=lambda event: (
                event.get("created_at") or "",
                int(event.get("id") or 0),
            ),
        )

    def _event_candidate(self, payload):
        repository = ((payload.get("repository") or {}).get("full_name") or "")
        if repository.lower() != self.repository.lower():
            return None
        pr = payload.get("pull_request")
        if not isinstance(pr, dict) or pr.get("number") is None:
            return None
        action = payload.get("action")
        if action == "review_requested":
            requested = (
                (payload.get("requested_reviewer") or {}).get("login") or ""
            ).lower()
            return pr if requested == self.trigger_reviewer else None
        if action == "submitted":
            author = ((payload.get("review") or {}).get("user") or {}).get("login")
            return pr if (author or "").lower() == self.trigger_reviewer else None
        return None

    def _prompt(self, pr, trigger, label=None):
        number = pr["number"]
        sha = pr["head"]["sha"]
        token = self.token_name
        workspace = (
            "The workspace contains an empty Git repository. Before fetching, run "
            f"`GH_TOKEN=${{{token}}} gh auth setup-git` so Git uses the "
            "profile-scoped credential without storing it in the remote URL. Set "
            f"the plain HTTPS origin to `https://github.com/{self.repository}.git`, "
            f"fetch PR #{number}, and check out exact head `{sha}` in detached-HEAD "
            "mode. Set `GIT_TERMINAL_PROMPT=0` on Git network commands so a missing "
            "permission fails immediately instead of waiting for input."
        )
        prompt = workflow._build_review_prompt(
            self.repository,
            pr,
            sha,
            trigger,
            workspace_instructions=workspace,
            github_token_secret=token,
            trigger_description=(
                None
                if label
                else (
                    f"latest review request for "
                    f"`{self.trigger_reviewer}` "
                    f"event {trigger.get('id', '?')} at "
                    f"{trigger.get('created_at', '?')}"
                )
            ),
        )
        moved_head_instruction = (
            f"leave `{label}` in place so the new head is reviewed"
            if label
            else "publish no review; the new head requires another reviewer request"
        )
        trigger_completion = (
            f"Leave the `{label}` label in place after GitHub accepts the review. "
            "The deterministic scanner removes it"
            if label
            else "Do not change review requests after GitHub accepts the review. "
            "The deterministic event handler completes the request"
        )
        return (
            prompt + "\n\nAcceptance reporting:\n"
            "- Inspect the current GitHub Actions results for the exact head and run "
            "the repository's appropriate focused tests in the workspace. Do not "
            "modify tracked files.\n"
            f"- Re-read {self.repository} PR #{number} immediately before reporting. "
            "Confirm its current body, labels, review threads, and the head's check "
            "results, and re-read every linked issue's current body and labels: an "
            "issue's readiness or priority may have changed since an earlier turn. "
            f"If the head is no longer `{sha}`, {moved_head_instruction}.\n"
            f"- {trigger_completion} after completing any configured "
            "human-review handoff. Never paste JSON artifacts or full command logs "
            "into comments.\n"
            "- Once GitHub accepts the native review, stop immediately. Do not "
            "continue inspecting the repository, run more commands, or publish a "
            "second result."
        )

    def _finish_completed_review(self, pr, trigger, label=None):
        """Complete an exact-head review, including an optional human handoff."""
        head_sha = pr["head"]["sha"]
        triggered_at = trigger.get("created_at") or ""
        reviews = self.gh_pages(f"/pulls/{pr['number']}/reviews")
        completed = [
            review
            for review in reviews
            if review.get("commit_id") == head_sha
            and ((review.get("user") or {}).get("login") or "").lower()
            == self.github_login.lower()
            and (review.get("submitted_at") or "") > triggered_at
        ]
        if not completed:
            return False
        approved = None
        maintainer_decision = False
        for review in sorted(
            completed, key=lambda item: item["submitted_at"], reverse=True
        ):
            body = (review.get("body") or "").rstrip()
            if body.endswith("✅ APPROVED"):
                approved = True
                break
            if body.endswith("🔄 CHANGES REQUESTED"):
                approved = False
                break
            if body.endswith(workflow.MAINTAINER_DECISION_VERDICT):
                maintainer_decision = True
                break
        if approved is None and not maintainer_decision:
            return False
        # A scope stop is not an approval: it requests the maintainer decision
        # the change is missing, through the same handoff as an approval.
        if approved or maintainer_decision:
            maintainers = parse_maintainers(self.config.get("maintainers"))
            if maintainers:
                try:
                    selected = request_maintainer_review(self, pr, maintainers)
                except HandoffConfigurationError as exc:
                    self.gh(
                        "POST",
                        f"/issues/{pr['number']}/comments",
                        {
                            "body": (
                                "⚠️ **Automated maintainer handoff could not be "
                                f"completed:** {exc}. Update the automation's "
                                "maintainer roster, then request another review."
                                "\n\n_This is an automated configuration check; "
                                "no AI was used to generate this comment._"
                            )
                        },
                    )
                    selected = None
                print(
                    json.dumps(
                        {
                            "repository": self.repository,
                            "pr": pr["number"],
                            "human_reviewer": selected,
                        }
                    ),
                    flush=True,
                )
        current = self.gh("GET", f"/pulls/{pr['number']}")
        if current["head"]["sha"] != pr["head"]["sha"]:
            # Treat this scan as handled so it cannot redeliver the stale head.
            # Scheduled mode leaves its label in place; event mode requires a
            # fresh review request for the new head.
            return True
        if label:
            self.gh(
                "DELETE", f"/issues/{pr['number']}/labels/{quote(label, safe='')}"
            )
        return True

    @staticmethod
    def _check_app_identity(run):
        """The app that reported a check run, as a stable grouping key."""
        app = run.get("app") or {}
        if isinstance(app, dict):
            return str(app.get("slug") or app.get("id") or app.get("name") or "")
        return str(app)

    @staticmethod
    def _check_run_order(run):
        """Deterministic ordering by run ID, then start time as a tie-break.

        The check-run ID is a monotonically increasing per-repository counter,
        so it tracks creation order even when `started_at` is absent, and it is
        the primary key. Ordering by start time first broke in both directions:
        a missing start time sorted before every real timestamp (an older queued
        run lost to an earlier success), and the earlier `~{run_id}` fallback
        sorted after every real timestamp (an older queued run outranked a newer
        success). The start time only breaks a tie when two runs share an ID or
        have none.
        """
        run_id = int(run.get("id") or 0)
        return (run_id, run.get("started_at") or "")

    @staticmethod
    def _workflow_run_order(run):
        """Deterministic ordering for workflow runs, keyed by run ID first.

        Workflow-run IDs are the same monotonic per-repository counter as
        check-run IDs, so the ID is again the primary key. The start time lives
        in `run_started_at` (`created_at` before the run starts) and only breaks
        a tie.
        """
        run_id = int(run.get("id") or 0)
        return (run_id, run.get("run_started_at") or run.get("created_at") or "")

    @staticmethod
    def _latest_by_group(runs, sha, order, group):
        """Keep the latest run per group, ignoring any other head's runs.

        GitHub lists every run for a commit, so a check that was re-run after a
        fix would otherwise contribute its superseded failure forever. Only runs
        attributed to the exact head count: a run left behind on an obsolete head
        must not block the push that fixed it. Within a group the latest run
        wins, ordered by the run ID (the reliable creation sequence) with the
        start time as a tie-break, so a newer queued or in-progress re-run
        supersedes an earlier success and makes the head wait even when its start
        time is still absent, while an older run without a start time cannot
        outrank a newer success.
        """
        latest = {}
        for run in runs:
            if run.get("head_sha") != sha:
                continue
            key = group(run)
            current = latest.get(key)
            if current is None or order(run) > order(current):
                latest[key] = run
        return list(latest.values())

    def _latest_check_runs(self, sha, check_runs):
        """Return only the latest run of each logical check on the exact head.

        A logical check is its name plus the reporting app identity, so two apps
        that use the same name stay independent.
        """
        return self._latest_by_group(
            check_runs,
            sha,
            self._check_run_order,
            lambda run: (
                run.get("name") or "unnamed check",
                self._check_app_identity(run),
            ),
        )

    def _latest_workflow_runs(self, sha, check_runs):
        """Return the current-head workflow runs that created no check runs.

        A workflow run's check suite is the link to its check runs. When that
        suite already reported check runs, those runs carry the conclusion and
        re-reporting the workflow run would only duplicate them. A suite with no
        check runs is a workflow that failed before any job reported - a
        workflow-level error, or a `pull_request` run whose jobs never started -
        which the commit's check-run rollup and `gh pr check`s cannot see. Group
        by workflow identity so a re-run supersedes its earlier attempt.
        """
        reported_suites = {
            (run.get("check_suite") or {}).get("id")
            for run in check_runs
            if run.get("head_sha") == sha
        }
        return self._latest_by_group(
            [
                run
                for run in self.workflow_runs(sha)
                if run.get("check_suite_id") not in reported_suites
            ],
            sha,
            self._workflow_run_order,
            lambda run: (
                run.get("name") or "unnamed workflow",
                run.get("workflow_id"),
            ),
        )

    @staticmethod
    def _classify_runs(reporters):
        """Split runs into blocking, pending, and green by status/conclusion.

        A completed run whose conclusion is neither blocking nor explicitly
        non-blocking fails closed, so an unknown conclusion cannot silently
        approve a PR. A run that has not completed means waiting, never
        approval.
        """
        blocking, pending = [], []
        for run in reporters:
            name = run.get("name") or "unnamed check"
            status = (run.get("status") or "").lower()
            if status != "completed":
                pending.append(name)
            elif (run.get("conclusion") or "").lower() in NON_BLOCKING_CHECK_CONCLUSIONS:
                continue
            else:
                blocking.append(name)
        if blocking:
            return "blocked", sorted(set(blocking))
        if pending:
            return "waiting", sorted(set(pending))
        return "green", []

    def _classify_all_runs(self, sha):
        """Every current-head check and workflow run, regardless of requirement.

        The conservative fallback used when the required-check set cannot be
        read. Check runs are the primary signal, but a workflow can fail before
        creating any check run, so workflow runs whose suites reported no check
        runs are considered too.
        """
        check_runs = self.check_runs(sha)
        reporters = (
            self._latest_check_runs(sha, check_runs)
            + self._latest_workflow_runs(sha, check_runs)
        )
        return self._classify_runs(reporters)

    def _classify_required_runs(self, sha, required):
        """Classify only the required current-head checks.

        `required` is the required contexts GitHub reports for the pull request.
        Only a required check decides the scheduled gate, so an optional workflow
        that fails before creating any check run - and whose context GitHub does
        not mark required - cannot block a head whose required checks pass. A
        required context that reported no current-head check run, such as a
        required workflow that failed before any job, is expected but unfulfilled
        and classifies as waiting.
        """
        check_runs = self.check_runs(sha)
        latest = {
            (run.get("name") or "unnamed check"): run
            for run in self._latest_check_runs(sha, check_runs)
        }
        reporters = []
        for context in required:
            name = context["name"]
            if context.get("kind") == "StatusContext":
                state = self.statuses(sha).get(name)
                reporters.append(
                    {
                        "name": name,
                        "status": "completed" if state else "expected",
                        "conclusion": state,
                    }
                )
                continue
            reporters.append(latest.get(name, {"name": name, "status": "expected"}))
        return self._classify_runs(reporters)

    def _classify_check_runs(self, pr):
        """Split a pull request head into blocked, waiting, or green.

        Scheduled discovery classifies only GitHub-required checks, because an
        optional workflow must not block the merge gate. The required set is read
        per pull request; when it is unavailable or empty the classifier falls
        back to every current-head check and workflow run, so a red head still
        blocks. The exact-head, latest-run, and fail-closed behavior is identical
        either way.
        """
        sha = pr["head"]["sha"]
        try:
            required = self.required_check_contexts(pr["number"])
        except Exception as exc:  # noqa: BLE001 - fail closed to the full rollup
            print(
                json.dumps(
                    {
                        "repository": self.repository,
                        "pr": pr["number"],
                        "head_sha": sha,
                        "required_check_signal": "unavailable",
                        "error": type(exc).__name__,
                    }
                ),
                flush=True,
            )
            return self._classify_all_runs(sha)
        if not required:
            # No required checks configured is not a red head, but it is also not
            # evidence the head is reviewable, so fall back to the full rollup.
            return self._classify_all_runs(sha)
        return self._classify_required_runs(sha, required)

    def _owns_comment(self, comment):
        login = ((comment.get("user") or {}).get("login") or "").lower()
        return login == self.github_login.lower()

    @staticmethod
    def _explains_checks(body, names):
        """Whether a deterministic comment names every check the gate reports."""
        lowered = body.lower()
        return all(name.lower() in lowered for name in names)

    def _gate_comment(self, number, marker, body, names):
        """Post one gate explanation, upserting the automation's own comment.

        The marker carries the head SHA and gate category, so a later run for a
        different head updates the comment it owns instead of stacking another
        one. A run that finds the same marker still compares the full body, so a
        comment written for one deployment is reworded in place when the retry it
        names changes -- an event-only gate comment becomes the scheduled one when
        the automation is switched to cron -- and an unchanged body is a no-op.
        Every PR comment is untrusted input: only a marker this account authored
        is "managed", so a marker someone else placed can neither suppress the
        explanation nor be edited. An unmarked deterministic comment an existing
        repository workflow already posted is treated as the equivalent
        explanation only when it names the same reported checks; a comment about
        some other check is left alone and the gate posts its own.
        """
        comments = self.gh_pages(f"/issues/{number}/comments")
        managed = [
            comment
            for comment in comments
            if CHECK_GATE_MARKER in (comment.get("body") or "")
            and self._owns_comment(comment)
        ]
        matching = [
            comment for comment in managed if marker in (comment.get("body") or "")
        ]
        if matching:
            target = max(matching, key=lambda comment: int(comment["id"]))
            if (target.get("body") or "").strip() == body.strip():
                return None
            self.gh("PATCH", f"/issues/comments/{target['id']}", {"body": body})
            return target["id"]
        if managed:
            target = max(managed, key=lambda comment: int(comment["id"]))
            self.gh("PATCH", f"/issues/comments/{target['id']}", {"body": body})
            return target["id"]
        if any(
            WORKFLOW_DISCLOSURE.lower() in (comment.get("body") or "").lower()
            and self._explains_checks(comment.get("body") or "", names)
            for comment in comments
            if CHECK_GATE_MARKER not in (comment.get("body") or "")
        ):
            return None
        created = self.gh("POST", f"/issues/{number}/comments", {"body": body})
        return created.get("id")

    def _gate_body(self, sha, state, names, scheduled):
        """Explain a stop, naming the retry this deployment actually has.

        A scheduled run proves a scan is configured, so it may promise the next
        scan. An event run does not, so it names the one mechanism this
        deployment is guaranteed to honor: another native review request. GitHub
        refuses to request a reviewer who is already requested, so an event-only
        deployment must say that the outstanding request has to be removed and
        re-requested before the review can start.
        """
        short = sha[:12]
        listed = "\n".join(f"- `{name}`" for name in names)
        if state == "blocked":
            heading = "### ⚠️ Review paused: current-head checks failed"
            lead = (
                f"The current head `{short}` has failing checks, so no review "
                "conversation was started:"
            )
            action = (
                "Fix the checks above and push. The scheduled scan then starts "
                "the review on the updated head."
                if scheduled
                else "Fix the checks above and push. Then remove the outstanding "
                f"`{self.trigger_reviewer}` request and request "
                f"`{self.trigger_reviewer}` again: GitHub will not accept a "
                "second request while the first is still outstanding. The review "
                "starts on the updated head."
            )
        else:
            heading = "### ⏳ Review waiting on checks"
            lead = (
                f"The current head `{short}` still has checks that have not "
                "finished, so no review conversation was started:"
            )
            action = (
                "No action is needed. The scheduled scan retries once every "
                "check on the head reports a conclusion."
                if scheduled
                else "Once every check on the head reports a conclusion, remove "
                f"the outstanding `{self.trigger_reviewer}` request and request "
                f"`{self.trigger_reviewer}` again: GitHub will not accept a "
                "second request while the first is still outstanding. That "
                "starts the review."
            )
        return (
            f"{heading}\n\n{lead}\n\n{listed}\n\n{action}\n\n"
            f"{CHECK_GATE_MARKER}{state}:{sha} -->\n\n"
            f"_This is an automated check - {WORKFLOW_DISCLOSURE}._"
        )

    def _gate_head(self, pr, requested=False, scheduled=False):
        """Return the head's eligibility, explaining any stop on the PR.

        An explicit `all-hands-bot` review request is the intake-policy
        exception: the caller asked for this head by name, so the CI gate does
        not apply and no gate comment is left. Scheduled discovery still gates on
        the required checks. When it stops a scheduled run, the explanation names
        the retry that deployment actually has, which is why `scheduled` is
        threaded into the body.
        """
        sha = pr["head"]["sha"]
        if requested:
            return "green", sha
        state, names = self._classify_check_runs(pr)
        if state in ("blocked", "waiting"):
            marker = f"{CHECK_GATE_MARKER}{state}:{sha} -->"
            self._gate_comment(
                pr["number"],
                marker,
                self._gate_body(sha, state, names, scheduled),
                names,
            )
        return state, sha

    def _outstanding_review_request(self, pr):
        """Whether an open, non-draft PR still holds a request for the reviewer.

        The list endpoint already answers this: `requested_reviewers` is the live
        set, so a review that was submitted, or a request that was withdrawn, is
        simply absent. Drafts are excluded because a draft is not reviewable.
        """
        if pr.get("draft"):
            return False
        return any(
            (item.get("login") or "").lower() == self.trigger_reviewer
            for item in pr.get("requested_reviewers") or []
        )

    def run(self):
        repository_id = self.gh("GET", "")["id"]
        label = self.config.get("trigger_label", workflow.TRIGGER_LABEL)
        payload = self._event_payload()
        if payload is None:
            prs = self.gh_pages("/pulls?state=open&sort=updated&direction=asc")
        else:
            candidate = self._event_candidate(payload)
            if candidate and self.github_login.lower() != self.trigger_reviewer:
                raise RuntimeError(
                    "The configured GitHub credential must authenticate as "
                    f"{self.trigger_reviewer} for reviewer-request mode"
                )
            prs = [candidate] if candidate else []
        failures = []
        for candidate in prs:
            event_mode = payload is not None
            if not event_mode and label not in {
                item["name"] for item in candidate.get("labels", [])
            } and not self._outstanding_review_request(candidate):
                # A scheduled scan covers the trigger label and any PR that still
                # holds a review request the CI gate deferred. Everything else is
                # not ours to review.
                continue
            try:
                pr = self.gh("GET", f"/pulls/{candidate['number']}")
                has_label = label in {
                    item["name"] for item in pr.get("labels", [])
                }
                if event_mode or has_label:
                    trigger = (
                        self._latest_reviewer_request(pr["number"])
                        if event_mode
                        else workflow._latest_trigger_label_event(
                            self.token, self.repository, pr["number"]
                        )
                    )
                else:
                    # The outstanding request is the trigger, so its own event
                    # keys the delivery and dedupes repeated scans.
                    trigger = self._latest_reviewer_request(pr["number"])
                if trigger is None:
                    continue
                trigger_label = label if (not event_mode and has_label) else None
                if self._finish_completed_review(pr, trigger, trigger_label):
                    continue
                if event_mode and payload.get("action") == "submitted":
                    # A submitted review is a completion signal, never a fresh
                    # trigger. A non-decisive review, or one superseded by a new
                    # head, must wait for another reviewer request instead of
                    # dispatching a review the caller never asked for.
                    continue
                sha = pr["head"]["sha"]
                gate_state, sha = self._gate_head(
                    pr, requested=event_mode, scheduled=not event_mode
                )
                if gate_state != "green":
                    # A deterministic blocker stops the run without spending a
                    # worker slot on an agent. The trigger is not consumed: the
                    # next scheduled scan or explicit request re-evaluates the
                    # head once its checks are non-blocking.
                    print(
                        json.dumps(
                            {
                                "repository": self.repository,
                                "pr": pr["number"],
                                "head_sha": sha,
                                "disposition": f"review-{gate_state}",
                            }
                        ),
                        flush=True,
                    )
                    continue
                record = {
                    "repository": self.repository,
                    "number": pr["number"],
                    # The oldest outstanding request drains first; repository and
                    # number break a tie so the order is deterministic.
                    "created_at": trigger.get("created_at") or "",
                    "config": self.config,
                    "start": lambda pr=pr, trigger=trigger, sha=sha,
                    trigger_label=trigger_label: self._start_review(
                        repository_id, pr, trigger, sha, trigger_label
                    ),
                }
                if event_mode:
                    # An explicit request is a caller's decision to spend a
                    # conversation now, not a backlog item, so the event path
                    # dispatches immediately and is never bounded by the
                    # scheduled scan's per-run maximum.
                    self._start_review(
                        repository_id, pr, trigger, sha, trigger_label
                    )
                else:
                    self.intake.register(record)
            except Exception as exc:  # noqa: BLE001 - one PR must not block the scan
                failures.append(candidate.get("number", "?"))
                print(
                    f"Failed to submit {self.repository} PR "
                    f"#{candidate.get('number', '?')}: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
        if self.scan_intake is None:
            # A run() with no shared scan intake owns its whole scan, so it
            # drains the candidates it collected, bounded by the per-run maximum.
            self.intake.drain()
        if failures:
            raise RuntimeError(
                "Reviewer scan failed for PRs: "
                + ", ".join(f"#{number}" for number in failures)
            )

    def _start_review(self, repository_id, pr, trigger, sha, trigger_label):
        result = self.dispatcher.deliver(
            subject=f"{repository_id}:pr:{pr['number']}",
            delivery=f"{trigger['id']}:{sha}",
            prompt=self._prompt(pr, trigger, trigger_label),
        )
        print(
            json.dumps(
                {
                    "repository": self.repository,
                    "pr": pr["number"],
                    "head_sha": sha,
                    "disposition": result["disposition"],
                    "conversation_id": result["conversation_id"],
                }
            ),
            flush=True,
        )
        return result


def run_scan(dispatcher):
    """Run one scheduled scan over every configured repository, then drain.

    One shared intake spans the whole scan, so the per-run maximum is global
    rather than reset per repository, and the drain happens after every
    repository has been scanned so the oldest outstanding request across all of
    them starts first. One repository failing must not discard another
    repository's drained candidates, so the drain still runs and the first
    failure is what the scan reports.
    """
    PullRequestReviewer.scan_intake = ReviewIntake()
    failure = None
    try:
        run_repositories(PullRequestReviewer, dispatcher=dispatcher)
    except Exception as exc:  # noqa: BLE001 - reported after the drain
        failure = exc
    try:
        PullRequestReviewer.scan_intake.drain()
    except Exception as exc:  # noqa: BLE001 - reported after the scan failure
        failure = failure or exc
    if failure is not None:
        raise failure


if __name__ == "__main__":
    with AgentConversationDispatcher() as dispatcher:
        run_scan(dispatcher)
