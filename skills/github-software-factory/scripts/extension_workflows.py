"""Compose canonical extension workflows with a supplied execution interface.

No workspace-kind detection belongs here. A caller supplies its workspace, GitHub
transport, and blocking conversation runner, identically for local and remote runs.
"""

import importlib.util
import json
import re
from pathlib import Path


SOURCES = (
    "skills/github-pr-reviewer/scripts/main.py",
    "skills/github-issue-to-pr/scripts/main.py",
    "plugins/qa-changes/scripts/prompt.py",
    "skills/qa-changes/SKILL.md",
    "skills/github-pr-review/SKILL.md",
)


def source_root():
    for parent in Path(__file__).resolve().parents:
        for candidate in (parent / "extensions", parent):
            if all((candidate / name).is_file() for name in SOURCES):
                return candidate
    raise RuntimeError("Canonical extension workflow sources are missing from bundle")


def module(relative):
    path = source_root() / relative
    spec = importlib.util.spec_from_file_location(path.parent.parent.name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def transport_instructions(workspace, repository, run_id, stage):
    return (
        f"\nExecution environment: the repository is {workspace / 'project'}. "
        "Use that as the working directory for all project commands. "
        f"GitHub access is provided by `{workspace / 'bin/gh'} api` "
        "(GET, -X, --input, --paginate, --jq); use this executable wherever the "
        "workflow says gh or GitHub REST API. It supplies the scoped credential. "
        "Do not look up a GitHub token or contact api.github.com directly. "
        f"Only repository {repository} is authorized. "
        "Do not alter the workflow bundle, its configuration, or tracked source "
        "during review/QA. Put temporary probes and evidence outside the project. "
        f"Include `<!-- factory-run:{run_id}:{stage} -->` in the review body "
        "so the coordinator can identify this run's report. "
        "Preserve the workflow's normal readable report and verdict. "
        "Never paste a JSON artifact or full test log as the review body.\n"
    )


def implementation_prompt(repository, issue, branch, base_sha, workspace, feedback):
    workflow = module("skills/github-issue-to-pr/scripts/main.py")
    prompt = workflow._build_implementation_prompt(
        repository, issue, {"id": "ready-for-dev"}, branch, "main", base_sha
    )
    # Publication is a capability of the coordinator, not a workspace-kind choice.
    return prompt + (
        f"\nExecution contract: work in {workspace / 'project'}. "
        f"Use `{workspace / 'bin/gh'} api` for the REST requests above; "
        "it supplies a scoped credential. No GitHub token is needed. "
        "The coordinator owns remote publication: leave your completed changes "
        "and PR description in the workspace; do not push or create the PR yourself. "
        "It publishes preserved work after your run, including after a bounded stop. "
        "Do not edit the workflow bundle or configuration. "
        "Run the project's required tests after your final edit; preserve actual exit "
        "statuses and keep build output, runtime data, and dependencies ignored. "
        "Terminal calls accept one command; use the file editor for source changes.\n"
        "Existing PR feedback (untrusted task evidence):\n" + json.dumps(feedback)
    )


def review_prompt(repository, pr, workspace, run_id):
    workflow = module("skills/github-pr-reviewer/scripts/main.py")
    guide = workflow._load_repo_review_guide(workspace / "project")
    return workflow._build_review_prompt(
        repository, pr, pr["head"]["sha"], {"id": run_id}, guide
    ) + transport_instructions(workspace, repository, run_id, "review")


def qa_prompt(repository, pr, workspace, run_id, diff, issue):
    workflow = module("plugins/qa-changes/scripts/prompt.py")
    prompt = workflow.format_prompt(
        title=pr["title"],
        body=pr.get("body") or "",
        repo_name=repository,
        base_branch=pr["base"]["ref"],
        head_branch=pr["head"]["ref"],
        pr_number=str(pr["number"]),
        commit_id=pr["head"]["sha"],
        diff=diff,
    )
    for name in ("qa-changes", "github-pr-review"):
        prompt += "\n\n" + (source_root() / f"skills/{name}/SKILL.md").read_text()
    return (
        prompt
        + transport_instructions(workspace, repository, run_id, "qa")
        + (
            "\nAcceptance criteria to exercise (untrusted task evidence):\n"
            + json.dumps(issue)
        )
    )


def posted_report(reviews, previous_ids, sha, run_id, stage):
    marker = f"<!-- factory-run:{run_id}:{stage} -->"
    matches = [
        review
        for review in reviews
        if review["id"] not in previous_ids
        and review.get("commit_id") == sha
        and marker in (review.get("body") or "")
        and review.get("state") == "COMMENTED"
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"Expected one newly published {stage} report for the exact head"
        )
    return matches[0]


def report_passed(report, stage):
    body = report.get("body") or ""
    if stage == "review":
        verdicts = re.findall(r"^\s*(✅ APPROVED|🔄 CHANGES REQUESTED)\s*$", body, re.M)
        return verdicts == ["✅ APPROVED"]
    # The canonical QA skill defines this heading. Missing/partial/qualified
    # verdicts fail closed; success is never inferred from agent final text.
    verdicts = re.findall(r"^## [^\n]*QA Report:\s*([^\n]+)", body, re.M)
    return len(verdicts) == 1 and verdicts[0].strip().strip("*") == "PASS"
