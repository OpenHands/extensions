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

# The head-eligibility gate. It reads the check runs GitHub already reports for
# the exact head, so it needs no branch-protection or ruleset access and no
# maintained list of check names. A completed run blocks unless its conclusion is
# explicitly non-blocking, so an unrecognized conclusion fails closed rather than
# approving silently. A run that has not completed means waiting, never approval.
CHECK_GATE_MARKER = "<!-- openhands-review-gate:"
NON_BLOCKING_CHECK_CONCLUSIONS = frozenset({"success", "neutral", "skipped"})
# The gate is deterministic; this disclosure is what tells a reader no model ran.
WORKFLOW_DISCLOSURE = "no AI was used to generate this comment"


class PullRequestReviewer(GitHubRepository):
    name = "github-pr-reviewer"

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
            f"If its head is no longer `{sha}`, {moved_head_instruction}.\n"
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
        """Deterministic ordering: start time first, then the run ID.

        A queued or requested run can predate its `started_at`, which GitHub
        reports as null, so a missing start time must not sort before a real
        timestamp and let a stale earlier run win. The run ID is a monotonically
        increasing per-repository counter, so it is the fallback whenever a
        start time is absent.
        """
        run_id = int(run.get("id") or 0)
        started_at = run.get("started_at")
        return (started_at or f"~{run_id:020d}", run_id)

    def _latest_check_runs(self, sha):
        """Return only the latest run of each logical check on the exact head.

        GitHub lists every run for a commit, so a check that was re-run after a
        fix would otherwise contribute its superseded failure forever. A logical
        check is its name plus the reporting app identity, so two apps that use
        the same name stay independent. Within a group the latest run wins,
        ordered by start time and then run ID so a timestamp tie stays
        deterministic, with the run ID also standing in for a queued run whose
        start time is still absent; a newer queued or in-progress re-run
        therefore supersedes an earlier success and makes the head wait.
        """
        latest = {}
        for run in self.check_runs(sha):
            if run.get("head_sha") != sha:
                continue
            key = (run.get("name") or "unnamed check", self._check_app_identity(run))
            current = latest.get(key)
            if current is None or self._check_run_order(run) > self._check_run_order(
                current
            ):
                latest[key] = run
        return list(latest.values())

    def _classify_check_runs(self, sha):
        """Split current-head check runs into blocking, pending, and green.

        Only runs GitHub attributes to the exact head count: a run left behind on
        an obsolete head must not block the push that fixed it. Only the latest
        run of each logical check counts, so a re-run that fixed a check
        supersedes its earlier failure. A completed run whose conclusion is
        neither blocking nor explicitly non-blocking fails closed, so an unknown
        conclusion cannot silently approve a PR.
        """
        blocking, pending = [], []
        for run in self._latest_check_runs(sha):
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
        one. Every PR comment is untrusted input: only a marker this account
        authored is "managed", so a marker someone else placed can neither
        suppress the explanation nor be edited. An unmarked deterministic comment
        an existing repository workflow already posted is treated as the
        equivalent explanation only when it names the same reported checks; a
        comment about some other check is left alone and the gate posts its own.
        """
        comments = self.gh_pages(f"/issues/{number}/comments")
        managed = [
            comment
            for comment in comments
            if CHECK_GATE_MARKER in (comment.get("body") or "")
            and self._owns_comment(comment)
        ]
        if any(marker in (comment.get("body") or "") for comment in managed):
            return None
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

    def _gate_body(self, sha, state, names):
        short = sha[:12]
        listed = "\n".join(f"- `{name}`" for name in names)
        if state == "blocked":
            heading = "### ⚠️ Review paused: current-head checks failed"
            lead = (
                f"The current head `{short}` has failing checks, so no review "
                "conversation was started:"
            )
            action = (
                "Fix the checks above and push. The scheduled scan, or a new "
                "review request, then starts the review on the updated head."
            )
        else:
            heading = "### ⏳ Review waiting on checks"
            lead = (
                f"The current head `{short}` still has checks that have not "
                "finished, so no review conversation was started:"
            )
            action = (
                "No action is needed. The scheduled scan, or a new review "
                "request, retries once every check on the head reports a "
                "conclusion."
            )
        return (
            f"{heading}\n\n{lead}\n\n{listed}\n\n{action}\n\n"
            f"{CHECK_GATE_MARKER}{state}:{sha} -->\n\n"
            f"_This is an automated check - {WORKFLOW_DISCLOSURE}._"
        )

    def _gate_head(self, pr):
        """Return the head's eligibility, explaining any stop on the PR."""
        sha = pr["head"]["sha"]
        state, names = self._classify_check_runs(sha)
        if state in ("blocked", "waiting"):
            marker = f"{CHECK_GATE_MARKER}{state}:{sha} -->"
            self._gate_comment(
                pr["number"], marker, self._gate_body(sha, state, names), names
            )
        return state, sha

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
            }:
                continue
            try:
                pr = self.gh("GET", f"/pulls/{candidate['number']}")
                trigger = (
                    self._latest_reviewer_request(pr["number"])
                    if event_mode
                    else workflow._latest_trigger_label_event(
                        self.token, self.repository, pr["number"]
                    )
                )
                if trigger is None:
                    continue
                trigger_label = None if event_mode else label
                if self._finish_completed_review(pr, trigger, trigger_label):
                    continue
                if event_mode and payload.get("action") == "submitted":
                    # A submitted review is a completion signal, never a fresh
                    # trigger. A non-decisive review, or one superseded by a new
                    # head, must wait for another reviewer request instead of
                    # dispatching a review the caller never asked for.
                    continue
                sha = pr["head"]["sha"]
                gate_state, sha = self._gate_head(pr)
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
            except Exception as exc:  # noqa: BLE001 - one PR must not block the scan
                failures.append(candidate.get("number", "?"))
                print(
                    f"Failed to submit {self.repository} PR "
                    f"#{candidate.get('number', '?')}: "
                    f"{type(exc).__name__}: {exc}",
                    file=sys.stderr,
                    flush=True,
                )
        if failures:
            raise RuntimeError(
                "Reviewer scan failed for PRs: "
                + ", ".join(f"#{number}" for number in failures)
            )


if __name__ == "__main__":
    with AgentConversationDispatcher() as dispatcher:
        run_repositories(PullRequestReviewer, dispatcher=dispatcher)
