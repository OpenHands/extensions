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

    @staticmethod
    def _review_completes_request(review, triggered_at, submitted_review):
        """Whether *review* closes the request the current run was triggered by.

        A ``pull_request_review.submitted`` delivery names the review it reports
        and is created after that review's ``submitted_at``. Comparing it to the
        earlier ``review_requested`` timestamp would reject the very review the
        event announced, so the reported review is accepted regardless of timing.
        """
        if submitted_review and submitted_review.get("id") is not None:
            return review.get("id") == submitted_review["id"]
        if not triggered_at:
            # With no selected trigger there is no window to compare against, so
            # only the review a submitted event names can complete the run.
            return False
        return (review.get("submitted_at") or "") > triggered_at

    def _finish_completed_review(self, pr, trigger, label=None, submitted_review=None):
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
            and self._review_completes_request(review, triggered_at, submitted_review)
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
                submitted_review = (
                    payload.get("review")
                    if event_mode and payload.get("action") == "submitted"
                    else None
                )
                trigger = (
                    self._latest_reviewer_request(pr["number"])
                    if event_mode
                    else workflow._latest_trigger_label_event(
                        self.token, self.repository, pr["number"]
                    )
                )
                if trigger is None:
                    # A submitted review is its own completion signal: the bot
                    # may have published a review whose request predates the
                    # issue-event window, and that review must still complete.
                    if submitted_review is None:
                        continue
                    trigger = {}
                trigger_label = None if event_mode else label
                if self._finish_completed_review(
                    pr, trigger, trigger_label, submitted_review
                ):
                    continue
                if event_mode and payload.get("action") == "submitted":
                    # A submitted review is a completion signal, never a fresh
                    # trigger. A non-decisive review, or one superseded by a new
                    # head, must wait for another reviewer request instead of
                    # dispatching a review the caller never asked for.
                    continue
                sha = pr["head"]["sha"]
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
