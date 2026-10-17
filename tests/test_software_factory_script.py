"""The software-factory helper builds the same create body as Agent Canvas."""

import importlib.util
import io
import json
import tarfile
from pathlib import Path

import pytest
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
def test_create_body_matches_reference_renderer(factory, station, repos):
    entry = _entry(station)
    values = factory._form_values(entry, repos, {})
    expected = _render_payload(entry, values, "", selected_trigger="cron")
    assert factory._create_body(entry, values, repos) == expected


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
    config = factory._create_body(entry, values, ["acme/api"])["template"]["config"]
    assert config["max_new_per_run"] == 4
    assert config["review_tone"] == "thorough"
    assert config["repos"] == ["acme/api"]


def test_unknown_field_is_rejected(factory):
    with pytest.raises(factory.FactoryError):
        factory._form_values(_entry("github-issue-to-pr"), ["acme/api"], {"nope": 1})


@pytest.mark.parametrize("station", BUNDLE_STATIONS)
def test_tarball_holds_bundle_files_and_config(factory, station):
    bundle = _entry(station)["setup"]["bundle"]
    data = factory._tarball(ROOT, bundle["files"], {"repos": ["acme/api"]})
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        names = set(tar.getnames())
        config = json.load(tar.extractfile("config.json"))
    assert names == set(bundle["files"]) | {"config.json"}
    assert config == {"repos": ["acme/api"]}


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


def test_automation_backend_host_gets_a_clear_error(factory, monkeypatch):
    def not_found(*args, **kwargs):
        raise factory.FactoryError("GET http://localhost:18001/api/agent-profiles -> 404: {}")

    monkeypatch.setenv("OPENHANDS_HOST", "http://localhost:18001")
    monkeypatch.setenv("OPENHANDS_AUTOMATION_API_KEY", "key")
    monkeypatch.setattr(factory, "_request", not_found)
    with pytest.raises(factory.FactoryError, match="Ingress URL"):
        factory._profile(None)
