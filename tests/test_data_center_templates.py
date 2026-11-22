"""The Data Center templates' event filters, run against representative payloads.

The automation service evaluates a filter with JMESPath against the raw webhook
payload that the instance's built-in Jira Data Center or Bitbucket Data Center
integration forwards, with the built-in functions plus its own. The Jira filter
uses only built-in functions; the Bitbucket filter also calls the service's
`lower`, which `SERVICE_OPTIONS` reproduces (`FilterFunctions` in
openhands/automation/filter_eval.py).

`fixtures/bitbucket-data-center/pr-opened.json` keeps the shape of a pull request
delivery recorded by a Bitbucket Data Center 9.4.19 server, with its names and
host replaced. Its clone links spell the project key in lower case while
`project.key` is upper case, as that server sends them.
"""

import json
from copy import deepcopy
from pathlib import Path

import jmespath
import pytest
from jmespath import functions
from test_automation_setup import _context, _interpolate


ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "automations" / "catalog"
PR_OPENED = json.loads(
    (ROOT / "tests" / "fixtures" / "bitbucket-data-center" / "pr-opened.json").read_text()
)


class _ServiceFunctions(functions.Functions):
    @functions.signature({"types": ["string"]})
    def _func_lower(self, subject: str) -> str:
        return subject.lower()


SERVICE_OPTIONS = jmespath.Options(custom_functions=_ServiceFunctions())


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
    """The recorded delivery, retargeted at another event, state or repository."""
    payload = deepcopy(PR_OPENED)
    payload["eventKey"] = event_key
    pull_request = payload["pullRequest"]
    pull_request["draft"] = draft
    for ref in ("fromRef", "toRef"):
        repository = pull_request[ref]["repository"]
        repository["project"]["key"] = project
        repository["slug"] = slug
        repository["links"]["clone"] = [
            {"href": f"https://bitbucket.example.com/scm/{project.lower()}/{slug}.git", "name": "http"},
            {"href": f"ssh://git@bitbucket.example.com:7999/{project.lower()}/{slug}.git", "name": "ssh"},
        ]
    return payload


def _without_draft(payload):
    payload["pullRequest"].pop("draft")
    return payload


# What the repository picker stores: the clone URL on the connected host, with
# the project key as the server lists it.
PICKED = "https://bitbucket.example.com/scm/ENG/payments.git"

BITBUCKET_CASES = [
    ("opened", PICKED, _pull_request("pr:opened"), True),
    ("new commits pushed", PICKED, _pull_request("pr:from_ref_updated"), True),
    ("a server without draft pull requests", PICKED, _without_draft(_pull_request("pr:opened")), True),
    ("the clone URL the server shows, in lower case", "https://bitbucket.example.com/scm/eng/payments.git", _pull_request("pr:opened"), True),
    ("a clone URL without .git", "https://bitbucket.example.com/scm/ENG/payments", _pull_request("pr:opened"), True),
    ("a server under a context path", "https://example.com/bitbucket/scm/ENG/payments.git", _pull_request("pr:opened"), True),
    (
        "a personal repository",
        "https://bitbucket.example.com/scm/~developer/sandbox.git",
        _pull_request("pr:opened", project="~DEVELOPER", slug="sandbox"),
        True,
    ),
    ("a draft opened", PICKED, _pull_request("pr:opened", draft=True), False),
    ("another repository", PICKED, _pull_request("pr:opened", slug="web"), False),
    ("a repository whose name extends the configured one", PICKED, _pull_request("pr:opened", slug="payments-api"), False),
    (
        "the configured name extending the repository's",
        "https://bitbucket.example.com/scm/ENG/payments-api.git",
        _pull_request("pr:opened"),
        False,
    ),
    ("another project", PICKED, _pull_request("pr:opened", project="OPS"), False),
    ("a comment added", PICKED, _pull_request("pr:comment:added"), False),
    ("merged", PICKED, _pull_request("pr:merged"), False),
]


@pytest.mark.parametrize(
    ("repository", "payload", "expected"), [c[1:] for c in BITBUCKET_CASES], ids=[c[0] for c in BITBUCKET_CASES]
)
def test_bitbucket_filter_matches_new_heads_of_the_repository(repository: str, payload: dict, expected: bool) -> None:
    expression = _filter("bitbucket-data-center-pr-reviewer", {"repository": repository})

    assert bool(jmespath.search(expression, payload, options=SERVICE_OPTIONS)) is expected
