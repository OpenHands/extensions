"""Select ready GitHub work and delegate each subject to a sandboxed agent."""

import json
import re

import main as workflow
from agent_conversation import AgentConversationDispatcher
from github_client import GitHubRepository, run_repositories


class IssueToPR(GitHubRepository):
    name = "github-issue-to-pr"

    def _workspace_instructions(self, branch, revision):
        token = self.token_name
        if revision:
            checkout = f"check out the existing remote branch `{branch}`"
        else:
            checkout = (
                f"create and check out `{branch}` from the repository's base branch"
            )
        return (
            "The workspace starts empty. Clone the repository into it with "
            f"`GH_TOKEN=${{{token}}} gh repo clone {self.repository} .`, then {checkout}. "
            "Keep the remote free of embedded credentials."
        )

    def _prompt(self, issue, branch, base_branch, base_sha, *, revision=None):
        review_label = self.config.get("review_label", "openhands-review")
        prompt = workflow._build_implementation_prompt(
            self.repository,
            issue,
            {
                "id": issue.get("updated_at", "?"),
                "created_at": issue.get("updated_at", "?"),
            },
            branch,
            base_branch,
            base_sha,
            workspace_instructions=self._workspace_instructions(branch, revision),
            github_token_secret=self.token_name,
        )
        if revision:
            prompt = (
                f"Revise existing PR #{revision['number']} at exact head "
                f"`{revision['head']['sha']}`. Read its current reviews, inline "
                "comments, discussion, and failing checks directly from GitHub. "
                "Address each current finding or explain with evidence why no code "
                "change is warranted. Push revisions to the existing branch; do not "
                "open another pull request. After responding, remove and reapply the "
                f"`{review_label}` label so the exact new head is reviewed. If no code "
                "change is needed, post that evidence on the PR before reapplying it.\n\n"
                + prompt
            )
        else:
            prompt += (
                f"\n\nAfter opening the pull request, add the `{review_label}` label so "
                "the independent reviewer checks its exact head."
            )
        return prompt

    def _submit(
        self, repository_id, issue, branch, base_branch, base_sha, *, revision=None
    ):
        revision_sha = revision["head"]["sha"] if revision else None
        key = revision_sha or issue.get("updated_at") or str(issue["number"])
        result = self.dispatcher.deliver(
            subject=f"{repository_id}:issue:{issue['number']}",
            delivery=f"{issue['number']}:{key}",
            prompt=self._prompt(
                issue,
                branch,
                base_branch,
                revision_sha or base_sha,
                revision=revision,
            ),
        )
        print(
            json.dumps(
                {
                    "repository": self.repository,
                    "issue": issue["number"],
                    "pr": revision["number"] if revision else None,
                    "disposition": result["disposition"],
                    "conversation_id": result["conversation_id"],
                }
            ),
            flush=True,
        )

    def _try_submit(
        self, repository_id, issue, branch, base_branch, base_sha, *, revision=None
    ):
        try:
            self._submit(
                repository_id,
                issue,
                branch,
                base_branch,
                base_sha,
                revision=revision,
            )
        except Exception as exc:  # noqa: BLE001 - one issue must not block the scan
            print(
                f"Failed to submit {self.repository} issue "
                f"#{issue.get('number', '?')}: {exc}",
                flush=True,
            )

    def run(self):
        trigger_label = self.config.get("trigger_label", workflow.TRIGGER_LABEL)
        branch_prefix = self.config.get("branch_prefix", workflow.BRANCH_PREFIX)
        repository = self.gh("GET", "")
        repository_id = repository["id"]
        base_branch = self.config.get("base_branch") or repository["default_branch"]
        base_sha = self.gh("GET", f"/git/ref/heads/{base_branch}")["object"]["sha"]
        issues = {issue["number"]: issue for issue in self.open_issues()}

        open_prs = self.gh_pages("/pulls?state=open")
        issue_prs = {}
        for pr in open_prs:
            match = re.fullmatch(
                re.escape(branch_prefix) + r"-(\d+)", pr["head"]["ref"]
            )
            if match:
                issue_prs[int(match[1])] = pr

        for issue_number, pr in sorted(issue_prs.items()):
            issue = issues.get(issue_number)
            if issue is None:
                continue
            if self.statuses(pr["head"]["sha"]).get("software-factory/review") not in {
                "failure",
                "error",
            }:
                continue
            self._try_submit(
                repository_id,
                issue,
                pr["head"]["ref"],
                (pr.get("base") or {}).get("ref") or base_branch,
                base_sha,
                revision=pr,
            )

        ready = [
            issue
            for issue in issues.values()
            if issue["number"] not in issue_prs
            and trigger_label in {label["name"] for label in issue.get("labels", [])}
            and self.dependencies_complete(issue)
        ]
        for issue in sorted(
            ready,
            key=lambda item: (
                "priority:high"
                not in {label["name"] for label in item.get("labels", [])},
                item["number"],
            ),
        ):
            self._try_submit(
                repository_id,
                issue,
                f"{branch_prefix}-{issue['number']}",
                base_branch,
                base_sha,
            )


if __name__ == "__main__":
    with AgentConversationDispatcher() as dispatcher:
        run_repositories(IssueToPR, dispatcher=dispatcher)
