"""Select labeled PR heads and delegate each review to a sandboxed agent."""

import json
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

    def _prompt(self, pr, label_event):
        number = pr["number"]
        sha = pr["head"]["sha"]
        label = self.config.get("trigger_label", workflow.TRIGGER_LABEL)
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
            label_event,
            workspace_instructions=workspace,
            github_token_secret=token,
        )
        return (
            prompt + "\n\nAcceptance reporting:\n"
            "- Inspect the current GitHub Actions results for the exact head and run "
            "the repository's appropriate focused tests in the workspace. Do not "
            "modify tracked files.\n"
            f"- Re-read {self.repository} PR #{number} immediately before reporting. "
            f"If its head is no longer `{sha}`, publish no review and leave `{label}` "
            "in place so the new head is reviewed.\n"
            f"- Leave the `{label}` label in place after GitHub accepts the review. "
            "The deterministic scanner removes it after completing any configured "
            "human-review handoff. Never paste JSON artifacts or full command logs "
            "into comments.\n"
            "- Once GitHub accepts the native review, stop immediately. Do not "
            "continue inspecting the repository, run more commands, or publish a "
            "second result."
        )

    def _finish_completed_review(self, pr, label, label_event):
        """Complete an exact-head review, including an optional human handoff."""
        head_sha = pr["head"]["sha"]
        triggered_at = label_event.get("created_at") or ""
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
        if approved is None:
            return False
        if approved:
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
                                "maintainer roster, then add the review label again."
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
            # The label remains for the next scan, which will review the new
            # head. Treat this scan as handled so it cannot redeliver the stale
            # head after detecting the race.
            return True
        self.gh("DELETE", f"/issues/{pr['number']}/labels/{quote(label, safe='')}")
        return True

    def run(self):
        repository_id = self.gh("GET", "")["id"]
        label = self.config.get("trigger_label", workflow.TRIGGER_LABEL)
        prs = self.gh_pages("/pulls?state=open&sort=updated&direction=asc")
        failures = []
        for candidate in prs:
            if label not in {item["name"] for item in candidate.get("labels", [])}:
                continue
            try:
                pr = self.gh("GET", f"/pulls/{candidate['number']}")
                event = workflow._latest_trigger_label_event(
                    self.token, self.repository, pr["number"]
                )
                if event is None:
                    continue
                if self._finish_completed_review(pr, label, event):
                    continue
                sha = pr["head"]["sha"]
                result = self.dispatcher.deliver(
                    subject=f"{repository_id}:pr:{pr['number']}",
                    delivery=f"{event['id']}:{sha}",
                    prompt=self._prompt(pr, event),
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
