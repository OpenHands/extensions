"""Review each new PR head with the existing code-review and QA workflows."""

import json
import os
import re
import shlex
import subprocess
from contextlib import closing
from pathlib import Path
from urllib.parse import quote
from uuid import UUID

import main as workflow
from github_client import GitHubRepository, run_repositories
from openhands.sdk import RemoteConversation, RemoteWorkspace
from qa_prompt import format_prompt


class PullRequestReviewer(GitHubRepository):
    name = "github-pr-reviewer"

    def status(self, sha, context, passed, detail):
        self.gh(
            "POST",
            f"/statuses/{sha}",
            {
                "context": "software-factory/" + context,
                "state": "success" if passed else "failure",
                "description": detail[:140],
            },
        )

    def independent_tests(self):
        results = []
        commands = self.config.get("test_commands", [])
        if isinstance(commands, str):
            commands = [
                shlex.split(line) for line in commands.splitlines() if line.strip()
            ]
        if not commands or not all(
            isinstance(c, list) and c and all(isinstance(a, str) for a in c)
            for c in commands
        ):
            raise ValueError(
                "Independent acceptance requires test_commands (one command per line or arrays of arguments)"
            )
        for command in commands:
            label = " ".join(command)
            try:
                output = self.shell(command, timeout=480).replace(
                    self.token, "[REDACTED]"
                )
                results.append({"command": label, "passed": True, "output": output})
            except (RuntimeError, subprocess.TimeoutExpired) as exc:
                results.append({"command": label, "passed": False, "output": str(exc)})
                break
        clean = self.tracked_files_unchanged()
        passed = (
            len(results) == len(commands)
            and all(t["passed"] for t in results)
            and clean
        )
        (self.evidence / "tests.json").write_text(json.dumps(results, indent=2))
        return (results, passed)

    def run(self):
        prs = self.gh_pages("/pulls?state=open&sort=updated&direction=asc")
        accepting = bool(self.config.get("test_commands"))
        if self.config.get("branch_prefix") and not accepting:
            raise ValueError(
                "Continuous delivery review requires independent test_commands"
            )
        if self.config.get("branch_prefix"):
            prs = [
                p
                for p in prs
                if re.fullmatch(
                    re.escape(self.config["branch_prefix"]) + r"-\d+", p["head"]["ref"]
                )
            ]
        else:
            label = self.config.get("trigger_label", "openhands-review")
            prs = [p for p in prs if label in {item["name"] for item in p["labels"]}]
        pending = [
            p
            for p in prs
            if "software-factory/review" not in self.statuses(p["head"]["sha"])
            or self.config.get("trigger_label", "openhands-review")
            in {label["name"] for label in p.get("labels", [])}
        ]
        if not pending:
            return
        pr = self.gh("GET", f"/pulls/{pending[0]['number']}")
        sha = pr["head"]["sha"]
        self.project = workflow._prepare_repository(
            self.token, self.repository, pr["number"], sha
        )
        # Use Git's existing ignore rules for generated files, while force-adding
        # the exact archive so ignored-but-tracked source remains protected.
        self.shell(["git", "init", "--quiet"])
        self.shell(["git", "add", "--force", "."])
        self.source_tree = self.shell(["git", "write-tree"])
        test_results, tests_pass = [], False
        reports = {}
        failure = None
        try:
            if accepting:
                test_results, tests_pass = self.independent_tests()
                self.status(
                    sha, "tests", tests_pass, "Independent repository test commands"
                )
                test_summary = "\n".join(
                    f"- {('PASS' if result['passed'] else 'FAIL')}: `{result['command']}`"
                    for result in test_results
                )
                failures = [result for result in test_results if not result["passed"]]
                if failures:
                    test_summary += (
                        "\n\nFailure excerpt:\n```text\n"
                        + failures[0]["output"][-2000:]
                        + "\n```"
                    )
                self.comment(
                    pr["number"], f"Independent checks for `{sha}`:\n\n" + test_summary
                )
            for stage in ("review", "qa") if accepting else ("review",):
                if stage == "qa" and not tests_pass:
                    break
                reports[stage] = self.run_stage(pr, stage)
                if not reports[stage]["passed"]:
                    break
        except Exception as exc:
            failure = type(exc).__name__
            try:
                self.comment(
                    pr["number"],
                    f"Independent review of `{sha}` could not finish ({failure}). The review automation will retry; this is not an acceptance decision.",
                )
            except Exception as report_error:  # noqa: BLE001 - reporting must not mask the review failure
                print(
                    f"Could not publish retry notice: {type(report_error).__name__}",
                    flush=True,
                )
            raise
        finally:
            clean = current = False
            try:
                clean = self.tracked_files_unchanged()
                current = self.gh("GET", f"/pulls/{pr['number']}")["head"]["sha"] == sha
            except Exception as verify_error:  # noqa: BLE001 - all verification failures require a retry
                failure = failure or type(verify_error).__name__
                print(
                    f"Could not verify acceptance: {type(verify_error).__name__}",
                    flush=True,
                )
            accepted = (
                (tests_pass or not accepting)
                and clean
                and current
                and all(
                    reports.get(stage, {}).get("passed") is True
                    for stage in (("review", "qa") if accepting else ("review",))
                )
            )
            (self.evidence / "acceptance.json").write_text(
                json.dumps(
                    {
                        "head_sha": sha,
                        "conversation_id": self.conversation_id,
                        "reports": reports,
                        "failure": failure,
                        "tests": test_results,
                        "tracked_files_unchanged": clean,
                        "current_head": current,
                        "accepted": accepted,
                    },
                    indent=2,
                )
            )
            review = reports.get("review")
            # A published code review is terminal unless passing tests and
            # review still require the independent QA report.
            complete = review is not None and (
                not accepting
                or not tests_pass
                or not review["passed"]
                or "qa" in reports
            )
            if complete and failure is None:
                self.status(
                    sha,
                    "review",
                    accepted,
                    "Code review and functional QA accepted"
                    if accepted
                    else "Code review or functional QA incomplete or needs changes",
                )
                label = self.config.get("trigger_label", "openhands-review")
                if current and label in {item["name"] for item in pr.get("labels", [])}:
                    self.gh(
                        "DELETE",
                        f"/issues/{pr['number']}/labels/{quote(label, safe='')}",
                    )

    def run_stage(self, pr, stage):
        sha = pr["head"]["sha"]
        before = {
            r["id"]
            for r in self.gh_pages(f"/pulls/{pr['number']}/reviews")
            if r.get("state") != "PENDING"
        }
        if stage == "review":
            prompt = self.review_prompt(pr)
        else:
            files = self.gh_pages(f"/pulls/{pr['number']}/files")
            diff = "\n".join(
                f"File: {file['filename']}\n{file.get('patch', '(patch unavailable; inspect workspace)')}"
                for file in files
            )
            prompt = self.qa_prompt(pr, diff)
        prompt += (
            f"\nInclude <!-- factory-run:{self.conversation_id}:{stage} --> in the review body. "
            "Preserve the normal readable report and verdict; never paste a JSON artifact or full log. "
            "Do not modify tracked source or the automation bundle; put temporary probes outside the project."
        )
        self.conversation.send_message(prompt)
        self.conversation.run(timeout=2400)
        report = self.posted_report(before, sha, stage, pr["number"])
        return {
            "id": report["id"],
            "url": report["html_url"],
            "passed": self.report_passed(report, stage),
        }

    def tracked_files_unchanged(self):
        return not self.shell(
            ["git", "diff", "--name-only", self.source_tree, "--"]
        ) and not self.shell(["git", "ls-files", "--others", "--exclude-standard"])

    def posted_report(self, previous_ids, sha, stage, number):
        marker = f"<!-- factory-run:{self.conversation_id}:{stage} -->"
        matches = [
            review
            for review in self.gh_pages(f"/pulls/{number}/reviews")
            if review["id"] not in previous_ids
            and review.get("commit_id") == sha
            and marker in (review.get("body") or "")
            and review.get("state") == "COMMENTED"
        ]
        if not matches:
            raise RuntimeError(
                f"Expected a newly published {stage} report for the exact head"
            )
        # The canonical workflow may publish its summary and inline comments
        # as separate reviews. Every matching report must agree on acceptance.
        return next(
            (report for report in matches if not self.report_passed(report, stage)),
            max(matches, key=lambda report: len(report.get("body") or "")),
        )

    @staticmethod
    def report_passed(report, stage):
        body = report.get("body") or ""
        if stage == "review":
            return re.findall(
                r"^\s*(✅ APPROVED|🔄 CHANGES REQUESTED)\s*$", body, re.MULTILINE
            ) == ["✅ APPROVED"]
        verdicts = re.findall(r"^## [^\n]*QA Report:\s*([^\n]+)", body, re.MULTILINE)
        return len(verdicts) == 1 and verdicts[0].strip().strip("*") == "PASS"

    def review_prompt(self, pr):
        return workflow._build_review_prompt(
            self.repository,
            pr,
            pr["head"]["sha"],
            {"id": self.conversation_id},
            workflow._load_repo_review_guide(self.project),
            github_access_instructions=self.github_instructions,
        )

    def qa_prompt(self, pr, diff):
        prompt = format_prompt(
            title=pr["title"],
            body=pr.get("body") or "",
            repo_name=self.repository,
            base_branch=pr["base"]["ref"],
            head_branch=pr["head"]["ref"],
            pr_number=str(pr["number"]),
            commit_id=pr["head"]["sha"],
            diff=diff,
        )
        for name in ("qa-changes", "github-pr-review"):
            prompt += "\n\n" + Path(__file__).with_name(name + ".md").read_text()
        return (
            self.github_instructions
            + "\n\n"
            + prompt
            + "\nRead the linked issue and its latest acceptance criteria and triage comments directly from GitHub, as required by the QA workflow."
        )


if __name__ == "__main__":
    from openhands.tools import register_default_tools

    register_default_tools()

    with (
        RemoteWorkspace(
            host=os.environ["AGENT_SERVER_URL"],
            api_key=os.environ["SESSION_API_KEY"],
            working_dir=os.environ["WORKSPACE_BASE"],
        ) as workspace,
        closing(
            RemoteConversation.attach(
                workspace=workspace,
                conversation_id=UUID(os.environ["AUTOMATION_CONVERSATION_ID"]),
                visualizer=None,
            )
        ) as conversation,
    ):
        run_repositories(PullRequestReviewer, conversation)
