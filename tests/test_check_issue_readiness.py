from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_prod_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / ".github" / "scripts" / "check_issue_readiness.py"
    name = "check_issue_readiness"
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_prod = _load_prod_module()
evaluate_readiness = _prod.evaluate_readiness
extract_sections = _prod.extract_sections


ENHANCEMENT_READY = """### Problem or Use Case

The integration catalog lacks a Linear entry.

### Desired Behavior

`integrations/catalog/linear.json` describes the Linear MCP server so the
catalog build picks it up.

### Acceptance Criteria

- [ ] `npm run build:integrations` succeeds with the new entry
- [ ] `getIntegrationCatalogEntry("linear")` returns the Linear catalog model
"""

BUG_READY = """### Actual Behavior

Running `uv run --group test pytest tests/` fails in
`test_skills_catalog.py` with a KeyError when a skill is missing from the
marketplace.

### Acceptance Criteria

- [ ] `uv run --group test pytest tests/` passes with a clear error message
"""


def test_extract_sections_splits_on_headings():
    sections = extract_sections("### Alpha\n\ntext\n\n### Beta\n\nmore\n")
    assert sections["alpha"] == "\ntext\n\n"
    assert sections["beta"] == "\nmore\n"


def test_enhancement_ready_passes():
    result = evaluate_readiness(ENHANCEMENT_READY, ["enhancement"])
    assert result.ready is True
    assert result.reasons == []


def test_enhancement_missing_acceptance_criteria_fails():
    body = "### Desired Behavior\n\nSome desired change.\n"
    result = evaluate_readiness(body, ["enhancement"])
    assert result.ready is False
    assert any("Acceptance Criteria" in r for r in result.reasons)


def test_enhancement_missing_desired_behavior_fails():
    body = ENHANCEMENT_READY.replace(
        "### Desired Behavior\n\n"
        "`integrations/catalog/linear.json` describes the Linear MCP server so the\n"
        "catalog build picks it up.\n\n",
        "",
    )
    result = evaluate_readiness(body, ["enhancement"])
    assert result.ready is False
    assert any("Desired Behavior" in r for r in result.reasons)


def test_bug_ready_passes():
    result = evaluate_readiness(BUG_READY, ["bug"])
    assert result.ready is True
    assert result.reasons == []


def test_bug_missing_run_method_fails():
    body = BUG_READY.replace(
        "Running `uv run --group test pytest tests/` fails",
        "Running the test suite fails",
    )
    result = evaluate_readiness(body, ["bug"])
    assert result.ready is False
    assert any("reproducible command" in r for r in result.reasons)


def test_bug_npm_build_command_is_a_valid_run_method():
    body = BUG_READY.replace(
        "Running `uv run --group test pytest tests/` fails in\n"
        "`test_skills_catalog.py` with a KeyError when a skill is missing from the\n"
        "marketplace.",
        "Running `npm run build:skills` fails with a schema error.",
    )
    result = evaluate_readiness(body, ["bug"])
    assert result.ready is True
    assert result.reasons == []


def test_bug_acceptance_needs_checklist_item():
    body = BUG_READY.replace(
        "- [ ] `uv run --group test pytest tests/` passes with a clear error message",
        "Make the test error message clearer",
    )
    result = evaluate_readiness(body, ["bug"])
    assert result.ready is False
    assert any("checklist item" in r for r in result.reasons)


def test_no_response_field_counts_as_empty():
    body = BUG_READY.replace(
        "### Acceptance Criteria\n\n- [ ] `uv run --group test pytest tests/` "
        "passes with a clear error message\n",
        "### Acceptance Criteria\n\n_No response_\n",
    )
    result = evaluate_readiness(body, ["bug"])
    assert result.ready is False
    assert any("Acceptance Criteria" in r for r in result.reasons)


def test_no_bug_or_enhancement_label_not_ready():
    result = evaluate_readiness(ENHANCEMENT_READY, [])
    assert result.ready is False
    assert any("bug" in r and "enhancement" in r for r in result.reasons)
