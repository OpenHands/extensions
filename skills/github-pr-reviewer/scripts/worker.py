"""Select labeled PR heads and delegate each review to a sandboxed agent."""

import json
import os
from urllib.request import Request, urlopen

import main as workflow
from github_client import GitHubRepository, run_repositories


def submit_subject_turn(*, source, subject_key, turn, idempotency_key):
    request = Request(
        os.environ["AUTOMATION_SUBJECT_TURN_URL"],
        data=json.dumps(
            {
                "source": source,
                "subject_key": subject_key,
                "turn": turn,
                "idempotency_key": idempotency_key,
            }
        ).encode(),
        headers={
            "Authorization": f"Bearer {os.environ['AUTOMATION_RUN_TOKEN']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(request, timeout=90) as response:
        return json.load(response)


class PullRequestReviewer(GitHubRepository):
    name = "github-pr-reviewer"

    def _prompt(self, pr, label_event):
        number = pr["number"]
        sha = pr["head"]["sha"]
        label = self.config.get("trigger_label", workflow.TRIGGER_LABEL)
        token = self.token_name
        workspace = (
            "The workspace starts empty. Clone the repository with "
            f"`GH_TOKEN=${{{token}}} gh repo clone {self.repository} .`, fetch PR "
            f"#{number}, and check out exact head `{sha}` in detached-HEAD mode. "
            "Keep the remote free of embedded credentials."
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
            f"- After both statuses are visible on that head, remove the `{label}` "
            "label. Never paste JSON artifacts or full command logs into comments."
        )

    def run(self):
        repository_id = self.gh("GET", "")["id"]
        label = self.config.get("trigger_label", workflow.TRIGGER_LABEL)
        prs = self.gh_pages("/pulls?state=open&sort=updated&direction=asc")
        for candidate in prs:
            if label not in {item["name"] for item in candidate.get("labels", [])}:
                continue
            pr = self.gh("GET", f"/pulls/{candidate['number']}")
            event = workflow._latest_trigger_label_event(
                self.token, self.repository, pr["number"]
            )
            if event is None:
                continue
            sha = pr["head"]["sha"]
            result = submit_subject_turn(
                source=self.name,
                subject_key=f"{repository_id}:pr:{pr['number']}",
                idempotency_key=f"{event['id']}:{sha}",
                turn=self._prompt(pr, event),
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


if __name__ == "__main__":
    run_repositories(PullRequestReviewer)
