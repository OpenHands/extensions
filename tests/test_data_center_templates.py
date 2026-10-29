"""The Data Center templates' event filters, run against representative payloads.

The automation service evaluates a filter with JMESPath against the raw webhook
payload that the instance's built-in Jira Data Center or Bitbucket Data Center
integration forwards. These filters use only built-in JMESPath functions, so
plain `jmespath` evaluates them the way the service does.
"""

import json
from pathlib import Path

import jmespath
import pytest
from test_automation_setup import _context, _interpolate


ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "automations" / "catalog"


def _filter(automation_id: str, form_values: dict) -> str:
    entry = json.loads((CATALOG_DIR / automation_id / "manifest.json").read_text())
    return _interpolate(entry["setup"]["filter"], _context(entry, form_values))


def _issue(labels, project="ENG"):
    return {
        "key": "ENG-1",
        "self": "https://jira.example.com/rest/api/2/issue/10001",
        "fields": {"project": {"key": project}, "labels": labels, "summary": "Fix it"},
    }


def _labels_changed(from_string, to_string):
    return {"items": [{"field": "labels", "fromString": from_string, "toString": to_string}]}


JIRA_CASES = [
    ("created with the label", {"webhookEvent": "jira:issue_created", "issue": _issue(["openhands"])}, True),
    ("created without the label", {"webhookEvent": "jira:issue_created", "issue": _issue(["bug"])}, False),
    ("created in another project", {"webhookEvent": "jira:issue_created", "issue": _issue(["openhands"], "OPS")}, False),
    (
        "the label added",
        {"webhookEvent": "jira:issue_updated", "issue": _issue(["bug", "openhands"]), "changelog": _labels_changed("bug", "bug openhands")},
        True,
    ),
    (
        "the first label added",
        {"webhookEvent": "jira:issue_updated", "issue": _issue(["openhands"]), "changelog": _labels_changed(None, "openhands")},
        True,
    ),
    (
        "a label that only contains it added",
        {"webhookEvent": "jira:issue_updated", "issue": _issue(["openhands-review"]), "changelog": _labels_changed("", "openhands-review")},
        False,
    ),
    (
        "another label added to a labelled issue",
        {"webhookEvent": "jira:issue_updated", "issue": _issue(["openhands", "bug"]), "changelog": _labels_changed("openhands", "bug openhands")},
        False,
    ),
    (
        "a labelled issue edited",
        {
            "webhookEvent": "jira:issue_updated",
            "issue": _issue(["openhands"]),
            "changelog": {"items": [{"field": "summary", "fromString": "a", "toString": "b"}]},
        },
        False,
    ),
    ("an update without a changelog", {"webhookEvent": "jira:issue_updated", "issue": _issue(["openhands"])}, False),
    ("deleted", {"webhookEvent": "jira:issue_deleted", "issue": _issue(["openhands"])}, False),
]


@pytest.mark.parametrize(("payload", "expected"), [c[1:] for c in JIRA_CASES], ids=[c[0] for c in JIRA_CASES])
def test_jira_filter_matches_each_labelling_once(payload: dict, expected: bool) -> None:
    expression = _filter(
        "jira-data-center-issue-to-bitbucket-data-center-pr",
        {"jiraProject": "ENG", "triggerLabel": "openhands"},
    )

    assert bool(jmespath.search(expression, payload)) is expected


def _pull_request(event_key, *, draft=False, project="ENG", slug="payments"):
    return {
        "eventKey": event_key,
        "pullRequest": {
            "id": 7,
            "draft": draft,
            "toRef": {"repository": {"slug": slug, "project": {"key": project}}},
            "fromRef": {"latestCommit": "0123abcd"},
        },
    }


def _without_draft(payload):
    payload["pullRequest"].pop("draft")
    return payload


BITBUCKET_CASES = [
    ("opened", _pull_request("pr:opened"), True),
    ("new commits pushed", _pull_request("pr:from_ref_updated"), True),
    ("a server without draft pull requests", _without_draft(_pull_request("pr:opened")), True),
    ("a draft opened", _pull_request("pr:opened", draft=True), False),
    ("another repository", _pull_request("pr:opened", slug="web"), False),
    ("another project", _pull_request("pr:opened", project="OPS"), False),
    ("a comment added", _pull_request("pr:comment:added"), False),
    ("merged", _pull_request("pr:merged"), False),
]


@pytest.mark.parametrize(("payload", "expected"), [c[1:] for c in BITBUCKET_CASES], ids=[c[0] for c in BITBUCKET_CASES])
def test_bitbucket_filter_matches_new_heads_of_the_repository(payload: dict, expected: bool) -> None:
    expression = _filter("bitbucket-data-center-pr-reviewer", {"repository": "ENG/payments"})

    assert bool(jmespath.search(expression, payload)) is expected
