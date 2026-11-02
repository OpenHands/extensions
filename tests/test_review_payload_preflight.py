import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DISCLOSURE = "_This review was posted by an AI agent (OpenHands)._"
HEAD = "a" * 40


@pytest.fixture(scope="module")
def publication_command():
    main = ROOT / "skills/github-pr-reviewer/scripts/main.py"
    render = subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy, sys; from pathlib import Path; "
            "sys.path.insert(0, str(Path(sys.argv[1]).parent)); "
            "m = runpy.run_path(sys.argv[1]); "
            "print(m['_build_review_prompt']('owner/repo', {'number': 7}, "
            "'a' * 40, {}, github_token_secret='REVIEW_TOKEN'))",
            str(main),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    match = re.search(r"```sh\n(.*?)\n```", render.stdout, re.S)
    assert match, "The reviewer must receive an executable publication preflight"
    return match[1]


@pytest.fixture
def publication(tmp_path, publication_command):
    work = tmp_path / ".agent_tmp"
    work.mkdir()
    record = tmp_path / "submitted.json"
    gh = tmp_path / "gh"
    # Only the external GitHub transport is replaced; execute the shipped recipe.
    gh.write_text(
        f"#!{sys.executable}\n"
        "import json, pathlib, sys\n"
        f"pathlib.Path({str(record)!r}).write_text(json.dumps("
        "{'argv': sys.argv[1:], 'raw': sys.stdin.read()}))\n"
        "print(json.dumps({'id': 1, 'state': 'APPROVED'}))\n"
    )
    gh.chmod(0o755)

    def execute(raw):
        if raw is not None:
            (work / "review-payload.json").write_text(raw)
        result = subprocess.run(
            ["bash", "-c", publication_command],
            cwd=tmp_path,
            env={"HOME": str(tmp_path), "PATH": f"{tmp_path}:{os.environ['PATH']}"},
            capture_output=True,
            text=True,
        )
        return result, json.loads(record.read_text()) if record.exists() else None

    return execute


def payload(**changes):
    return {
        "commit_id": HEAD,
        "event": "APPROVE",
        "body": f"{DISCLOSURE}\n\nNo material findings.\n\n✅ APPROVED",
        **changes,
    }


@pytest.mark.parametrize("raw", [None, "", "{", "null", "[]"])
def test_unreadable_or_invalid_payload_never_submits(publication, raw):
    result, submitted = publication(raw)
    assert result.returncode != 0
    assert submitted is None


@pytest.mark.parametrize(
    "changes",
    [
        {"body": None},
        {"body": 7},
        {"body": ""},
        {"body": f"{DISCLOSURE}\\n\\n✅ APPROVED"},
        {"body": " \n\t"},
        {"body": DISCLOSURE},
        {"body": f"{DISCLOSURE}\n\n✅ APPROVED"},
        {"body": f"{DISCLOSURE}\n<!-- metadata only -->\n✅ APPROVED"},
        {"body": "No material findings.\n\n✅ APPROVED"},
        {"body": f"{DISCLOSURE}\nNo findings, but no verdict."},
        {"commit_id": "b" * 40},
        {"event": "REQUEST_CHANGES"},
        {"event": "APPROVE", "body": f"{DISCLOSURE}\nA defect.\n🔄 CHANGES REQUESTED"},
        {"body": None, "body_file": "/tmp/review.md"},
    ],
)
def test_contract_violation_never_submits(publication, changes):
    result, submitted = publication(json.dumps(payload(**changes)))
    assert result.returncode != 0
    assert submitted is None


@pytest.mark.parametrize(
    ("event", "verdict"),
    [
        ("APPROVE", "✅ APPROVED"),
        ("COMMENT", "✅ APPROVED"),
        ("COMMENT", "🔄 CHANGES REQUESTED"),
        ("COMMENT", "🛑 MAINTAINER DECISION REQUIRED"),
    ],
)
def test_valid_payload_submits_exact_validated_bytes(publication, event, verdict):
    raw = json.dumps(
        payload(
            event=event,
            body=f"{DISCLOSURE}\n\nAssessment with Unicode: café.\n\n{verdict}",
            comments=[{"path": "file.py", "line": 1, "side": "RIGHT", "body": "A defect."}],
        ),
        ensure_ascii=False,
        indent=2,
    )
    result, submitted = publication(raw)
    assert result.returncode == 0, result.stderr
    assert submitted["raw"] == raw
    assert submitted["argv"][:5] == [
        "api", "--method", "POST", "repos/owner/repo/pulls/7/reviews", "--input"
    ]
    assert submitted["argv"][5] == "-"


@pytest.mark.parametrize("separator", [" ", r"\n\n", "\n\n"])
def test_complete_assessment_format_is_preserved(publication, separator):
    body = f"{DISCLOSURE}{separator}No material findings.{separator}✅ APPROVED"
    raw = json.dumps(payload(body=body), ensure_ascii=False)
    result, submitted = publication(raw)
    assert result.returncode == 0, result.stderr
    assert submitted["raw"] == raw


def test_body_file_is_not_a_body(publication):
    raw = json.dumps({"commit_id": HEAD, "event": "APPROVE", "body_file": "review.md"})
    result, submitted = publication(raw)
    assert result.returncode != 0
    assert submitted is None
