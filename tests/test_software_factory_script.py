"""The software-factory helper builds plugin-spec automation requests."""

import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from test_automation_setup import _render_payload

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_STATIONS = [
    "github-issue-to-pr",
    "github-pr-reviewer",
    "github-agents-md-maintainer",
    "github-issue-triage",
    "github-delivery-watchdog",
    "github-stale-ci-pr-closer",
]


@pytest.fixture(scope="module")
def factory():
    path = ROOT / "skills" / "software-factory" / "scripts" / "factory.py"
    spec = importlib.util.spec_from_file_location("factory", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _entry(station: str) -> dict:
    return json.loads((ROOT / "automations" / "catalog" / station / "manifest.json").read_text())


@pytest.mark.parametrize("station", BUNDLE_STATIONS)
@pytest.mark.parametrize("repos", [["acme/api"], ["acme/api", "acme/web"]])
def test_create_body_uses_plugin_spec(factory, station, repos, monkeypatch):
    monkeypatch.setenv("OPENHANDS_HOST", "http://localhost:8000")
    entry = _entry(station)
    values = factory._form_values(entry, repos, {})
    body = factory._create_body(entry, values, repos, ROOT)
    rendered = _render_payload(entry, values, "", selected_trigger="cron")

    assert body["name"] == rendered["name"]
    assert body["trigger"] == rendered["trigger"]
    assert body["config"] == rendered["template"]["config"]
    assert body["template"] == rendered["template"]
    assert body["enabled"] is False
    assert body["plugin"] == {
        "source": str(ROOT),
        "repo_path": f"plugins/{station}",
    }
    assert body.get("timeout") == rendered.get("timeout")


def test_reviewer_plugin_schema_accepts_catalog_config(factory):
    entry = _entry("github-pr-reviewer")
    values = factory._form_values(entry, ["acme/api"], {"maxNewPerRun": 4})
    schema_path = ROOT / "plugins" / "github-pr-reviewer" / ".plugin" / "plugin.json"
    schema = json.loads(schema_path.read_text())["automation"]["config_schema"]
    validator = Draft202012Validator(schema)
    config = factory._station_config(entry, values)

    assert config["max_new_per_run"] == 4
    assert config["maintainers"] == ""
    assert not list(validator.iter_errors(config))
    assert validator.is_valid({**config, "maintainers": ["alice", "bob"]})
    assert validator.is_valid({**config, "maintainers": "alice, bob"})
    for invalid in (0, "4", True):
        assert not validator.is_valid({**config, "max_new_per_run": invalid})


@pytest.mark.parametrize("station", BUNDLE_STATIONS)
def test_every_token_secret_is_the_factory_token(factory, station):
    values = factory._form_values(_entry(station), ["acme/api"], {})
    if "githubTokenSecret" in values:
        assert values["githubTokenSecret"] == "GITHUB_PERSONAL_ACCESS_TOKEN"


def test_overrides_keep_json_types(factory):
    entry = _entry("github-pr-reviewer")
    values = factory._form_values(
        entry, ["acme/api"], {"maxNewPerRun": factory._parse_value("4"), "reviewTone": "thorough"}
    )
    config = factory._station_config(entry, values)
    assert config["max_new_per_run"] == 4
    assert config["review_tone"] == "thorough"
    assert config["repos"] == ["acme/api"]


def test_unknown_field_is_rejected(factory):
    with pytest.raises(factory.FactoryError):
        factory._form_values(_entry("github-issue-to-pr"), ["acme/api"], {"nope": 1})


def test_prs_keeps_only_branches_with_the_prefix(factory, monkeypatch):
    pulls = [
        {"number": 2, "title": "docs: add AGENTS.md", "html_url": "u2", "draft": True,
         "created_at": "2026-10-16T21:32:40Z", "head": {"ref": "openhands/agents-md-2026-W42"}},
        {"number": 3, "title": "feature", "html_url": "u3", "draft": False,
         "head": {"ref": "feature/x"}},
    ]
    monkeypatch.setattr(factory, "_github", lambda path: pulls)
    args = type("Args", (), {"repos": "acme/api", "branch_prefix": "openhands/agents-md"})
    assert factory.prs(args) == {
        "acme/api": [
            {"number": 2, "title": "docs: add AGENTS.md", "url": "u2", "draft": True,
             "created_at": "2026-10-16T21:32:40Z"}
        ]
    }


def test_automation_url_points_at_the_canvas_page(factory, monkeypatch):
    monkeypatch.setenv("OPENHANDS_HOST", "http://localhost:8000/")
    assert factory._automation_url("abc") == "http://localhost:8000/automations/abc"


def test_extensions_prefers_the_installed_checkout(factory, monkeypatch):
    """Bundles must come from the release the user has, not a moving main."""
    monkeypatch.delenv("FACTORY_EXTENSIONS", raising=False)
    monkeypatch.setattr(factory, "subprocess", None)  # a clone here would fail
    assert factory._extensions() == ROOT


def test_extensions_honours_the_override(factory, monkeypatch, tmp_path):
    monkeypatch.setenv("FACTORY_EXTENSIONS", str(tmp_path))
    assert factory._extensions() == tmp_path


def test_release_ref_is_none_without_installed_metadata(factory, monkeypatch):
    import importlib.metadata as md

    def missing(name):
        raise md.PackageNotFoundError(name)

    monkeypatch.setattr(md, "version", missing)
    assert factory._release_ref() is None


def test_plugin_ref_can_be_overridden(factory, monkeypatch):
    monkeypatch.setenv("FACTORY_EXTENSIONS_REF", "v9.9.9")
    monkeypatch.setenv("OPENHANDS_HOST", "https://app.all-hands.dev")
    assert factory._plugin_ref() == "v9.9.9"


def test_plugin_ref_falls_back_to_main_for_source_checkout(factory, monkeypatch):
    monkeypatch.delenv("FACTORY_EXTENSIONS_REF", raising=False)
    monkeypatch.setattr(factory, "_release_ref", lambda: None)
    assert factory._plugin_ref() == "main"


def test_automation_backend_host_gets_a_clear_error(factory, monkeypatch):
    def not_found(*args, **kwargs):
        raise factory.FactoryError("GET http://localhost:18001/api/agent-profiles -> 404: {}")

    monkeypatch.setenv("OPENHANDS_HOST", "http://localhost:18001")
    monkeypatch.setenv("OPENHANDS_AUTOMATION_API_KEY", "key")
    monkeypatch.setattr(factory, "_request", not_found)
    with pytest.raises(factory.FactoryError, match="Ingress URL"):
        factory._profile(None)


def _create_args(ids: str, repos: str = "acme/api", sets=None):
    return type("Args", (), {"ids": ids, "repos": repos, "set": sets, "profile": None})


def _stub_create(factory, monkeypatch, responses):
    """Stub upload/manifest/profile and record the POST bodies and PATCHes."""
    monkeypatch.setenv("OPENHANDS_HOST", "http://localhost:8000")
    monkeypatch.setattr(factory, "_extensions", lambda: ROOT)
    monkeypatch.setattr(factory, "_profile", lambda name: {"id": "p1", "name": "default"})
    posts = []
    patches = []

    def api(method, path, body=None, **kwargs):
        if method == "POST" and path == "/plugin-spec":
            posts.append(body)
            return responses[len(posts) - 1]
        if method == "PATCH":
            patches.append((path, body))
            return {"id": path.strip("/")}
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(factory, "_api", api)
    return posts, patches


def test_create_reports_existing_station_instead_of_claiming_it(factory, monkeypatch):
    """A 200 from the service means the template already exists, not a create."""
    responses = [
        (201, {"id": "a1", "enabled": False, "state": "INACTIVE"}),
        (200, {"id": "a2", "enabled": True, "state": "ACTIVE"}),
    ]
    posts, patches = _stub_create(factory, monkeypatch, responses)
    result = factory.create(_create_args("github-pr-reviewer,github-issue-to-pr"))
    assert [c["id"] for c in result["created"]] == ["a1"]
    assert [e["id"] for e in result["existing"]] == ["a2"]
    # The pre-existing automation is not disabled; it only gets the factory tag.
    assert patches == [("/a2", {"tags": ["software-factory"]})]
    assert result["not_tagged"] == []


def test_create_tags_every_new_station(factory, monkeypatch):
    posts, patches = _stub_create(factory, monkeypatch, [(201, {"id": "a1", "enabled": False})])
    factory.create(_create_args("github-pr-reviewer"))
    assert posts[0]["tags"] == ["software-factory"]
    assert patches == []


@pytest.mark.parametrize(
    "tags, expected_patches",
    [
        (["software-factory"], []),
        (["team-api"], [("/a2", {"tags": ["team-api", "software-factory"]})]),
    ],
)
def test_create_keeps_an_existing_station_s_own_tags(factory, monkeypatch, tags, expected_patches):
    """PATCH replaces the tag list, so the station's own tags are sent back."""
    responses = [(200, {"id": "a2", "enabled": False, "tags": tags})]
    posts, patches = _stub_create(factory, monkeypatch, responses)
    factory.create(_create_args("github-pr-reviewer"))
    assert patches == expected_patches


def test_create_reports_a_station_only_its_creator_can_tag(factory, monkeypatch):
    responses = [(200, {"id": "a2", "enabled": False, "tags": []})]
    _stub_create(factory, monkeypatch, responses)

    def forbidden(method, path, body=None, **kwargs):
        if method == "POST":
            return responses[0]
        raise factory.FactoryError(f"{method} {path} -> 403: {{}}", status=403)

    monkeypatch.setattr(factory, "_api", forbidden)
    result = factory.create(_create_args("github-pr-reviewer"))
    assert [e["id"] for e in result["existing"]] == ["a2"]
    assert [(e["id"], e["reason"]) for e in result["not_tagged"]] == [("a2", factory.NOT_CREATOR)]


def test_tag_adds_the_factory_tag_to_other_skills_stations(factory, monkeypatch):
    stored = {"j1": {"id": "j1", "tags": ["jira"]}, "l1": {"id": "l1", "tags": ["software-factory"]}}
    calls = []

    def api(method, path, body=None, **kwargs):
        calls.append((method, path, body))
        if method == "GET":
            return stored[path.strip("/")]
        if path == "/x1":
            raise factory.FactoryError("PATCH /x1 -> 403: {}", status=403)
        return {"id": path.strip("/"), **body}

    stored["x1"] = {"id": "x1", "tags": []}
    monkeypatch.setattr(factory, "_api", api)
    result = factory.tag(type("Args", (), {"ids": ["j1", "l1", "x1"]}))
    assert result == {"tagged": ["j1", "l1"], "not_tagged": [{"id": "x1", "reason": factory.NOT_CREATOR}]}
    assert ("PATCH", "/j1", {"tags": ["jira", "software-factory"]}) in calls
    assert not any(method == "PATCH" and path == "/l1" for method, path, _ in calls)


def test_tag_raises_errors_other_than_forbidden(factory, monkeypatch):
    def api(method, path, body=None, **kwargs):
        if method == "GET":
            return {"id": "a1", "tags": []}
        raise factory.FactoryError("PATCH /a1 -> 422: {}", status=422)

    monkeypatch.setattr(factory, "_api", api)
    with pytest.raises(factory.FactoryError, match="422"):
        factory.tag(type("Args", (), {"ids": ["a1"]}))


# FastAPI's 422 from an automation service older than tags, whose create and
# update bodies forbid unknown fields.
TAGS_FORBIDDEN = json.dumps(
    {
        "detail": [
            {
                "type": "extra_forbidden",
                "loc": ["body", "tags"],
                "msg": "Extra inputs are not permitted",
                "input": ["software-factory"],
            }
        ]
    }
)


def test_create_falls_back_to_untagged_on_a_service_without_tags(factory, monkeypatch):
    responses = [(201, {"id": "a1", "enabled": False}), (200, {"id": "a2", "enabled": False})]
    posts, patches = _stub_create(factory, monkeypatch, responses)
    accepts = factory._api

    def old_service(method, path, body=None, **kwargs):
        if body and "tags" in body:
            raise factory.FactoryError(f"{method} {path} -> 422", status=422, detail=TAGS_FORBIDDEN)
        return accepts(method, path, body, **kwargs)

    monkeypatch.setattr(factory, "_api", old_service)
    result = factory.create(_create_args("github-pr-reviewer,github-issue-to-pr"))
    assert all("tags" not in body for body in posts)
    assert [c["id"] for c in result["created"]] == ["a1"]
    assert [e["id"] for e in result["existing"]] == ["a2"]
    assert [(e["id"], e["reason"]) for e in result["not_tagged"]] == [
        ("a1", factory.TAGS_UNSUPPORTED),
        ("a2", factory.TAGS_UNSUPPORTED),
    ]
    assert patches == []


def test_create_raises_a_422_that_is_not_about_tags(factory, monkeypatch):
    _stub_create(factory, monkeypatch, [])
    missing = json.dumps({"detail": [{"type": "missing", "loc": ["body", "trigger"], "msg": "Field required"}]})

    def api(method, path, body=None, **kwargs):
        raise factory.FactoryError(f"{method} {path} -> 422: {missing}", status=422, detail=missing)

    monkeypatch.setattr(factory, "_api", api)
    with pytest.raises(factory.FactoryError, match="422"):
        factory.create(_create_args("github-pr-reviewer"))


def test_tag_reports_a_service_without_tags(factory, monkeypatch):
    def api(method, path, body=None, **kwargs):
        if method == "GET":
            return {"id": "a1"}
        raise factory.FactoryError(f"{method} {path} -> 422", status=422, detail=TAGS_FORBIDDEN)

    monkeypatch.setattr(factory, "_api", api)
    result = factory.tag(type("Args", (), {"ids": ["a1"]}))
    assert result == {"tagged": [], "not_tagged": [{"id": "a1", "reason": factory.TAGS_UNSUPPORTED}]}


def test_create_disables_a_station_the_service_returned_enabled(factory, monkeypatch):
    posts, patches = _stub_create(factory, monkeypatch, [(201, {"id": "a1", "enabled": True})])
    factory.create(_create_args("github-pr-reviewer"))
    assert patches == [("/a1", {"enabled": False})]


def test_tune_patches_schedule_without_stamping_template(factory, monkeypatch):
    """Tune must not go through create's template-id dedup path."""
    monkeypatch.setenv("OPENHANDS_HOST", "http://localhost:8000")
    monkeypatch.setattr(factory, "_find_existing", lambda station: {"id": "a1"})
    calls = []

    def api(method, path, body=None, **kwargs):
        calls.append((method, path, body))
        return {"id": "a1"}

    monkeypatch.setattr(factory, "_api", api)
    result = factory.tune(
        _create_args("github-pr-reviewer", sets=["schedule=0 * * * *"])
    )
    assert [t["id"] for t in result["tuned"]] == ["a1"]
    method, path, body = calls[-1]
    assert (method, path) == ("PATCH", "/a1")
    assert "template" not in body
    assert body == {
        "name": "GitHub code review - acme/api",
        "trigger": {"type": "cron", "schedule": "0 * * * *", "timezone": "UTC"},
    }


def test_tune_rejects_plugin_config_changes(factory, monkeypatch):
    monkeypatch.setenv("OPENHANDS_HOST", "http://localhost:8000")
    monkeypatch.setattr(factory, "_find_existing", lambda station: {"id": "a1"})
    with pytest.raises(factory.FactoryError, match="cannot be updated in place"):
        factory.tune(_create_args("github-pr-reviewer", sets=["reviewTone=thorough"]))


def test_tune_rejects_a_station_that_is_not_set_up(factory, monkeypatch):
    monkeypatch.setattr(factory, "_extensions", lambda: ROOT)
    monkeypatch.setattr(factory, "_find_existing", lambda station: None)
    with pytest.raises(factory.FactoryError, match="not set up yet"):
        factory.tune(_create_args("github-pr-reviewer"))


def test_find_existing_matches_on_template_id(factory, monkeypatch):
    page = {
        "automations": [
            {"id": "a1", "preset_metadata": {"template": {"id": "other"}}},
            {"id": "a2", "preset_metadata": {"template": {"id": "github-pr-reviewer"}}},
            {"id": "a3", "preset_metadata": None},
        ]
    }
    monkeypatch.setattr(factory, "_api", lambda method, path, **kwargs: page)
    assert factory._find_existing("github-pr-reviewer")["id"] == "a2"
    assert factory._find_existing("github-issue-to-pr") is None


def test_event_only_station_fields_do_not_raise(factory):
    """qa-changes declares only an event trigger; --set must report, not KeyError."""
    entry = _entry("qa-changes")
    assert factory._fields(entry) == entry["setup"]["form"]["args"]
    with pytest.raises(factory.FactoryError, match="no listed station has field"):
        factory._overrides({"qa-changes": entry}, ["reviewTone=thorough"], ["qa-changes"])
