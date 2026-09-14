"""Contracts for the shared GitHub automation foundation."""

import json

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
