"""Contracts for the shared GitHub automation foundation."""

import json
from urllib.error import HTTPError

import github_client
import pytest


def test_repository_runs_are_isolated(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["worker.py"])
    (tmp_path / "config.json").write_text(
        json.dumps(
            {
                "repos": ["owner/failed", "owner/next"],
                "github_token_secret": "GITHUB_TOKEN",
            }
        )
    )
    visited = []

    class Automation:
        def __init__(self, *, repository, github_token_secret, conversation):
            assert github_token_secret == "GITHUB_TOKEN"
            self.repository = repository

        def run(self):
            visited.append(self.repository)
            if self.repository == "owner/failed":
                raise TimeoutError

    with pytest.raises(RuntimeError, match="owner/failed"):
        github_client.run_repositories(Automation)

    assert visited == ["owner/failed", "owner/next"]


def test_pagination_rejects_a_non_list_response(monkeypatch):
    monkeypatch.setattr(
        github_client, "github_request", lambda *args, **kwargs: ({}, {})
    )

    with pytest.raises(TypeError, match="paginated GitHub list"):
        github_client.github_paginate("token", "/repos/owner/repo/issues")


@pytest.mark.parametrize(
    "state,reason,expected",
    [
        ("closed", "completed", True),
        ("closed", "not_planned", False),
        ("open", None, False),
    ],
)
def test_dependencies_must_be_completed(state, reason, expected):
    repository = object.__new__(github_client.GitHubRepository)
    repository._completed_dependencies = {}
    repository.gh = lambda *args: {"state": state, "state_reason": reason}

    assert repository.dependencies_complete({"body": "Depends on: #12"}) is expected


def test_dependency_permission_errors_fail_closed():
    repository = object.__new__(github_client.GitHubRepository)
    repository._completed_dependencies = {}

    def denied(*args):
        raise HTTPError("https://api.github.com", 403, "Forbidden", {}, None)

    repository.gh = denied
    with pytest.raises(HTTPError):
        repository.dependencies_complete({"body": "Depends on: #12"})


def test_check_runs_reads_every_page_of_the_object_response():
    """The endpoint answers with an object, not a list, so paging is manual."""
    repository = object.__new__(github_client.GitHubRepository)
    pages = {
        1: {"total_count": 3, "check_runs": [{"name": "a"}, {"name": "b"}]},
        2: {"total_count": 3, "check_runs": [{"name": "c"}]},
    }
    requests = []

    def gh(method, path, body=None):
        assert method == "GET"
        page = int(path.rsplit("page=", 1)[1])
        requests.append(page)
        return pages[page]

    repository.gh = gh

    assert [run["name"] for run in repository.check_runs("abc")] == ["a", "b", "c"]
    assert requests == [1, 2]


def test_check_runs_stops_on_an_empty_first_page():
    repository = object.__new__(github_client.GitHubRepository)
    repository.gh = lambda *args, **kwargs: {"total_count": 0, "check_runs": []}

    assert repository.check_runs("abc") == []


def test_workflow_runs_reads_every_page_of_the_object_response():
    """The runs endpoint answers with an object too, so paging is manual."""
    repository = object.__new__(github_client.GitHubRepository)
    pages = {
        1: {"total_count": 3, "workflow_runs": [{"name": "a"}, {"name": "b"}]},
        2: {"total_count": 3, "workflow_runs": [{"name": "c"}]},
    }
    requests = []

    def gh(method, path, body=None):
        assert method == "GET"
        assert "head_sha=abc" in path
        page = int(path.rsplit("page=", 1)[1])
        requests.append(page)
        return pages[page]

    repository.gh = gh

    assert [run["name"] for run in repository.workflow_runs("abc")] == [
        "a",
        "b",
        "c",
    ]
    assert requests == [1, 2]
