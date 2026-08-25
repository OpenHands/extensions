from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_prod_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / ".github" / "scripts" / "check_pr_description.py"
    name = "check_pr_description"
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_prod = _load_prod_module()
validate_pr_body = _prod.validate_pr_body
body_from_event = _prod.body_from_event
extract_linked_issue_numbers = _prod.extract_linked_issue_numbers
validate_linked_issue_ready = _prod.validate_linked_issue_ready
fetch_issue_details = _prod.fetch_issue_details


VALID_BODY = """<!-- Keep this PR as draft until it is ready for review. -->

<!-- AI/LLM agents: be concise and specific. Do not check the box below. -->

- [ ] A human has tested these changes.

---

## Why

The repository had no readiness gate for issues or linked PRs.

## Summary

- Add ready-for-dev issue and PR readiness gates.

## Issue Number

Fixes #508

## How to Test

Run `uv run --group test pytest tests/`.

## Video/Screenshots

N/A

## Notes

N/A
"""


def test_valid_pr_body_passes():
    assert validate_pr_body(VALID_BODY) == []


def test_required_template_fields_must_be_present_and_filled():
    how_to_test = "## How to Test\n\nRun `uv run --group test pytest tests/`."
    body = VALID_BODY.replace(how_to_test, "## How to Test\n\n<!-- TODO -->")
    body = body.replace("## Summary", "## Details")

    errors = validate_pr_body(body)

    assert "Fill in the `## How to Test` section of the PR template." in errors
    assert "Keep the `## Summary` section from the PR template." in errors


def test_summary_placeholder_bullet_counts_as_empty():
    body = VALID_BODY.replace(
        "- Add ready-for-dev issue and PR readiness gates.", "-"
    )

    errors = validate_pr_body(body)

    assert "Fill in the `## Summary` section of the PR template." in errors


def test_optional_template_sections_may_be_removed():
    body = VALID_BODY.replace("## Issue Number\n\nFixes #508\n\n", "")
    body = body.split("## Video/Screenshots", maxsplit=1)[0]

    assert validate_pr_body(body) == []


def test_body_from_event_reads_pull_request_body(tmp_path: Path):
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps(
            {
                "pull_request": {"body": VALID_BODY},
                "repository": {"full_name": "org/repo"},
            }
        )
    )

    body, repo = body_from_event(event_path)
    assert body == VALID_BODY
    assert repo == "org/repo"


def test_extract_linked_issue_numbers_keyword_and_bare_ref():
    body = (
        "Fixes #12\n"
        "Closes #12 again\n"
        "resolves #34\n"
        "## Issue Number\n"
        "Issue: #56, see also #12\n"
    )
    assert extract_linked_issue_numbers(body) == [12, 34, 56]


def test_extract_linked_issue_numbers_only_bare_ref_in_issue_section():
    body = "## Summary\n\nSome work.\n\n## Issue Number\n\n#7\n"
    assert extract_linked_issue_numbers(body) == [7]


def test_extract_linked_issue_numbers_no_bare_ref_outside_issue_section():
    # A bare `#42` in the Summary must not be treated as a linked issue.
    body = "## Summary\n\nSee #42 for background.\n\n## Issue Number\n\nN/A\n"
    assert extract_linked_issue_numbers(body) == []


def test_extract_linked_issue_numbers_keyword_inside_word_is_ignored():
    # "fix"/"clos"/"resolv" must not match inside larger words (e.g. "crucifixes").
    body = (
        "## Summary\n\n"
        "crucifixes #12, encloses #34, transfixes #56.\n\n"
        "## Issue Number\n\nN/A\n"
    )
    assert extract_linked_issue_numbers(body) == []


def test_validate_linked_issue_ready_requires_a_number():
    errors = validate_linked_issue_ready(
        "## Issue Number\n\nN/A\n", "org/repo", "token"
    )
    assert errors and "Link an issue" in errors[0]


def test_validate_linked_issue_ready_no_token_skips_network(monkeypatch):
    def _fail(*args, **kwargs):
        raise AssertionError("should not call the network without a token")

    monkeypatch.setattr(_prod, "fetch_issue_details", _fail)
    assert validate_linked_issue_ready("Fixes #12\n", None, None) == []


def test_validate_linked_issue_ready_passes_with_ready_label(monkeypatch):
    monkeypatch.setattr(
        _prod,
        "fetch_issue_details",
        lambda repo, num, token: (["ready-for-dev"], "2026-08-25T00:00:00Z"),
    )
    assert validate_linked_issue_ready("Fixes #12\n", "org/repo", "token") == []


def test_validate_linked_issue_ready_grandfathers_pre_rollout_issue(monkeypatch):
    monkeypatch.setattr(
        _prod,
        "fetch_issue_details",
        lambda repo, num, token: (["bug"], "2026-01-15T00:00:00Z"),
    )
    assert validate_linked_issue_ready("Fixes #12\n", "org/repo", "token") == []


def test_validate_linked_issue_ready_grandfathers_rollout_day_before_deployment(
    monkeypatch,
):
    # Opened on the rollout day (2026-08-24) before the workflow was deployed,
    # so it was never labeled. It must be exempt.
    monkeypatch.setattr(
        _prod,
        "fetch_issue_details",
        lambda repo, num, token: (["bug"], "2026-08-24T06:46:00Z"),
    )
    assert validate_linked_issue_ready("Fixes #12\n", "org/repo", "token") == []


def test_validate_linked_issue_ready_fails_for_new_not_ready_issue(monkeypatch):
    monkeypatch.setattr(
        _prod,
        "fetch_issue_details",
        lambda repo, num, token: (["bug"], "2026-08-25T00:00:00Z"),
    )
    errors = validate_linked_issue_ready("Fixes #12\n", "org/repo", "token")
    assert errors and "ready-for-dev" in errors[0]


def test_validate_linked_issue_ready_new_unready_not_masked_by_ready_sibling(
    monkeypatch,
):
    def _issues(repo, num, token):
        # #12 carries ready-for-dev; #34 is new and not ready.
        if num == 34:
            return ["bug"], "2026-08-25T00:00:00Z"
        return ["ready-for-dev"], "2026-08-25T00:00:00Z"

    monkeypatch.setattr(_prod, "fetch_issue_details", _issues)
    body = "Fixes #12 and Closes #34"
    errors = validate_linked_issue_ready(body, "org/repo", "token")
    assert "#34" in errors[0]
    assert "ready-for-dev" in errors[0]


def test_validate_linked_issue_ready_returns_error_when_all_issues_not_found(
    monkeypatch,
):
    import urllib.error
    from http.client import HTTPMessage

    def _missing(repo, num, token):
        raise urllib.error.HTTPError(
            "https://api.github.com", 404, "Not Found", HTTPMessage(), None
        )

    monkeypatch.setattr(_prod, "fetch_issue_details", _missing)
    errors = validate_linked_issue_ready("Fixes #12\n", "org/repo", "token")
    assert errors and "could not be found" in errors[0]
