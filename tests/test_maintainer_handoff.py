"""Deterministic maintainer selection for positive automated reviews."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

_MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills/github-pr-reviewer/scripts/maintainer_handoff.py"
)
_SPEC = importlib.util.spec_from_file_location("maintainer_handoff_test", _MODULE_PATH)
assert _SPEC and _SPEC.loader
maintainer_handoff = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(maintainer_handoff)


def _pr(**overrides):
    result = {
        "number": 7,
        "head": {"sha": "head"},
        "base": {
            "ref": "main",
            "repo": {"owner": {"type": "Organization"}},
        },
        "user": {"login": "author"},
        "requested_reviewers": [],
    }
    result.update(overrides)
    return result


def _repository(commits=None, reviews=None, loads=None):
    commits = commits or {}
    loads = loads or {}

    def gh_pages(path):
        if path.endswith("/files"):
            return [{"filename": name} for name in commits]
        if path.endswith("/reviews"):
            return reviews or []
        raise AssertionError(path)

    def gh(method, path, body=None):
        if path.startswith("/commits?"):
            filename = parse_qs(urlsplit(path).query)["path"][0]
            return [{"author": {"login": login}} for login in commits[filename]]
        if method == "POST" and path.endswith("/requested_reviewers"):
            return {}
        raise AssertionError((method, path, body))

    def api(method, path, params=None, body=None):
        assert (method, path) == ("GET", "/search/issues")
        login = params["q"].rsplit(":", 1)[1]
        return {"total_count": loads.get(login, 0)}

    return SimpleNamespace(
        repository="OpenHands/OpenHands",
        token="token",
        gh_pages=gh_pages,
        gh=Mock(side_effect=gh),
        api=Mock(side_effect=api),
    )


def test_code_proximity_precedes_review_load():
    repo = _repository(
        {"src/api.py": ["VascoSch92", "VascoSch92", "neubig"]},
        loads={"VascoSch92": 8, "neubig": 0},
    )

    selected = maintainer_handoff.request_maintainer_review(
        repo, _pr(), ["neubig", "VascoSch92"]
    )

    assert selected == "VascoSch92"
    assert repo.gh.call_args_list[-1].args[:2] == (
        "POST",
        "/pulls/7/requested_reviewers",
    )
    assert repo.gh.call_args_list[-1].args[2] == {"reviewers": ["VascoSch92"]}


def test_review_load_breaks_equal_proximity():
    repo = _repository({"src/api.py": []}, loads={"VascoSch92": 1, "neubig": 4})

    selected = maintainer_handoff.request_maintainer_review(
        repo, _pr(), ["neubig", "VascoSch92"]
    )

    assert selected == "VascoSch92"


def test_review_load_uses_user_qualifier_for_user_owned_repo():
    repo = _repository({"src/api.py": []}, loads={"VascoSch92": 1, "neubig": 4})
    repo.repository = "neubig/project"
    pr = _pr(base={"ref": "main", "repo": {"owner": {"type": "User"}}})

    maintainer_handoff.request_maintainer_review(
        repo, pr, ["neubig", "VascoSch92"]
    )

    assert all(
        "user:neubig" in call.kwargs["params"]["q"]
        for call in repo.api.call_args_list
    )


def test_existing_request_is_idempotent():
    repo = _repository()
    pr = _pr(requested_reviewers=[{"login": "VascoSch92"}])

    selected = maintainer_handoff.request_maintainer_review(
        repo, pr, ["neubig", "VascoSch92"]
    )

    assert selected == "VascoSch92"
    repo.api.assert_not_called()
    repo.gh.assert_not_called()


def test_author_is_excluded_and_empty_roster_is_compatible():
    repo = _repository({"src/api.py": ["neubig"]})

    selected = maintainer_handoff.request_maintainer_review(
        repo,
        _pr(user={"login": "neubig"}),
        ["neubig", "VascoSch92"],
    )

    assert selected == "VascoSch92"
    assert maintainer_handoff.request_maintainer_review(repo, _pr(), "") is None


def test_unassignable_maintainer_is_a_configuration_error():
    repo = _repository({"src/api.py": []})
    original_gh = repo.gh.side_effect

    def fail_assignment(method, path, body=None):
        if method == "POST":
            raise HTTPError("url", 422, "invalid reviewer", {}, None)
        return original_gh(method, path, body)

    repo.gh.side_effect = fail_assignment

    try:
        maintainer_handoff.request_maintainer_review(repo, _pr(), ["neubig"])
    except maintainer_handoff.HandoffConfigurationError as exc:
        assert "@neubig" in str(exc)
    else:
        raise AssertionError("expected HandoffConfigurationError")
