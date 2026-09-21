"""Select labeled PR heads and delegate each review to a sandboxed agent."""

import json
from urllib.parse import quote

import main as workflow
from agent_conversation import AgentConversationDispatcher
from github_client import GitHubRepository, run_repositories
from maintainer_handoff import parse_maintainers, request_maintainer_review


class PullRequestReviewer(GitHubRepository):
    name = "github-pr-reviewer"

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
            f"If its head is no longer `{sha}`, publish no status and leave `{label}` "
            "in place so the new head is reviewed.\n"
            "- After the readable native review is accepted by GitHub, set commit "
            "status `software-factory/review` to success only for an `✅ APPROVED` "
            "verdict, otherwise failure. Set `software-factory/tests` to success only "
            "when the relevant checks and tests pass, otherwise failure. Use the exact "
            f"head `{sha}` for both statuses.\n"
            f"- Leave the `{label}` label in place after both statuses are visible. "
            "The deterministic scanner removes it after completing any configured "
            "human-review handoff. Never paste JSON artifacts or full command logs "
            "into comments."
        )

    def _finish_completed_review(self, pr, label):
        """Complete an exact-head review, including an optional human handoff."""
        statuses = self.statuses(pr["head"]["sha"])
        review = statuses.get("software-factory/review")
        tests = statuses.get("software-factory/tests")
        if review is None or tests is None:
            return False
        if review == "success" and tests == "success":
            maintainers = parse_maintainers(self.config.get("maintainers"))
            if maintainers:
                selected = request_maintainer_review(self, pr, maintainers)
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
        self.gh("DELETE", f"/issues/{pr['number']}/labels/{quote(label, safe='')}")
        return True

    def run(self):
        repository_id = self.gh("GET", "")["id"]
        label = self.config.get("trigger_label", workflow.TRIGGER_LABEL)
        prs = self.gh_pages("/pulls?state=open&sort=updated&direction=asc")
        for candidate in prs:
            if label not in {item["name"] for item in candidate.get("labels", [])}:
                continue
            try:
                pr = self.gh("GET", f"/pulls/{candidate['number']}")
                if self._finish_completed_review(pr, label):
                    continue
                event = workflow._latest_trigger_label_event(
                    self.token, self.repository, pr["number"]
                )
                if event is None:
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
                print(
                    f"Failed to submit {self.repository} PR "
                    f"#{candidate.get('number', '?')}: {exc}",
                    flush=True,
                )


if __name__ == "__main__":
    with AgentConversationDispatcher() as dispatcher:
        run_repositories(PullRequestReviewer, dispatcher=dispatcher)
