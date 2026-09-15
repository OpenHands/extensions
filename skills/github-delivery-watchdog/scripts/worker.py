"""Follow delivery progress and merge only independently accepted, current PRs."""

import json
import re

from github_client import GitHubRepository, run_repositories


class DeliveryWatchdog(GitHubRepository):
    name = "github-delivery-watchdog"

    def ci_passed(self, sha):
        """Actions read works with fine-grained PATs; permission errors fail closed."""
        runs = {}
        for page in range(1, 11):
            result = self.gh(
                "GET", f"/actions/runs?head_sha={sha}&per_page=100&page={page}"
            )
            for run in result["workflow_runs"]:
                if run["head_sha"] != sha:
                    return False
                runs[run["id"]] = run
            if len(result["workflow_runs"]) < 100:
                if result["total_count"] != len(runs):
                    return False
                latest = {}
                for run in sorted(
                    runs.values(), key=lambda r: r["run_number"], reverse=True
                ):
                    # A newer execution supersedes the same workflow trigger,
                    # but a passing push must not hide a failing PR workflow.
                    latest.setdefault(
                        (run["workflow_id"], run["event"], run["head_branch"]), run
                    )
                return set(self.config.get("required_workflow_ids", [])) <= {
                    r["workflow_id"] for r in latest.values()
                } and all(
                    r["status"] == "completed" and r["conclusion"] == "success"
                    for r in latest.values()
                )
        return False

    def merge(self, number, sha):
        pr = self.gh("GET", f"/pulls/{number}")
        prefix = re.escape(self.config.get("branch_prefix", "openhands/issue"))
        if not (
            pr["state"] == "open"
            and pr["head"]["sha"] == sha
            and pr["base"]["ref"] == self.base_branch
            and re.fullmatch(prefix + r"-\d+", pr["head"]["ref"])
            and not pr["draft"]
            and pr["mergeable"] is True
        ):
            return None
        statuses = self.statuses(sha)
        required = ("software-factory/tests", "software-factory/review")
        if not all(statuses.get(c) == "success" for c in required):
            return None
        if not all(
            value == "success" for value in statuses.values()
        ) or not self.ci_passed(sha):
            return None
        comparison = self.gh("GET", f"/compare/{pr['base']['sha']}...{sha}")
        if comparison["status"] not in ("ahead", "identical"):
            return None
        return self.gh(
            "PUT", f"/pulls/{number}/merge", {"sha": sha, "merge_method": "squash"}
        )

    def run(self):
        for pr in self.gh_pages("/pulls?state=open"):
            try:
                result = self.merge(pr["number"], pr["head"]["sha"])
            except Exception as exc:  # noqa: BLE001 - one PR must not block other repositories
                # A conflict, permission failure, or unavailable API cannot
                # authorize a merge or prevent checking unrelated pull requests.
                result = {
                    "error": type(exc).__name__,
                    "status": getattr(exc, "code", None),
                }
            print(json.dumps({"pr": pr["number"], "merge": result}), flush=True)


if __name__ == "__main__":
    run_repositories(DeliveryWatchdog)
