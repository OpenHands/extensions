"""Read-only live canary for bounded scheduled intake across OSS repositories.

Loads the *shipped* bundle from the catalog manifest and drives the real
`PullRequestReviewer.run()` scheduled path and the real shared-intake drain
against the live GitHub API. It never starts an agent or posts a comment: the
dispatcher records what would have been delivered, and the gate comment upsert
is recorded instead of written. The maintainer handoff is skipped so the run
stays read-only.

Run:
    GITHUB_TOKEN_REVIEW=... WORKSPACE_BASE=$(mktemp -d) \
        python3 .pr/canary_bounded_intake.py
"""

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from github_automation_helpers import worker  # noqa: E402

REPOSITORIES = [
    "OpenHands/extensions",
    "OpenHands/OpenHands",
    "OpenHands/software-agent-sdk",
    "OpenHands/automation",
]


def _eligible_live_candidates(module, reviewers, bound):
    """Live outstanding-request PRs, forced eligible, to exercise the bound.

    The live scan is honest about the gate: a blocked head starts nothing. That
    left only one green candidate at canary time, so the bound was not the
    limiting factor. This pass takes the same live PRs, request events, head
    SHAs, and repositories, and treats each outstanding request as eligible, so
    the real drain is shown stopping at the bound on real data. Only the gate
    flag is overridden; ordering, delivery keys, and the drain are the shipped
    code.
    """
    delivered = []
    registered = []
    module.PullRequestReviewer.scan_intake = module.ReviewIntake()
    for run in reviewers:
        prs = run.gh_pages("/pulls?state=open&sort=updated&direction=asc")
        for candidate in prs:
            if candidate.get("draft") or not run._outstanding_review_request(
                candidate
            ):
                continue
            pr = run.gh("GET", f"/pulls/{candidate['number']}")
            trigger = run._latest_reviewer_request(pr["number"])
            if trigger is None:
                continue
            record = {
                "repository": run.repository,
                "number": pr["number"],
                "created_at": trigger.get("created_at") or "",
                "config": {**run.config, "max_new_per_run": bound},
                "start": (
                    lambda run=run, pr=pr, trigger=trigger: (
                        delivered.append(
                            {
                                "repository": run.repository,
                                "pr": pr["number"],
                                "delivery": (
                                    f"{trigger['id']}:{pr['head']['sha']}"
                                ),
                            }
                        )
                        or {"disposition": "created", "conversation_id": ""}
                    )
                ),
            }
            registered.append(record)
            run.intake.register(record)
    module.PullRequestReviewer.scan_intake.drain()
    return {
        "max_new_per_run": bound,
        "live_eligible_candidates": sorted(
            (
                {
                    "repository": item["repository"],
                    "pr": item["number"],
                    "requested_at": item["created_at"],
                }
                for item in registered
            ),
            key=lambda i: (i["requested_at"], i["repository"], i["pr"]),
        ),
        "conversations_started": delivered,
        "conversations_started_count": len(delivered),
    }


def main():
    workspace = Path(os.environ["WORKSPACE_BASE"])
    sys.argv = ["worker.py"]
    module = worker("github-pr-reviewer", workspace, _Ignore())

    bound = int(os.environ.get("CANARY_MAX_NEW_PER_RUN", "2"))
    delivered = []
    gate = []
    reviewers = []
    inspected = {}

    for repository in REPOSITORIES:
        run = object.__new__(module.PullRequestReviewer)
        run.config = {
            "repos": REPOSITORIES,
            "trigger_label": "openhands-review-canary",
            "trigger_reviewer": "all-hands-bot",
            "maintainers": "",
            "github_token_secret": "GITHUB_TOKEN_REVIEW",
            "max_new_per_run": bound,
        }
        run.repository = repository
        run.token_name = "GITHUB_TOKEN_REVIEW"
        run.token = os.environ["GITHUB_TOKEN_REVIEW"]
        run.github_login = "all-hands-bot"
        run.workspace = workspace
        run.project = workspace
        run.evidence = workspace / "evidence"
        run.evidence.mkdir(exist_ok=True)
        run._completed_dependencies = {}

        class Dispatcher:
            def deliver(self, *, subject, delivery, prompt, repo=repository):
                delivered.append(
                    {
                        "repository": repo,
                        "subject": subject,
                        "delivery": delivery,
                    }
                )
                return {"disposition": "created", "conversation_id": subject}

        run.dispatcher = Dispatcher()
        run._gate_comment = (
            lambda number, marker, body, names, repo=repository: gate.append(
                {"repository": repo, "pr": number, "marker": marker}
            )
        )
        run._finish_completed_review = lambda *a, **k: False
        reviewers.append(run)

    # The shipped entrypoint wiring: one shared intake, every repository's
    # scheduled run, then one bounded drain.
    module.PullRequestReviewer.scan_intake = module.ReviewIntake()
    for run in reviewers:
        run.run()
        inspected[run.repository] = len(run.gh_pages("/pulls?state=open"))
    pending = [
        {"repository": item["repository"], "pr": item["number"],
         "requested_at": item["created_at"]}
        for item in module.PullRequestReviewer.scan_intake._pending
    ]
    module.PullRequestReviewer.scan_intake.drain()

    evidence = {
        "configured_repositories": REPOSITORIES,
        "max_new_per_run": bound,
        "open_pull_requests_inspected": inspected,
        "registered_green_candidates": len(pending),
        "drain_order": sorted(
            pending,
            key=lambda i: (
                i["requested_at"],
                i["repository"],
                i["pr"],
            ),
        ),
        "conversations_started": delivered,
        "conversations_started_count": len(delivered),
        "gate_dispositions": gate,
    }
    for bound_case in (2, 1, 3):
        evidence[f"bound_demo_max_{bound_case}"] = _eligible_live_candidates(
            module, reviewers, bound_case
        )
    print(json.dumps(evidence, indent=2))


class _Ignore:
    """Minimal stand-in for pytest's monkeypatch, used only by the bundle loader."""

    def delitem(self, mapping, key, raising=True):
        mapping.pop(key, None)

    def syspath_prepend(self, path):
        sys.path.insert(0, path)


if __name__ == "__main__":
    main()
