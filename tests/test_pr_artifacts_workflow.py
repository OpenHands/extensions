"""Run the PR Artifacts notice script from .github/workflows/pr-artifacts.yml.

Node executes the workflow's real github-script body. Only the GitHub REST
transport is replaced, by in-memory pages and recorded comment writes.
"""

import json
import re
import subprocess
from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/pr-artifacts.yml"
MARKER = "<!-- pr-artifacts-notice -->"
HARNESS = """
import { readFileSync } from "node:fs";

const { script, files, comments } = JSON.parse(readFileSync(0, "utf8"));
const listFiles = Symbol("listFiles");
const listComments = Symbol("listComments");
const writes = [];
const github = {
  rest: {
    pulls: { listFiles },
    issues: {
      listComments,
      createComment: async ({ issue_number, body }) =>
        writes.push({ issue_number, body }),
      updateComment: async ({ comment_id, body }) =>
        writes.push({ comment_id, body }),
    },
  },
  paginate: async (endpoint, { per_page, pull_number, issue_number }) => {
    if (per_page !== 100) throw new Error("expected 100 items per page");
    if (endpoint === listFiles && pull_number === 42) return files;
    if (endpoint === listComments && issue_number === 42) return comments;
    throw new Error("unexpected paginated request");
  },
};
const AsyncFunction = Object.getPrototypeOf(async () => {}).constructor;
await new AsyncFunction("github", "context", "core", script)(
  github,
  { repo: { owner: "org", repo: "repo" }, issue: { number: 42 } },
  { warning: () => {} },
);
process.stdout.write(JSON.stringify(writes));
"""


def _script() -> str:
    """Return the github-script body as YAML's literal block scalar reads it."""
    lines = WORKFLOW.read_text().splitlines()
    start = next(i for i, line in enumerate(lines) if line.strip() == "script: |") + 1
    indent = len(lines[start]) - len(lines[start].lstrip())
    body = []
    for line in lines[start:]:
        if line.strip() and not line.startswith(" " * indent):
            break
        body.append(line[indent:])
    return "\n".join(body)


SCRIPT = _script()


def _notice(files: list[dict], comments: list[dict] | None = None) -> list[dict]:
    payload = {"script": SCRIPT, "files": files, "comments": comments or []}
    result = subprocess.run(
        ["node", "--input-type=module", "-e", HARNESS],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def _file(filename: str, status: str = "modified", **extra: str) -> dict[str, str]:
    return {"filename": filename, "status": status, **extra}


def test_own_added_modified_or_renamed_in_artifacts_post_notice() -> None:
    for artifact in (
        _file(".pr/design.html", "added"),
        _file(".pr/notes.md"),
        _file(".pr/notes.md", "renamed", previous_filename="docs/notes.md"),
    ):
        [comment] = _notice([_file("README.md"), artifact])
        assert comment["issue_number"] == 42
        assert "next release PR removes them" in comment["body"]


def test_removed_renamed_out_and_lookalike_paths_post_nothing() -> None:
    files = [
        _file(".pr/old.png", "removed"),
        _file("docs/notes.md", "renamed", previous_filename=".pr/notes.md"),
        _file(".pr-other/notes.md", "added"),
        _file("docs/.pr/notes.md", "added"),
        _file("README.md"),
    ]
    assert _notice(files) == []


def test_existing_notice_is_updated_in_place() -> None:
    existing = [{"id": 7, "body": f"{MARKER}\nold"}]
    [kept] = _notice([_file(".pr/notes.md")], existing)
    [cleared] = _notice([_file(".pr/notes.md", "removed")], existing)
    assert kept["comment_id"] == cleared["comment_id"] == 7
    assert "PR Artifacts Notice" in kept["body"]
    assert "PR Artifacts Cleaned Up" in cleared["body"]
    # Lines indented four or more spaces would render as a Markdown code block.
    for body in (kept["body"], cleared["body"]):
        assert not re.search(r"^ {4,}\S", body, re.MULTILINE)
