#!/usr/bin/env python3
"""Deterministic helpers for the software-factory skill (stdlib only, no LLM).

Each command prints one JSON document on stdout and exits non-zero on failure.

  factory.py preflight --repos owner/a,owner/b [--provider github|gitlab] [--gitlab-api-url URL] [--profile NAME]
  factory.py create --repos owner/a --ids ID[,ID...] [--provider github|gitlab] [--gitlab-api-url URL] [--trigger event --event-source SOURCE] [--set [ID.]FIELD=VALUE ...] [--profile NAME]
  factory.py tune --repos owner/a --ids ID[,ID...] [--provider github|gitlab] [--gitlab-api-url URL] [--trigger cron|event --event-source SOURCE] [--set [ID.]FIELD=VALUE ...] [--profile NAME]
  factory.py tag ID [ID ...]
  factory.py verify ID [ID ...] [--no-wait ID ...] [--timeout SECONDS]
  factory.py status ID [ID ...]
  factory.py prs --repos owner/a [--branch-prefix openhands/agents-md]
  factory.py reset-token

Environment:
  OPENHANDS_HOST                  automation host, as the openhands-automation skill determines it
  OPENHANDS_API_KEY               Bearer auth (OpenHands Cloud)
  OPENHANDS_AUTOMATION_API_KEY    X-Session-API-Key auth (local Agent Canvas; SESSION_API_KEY also works)
  GITHUB_PERSONAL_ACCESS_TOKEN    GitHub token; read, never printed
  GITLAB_TOKEN                    GitLab token; read, never printed
  FACTORY_EXTENSIONS              catalog checkout; defaults to the package this script ships in
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

TOKEN_SECRETS = {"github": "GITHUB_PERSONAL_ACCESS_TOKEN", "gitlab": "GITLAB_TOKEN"}
TOKEN_SECRET = TOKEN_SECRETS["github"]
GITLAB_API_URL = "https://gitlab.com/api/v4"
EXTENSIONS_URL = "https://github.com/OpenHands/extensions"
PLACEHOLDER_RE = re.compile(r"\{\{([a-z]+)\.([A-Za-z0-9_.]+)\}\}")
STATIONS = {
    "github": (
        "github-issue-to-pr",
        "github-pr-reviewer",
        "github-agents-md-maintainer",
        "github-issue-triage",
        "github-delivery-watchdog",
        "github-stale-ci-pr-closer",
        "qa-changes",
    ),
    "gitlab": ("gitlab-issue-to-mr", "gitlab-mr-reviewer", "gitlab-prd-refiner"),
}
TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "SKIPPED"}
# Every station carries this tag, so the Automations list can filter to the factory.
FACTORY_TAG = "software-factory"
# Why a station could not get the factory tag (reported under not_tagged).
NOT_CREATOR = "only its creator can change its tags"
TAGS_UNSUPPORTED = "this automation service does not support tags yet"


class FactoryError(Exception):
    def __init__(self, message: str, status: int | None = None, detail: str = "", **extra):
        super().__init__(message)
        self.status = status
        self.detail = detail
        self.extra = extra


# --- HTTP -------------------------------------------------------------------


def _host() -> str:
    host = os.environ.get("OPENHANDS_HOST", "").rstrip("/")
    if not host:
        raise FactoryError("set OPENHANDS_HOST (see the openhands-automation skill)")
    return host


def _auth() -> dict:
    local = urllib.parse.urlparse(_host()).hostname in ("localhost", "127.0.0.1", "::1")
    session = os.environ.get("OPENHANDS_AUTOMATION_API_KEY") or os.environ.get("SESSION_API_KEY")
    bearer = os.environ.get("OPENHANDS_API_KEY")
    if session and (local or not bearer):
        return {"X-Session-API-Key": session}
    if bearer:
        return {"Authorization": f"Bearer {bearer}"}
    raise FactoryError(
        "no automation API key: name OPENHANDS_API_KEY or OPENHANDS_AUTOMATION_API_KEY"
        " in the command so the agent server passes the saved secret in"
    )


def _request(
    method: str,
    url: str,
    body=None,
    headers=None,
    raw: bytes | None = None,
    return_status: bool = False,
):
    headers = dict(headers or {})
    data = raw
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            status_code = resp.status
            text = resp.read().decode()
    except urllib.error.HTTPError as err:
        with err:
            detail = err.read().decode()[:2000]
        raise FactoryError(f"{method} {url} -> {err.code}: {detail}", status=err.code, detail=detail) from None
    except urllib.error.URLError as err:
        raise FactoryError(f"{method} {url} -> {err.reason}") from None
    payload = json.loads(text) if text.strip() else None
    # The status distinguishes a fresh create (201) from the 200 the service
    # returns when the same template already exists in the organization.
    return (status_code, payload) if return_status else payload


def _api(
    method: str,
    path: str,
    body=None,
    raw: bytes | None = None,
    headers=None,
    return_status: bool = False,
):
    return _request(
        method,
        f"{_host()}/api/automation/v1{path}",
        body,
        {**_auth(), **(headers or {})},
        raw,
        return_status,
    )


def _github(path: str):
    token = os.environ.get(TOKEN_SECRET)
    if not token:
        raise FactoryError(f"{TOKEN_SECRET} is not set")
    return _request(
        "GET",
        f"https://api.github.com{path}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "openhands-software-factory",
        },
    )


def _gitlab_api_url(value: str) -> str:
    parsed = urllib.parse.urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.path.rstrip("/") != "/api/v4"):
        raise FactoryError("GitLab API URL must be an HTTPS /api/v4 root without credentials")
    return value.rstrip("/")


def _gitlab(path: str, api_url: str):
    token = os.environ.get(TOKEN_SECRETS["gitlab"])
    if not token:
        raise FactoryError("GITLAB_TOKEN is not set")
    return _request("GET", api_url + path, headers={"PRIVATE-TOKEN": token})


def _gitlab_project(repo: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)+", repo):
        raise FactoryError(f"invalid GitLab project: {repo!r}; use group/subgroup/project")
    return urllib.parse.quote(repo, safe="")


# --- Catalog ----------------------------------------------------------------


def _extensions() -> Path:
    """The checkout that holds `automations/catalog`.

    Prefer the installed package or working copy this script lives in, so a
    factory installs the bundles that shipped with the release the user has,
    rather than whatever `main` happens to be at run time. A bare copy of this
    script falls back to a shallow clone, pinned to the release tag when the
    installed version is known.
    """
    override = os.environ.get("FACTORY_EXTENSIONS")
    if override:
        return Path(override)
    installed = Path(__file__).resolve().parents[3]
    if (installed / "automations" / "catalog").is_dir():
        return installed
    root = Path("/tmp/software-factory/extensions")
    if not (root / "automations" / "catalog").is_dir():
        root.parent.mkdir(parents=True, exist_ok=True)
        ref = _release_ref()
        cmd = ["git", "clone", "-q", "--depth", "1"]
        if ref:
            cmd += ["--branch", ref]
        subprocess.run([*cmd, EXTENSIONS_URL, str(root)], check=True)
    return root


def _release_ref() -> str | None:
    """The `vX.Y.Z` tag matching the installed package, if it is known."""
    try:
        from importlib.metadata import PackageNotFoundError, version

        return f"v{version('openhands-extensions')}"
    except Exception:
        return None


def _manifest(station: str) -> dict:
    path = _extensions() / "automations" / "catalog" / station / "manifest.json"
    if not path.is_file():
        raise FactoryError(f"unknown station: {station}")
    return json.loads(path.read_text())


def _needs_profile(entry: dict) -> bool:
    return "agentProfiles" in entry.get("requires", {}).get("features", [])


def _resolve(namespace: str, key: str, context: dict):
    value = context[namespace]
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise FactoryError(f"unresolved placeholder {{{{{namespace}.{key}}}}}")
        value = value[part]
    return value


def _interpolate(node, context: dict):
    if isinstance(node, dict):
        return {k: _interpolate(v, context) for k, v in node.items()}
    if isinstance(node, list):
        return [_interpolate(v, context) for v in node]
    if not isinstance(node, str):
        return node
    whole = PLACEHOLDER_RE.fullmatch(node)
    if whole:
        return _resolve(whole.group(1), whole.group(2), context)
    return PLACEHOLDER_RE.sub(lambda m: str(_resolve(m.group(1), m.group(2), context)), node)


def _parse_value(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def _fields(entry: dict, trigger: str = "cron") -> dict:
    form = entry["setup"]["form"]
    return {**form.get("args", {}), **form.get("triggers", {}).get(trigger, {})}


def _form_values(entry: dict, repos: list[str], overrides: dict, gitlab_api_url: str | None = None,
                 trigger: str = "cron", event_source: str | None = None) -> dict:
    """Answers, else derived values, else manifest defaults."""
    fields = _fields(entry, trigger)
    values = {name: spec["default"] for name, spec in fields.items() if "default" in spec}
    for name, spec in fields.items():
        if spec.get("type") == "repo-picker":
            values[name] = repos if spec.get("multiple") else repos[0]
    if "githubTokenSecret" in fields:
        values["githubTokenSecret"] = TOKEN_SECRET
    if gitlab_api_url and "gitlabApiUrl" in fields:
        values["gitlabApiUrl"] = _gitlab_api_url(gitlab_api_url)
    if trigger == "event":
        values["source"] = event_source
    for name, value in overrides.items():
        if name not in fields:
            raise FactoryError(f"{entry['id']} has no field {name}")
        values[name] = value
    if gitlab_api_url and "gitlabApiUrl" in fields and values["gitlabApiUrl"] != gitlab_api_url:
        raise FactoryError(f"{entry['id']} must use --gitlab-api-url for this instance")
    missing = [n for n, s in fields.items() if s.get("required") and values.get(n) in (None, "", [])]
    if missing:
        raise FactoryError(f"{entry['id']} is missing required fields: {missing}")
    return values


def _create_body(entry: dict, values: dict, repos: list[str], selected_trigger: str = "cron") -> dict:
    """The create request, as Agent Canvas builds it for a catalog bundle."""
    bundle = entry["setup"]["bundle"]
    name = entry["name"] + (f" - {repos[0]}" if len(repos) == 1 else f" - {len(repos)} repositories")
    if selected_trigger == "event":
        trigger = {"type": "event", "source": values["source"], "on": values["on"]}
        if entry["setup"].get("filter"):
            trigger["filter"] = entry["setup"]["filter"]
    else:
        trigger = {"type": "cron", "schedule": values["schedule"], "timezone": values["timezone"]}
    body = {
        "name": name,
        "trigger": trigger,
        "tarball_path": "",
        "entrypoint": bundle["entrypoint"],
    }
    if "setupScript" in bundle:
        body["setup_script_path"] = bundle["setupScript"]
    if "timeout" in bundle:
        body["timeout"] = bundle["timeout"]
    body["template"] = {
        "id": entry["id"],
        "version": bundle["version"],
        "config": _interpolate(bundle["config"], {"form": values, "automation": entry}),
    }
    return body


def _tarball(root: Path, files: dict, config: dict) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for archive_name, repo_path in files.items():
            tar.add(str((root / repo_path).resolve()), arcname=archive_name)
        data = json.dumps(config, indent=2).encode()
        info = tarfile.TarInfo("config.json")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _upload(name: str, data: bytes) -> str:
    upload = _api(
        "POST",
        f"/uploads?name={urllib.parse.quote(name)}",
        raw=data,
        headers={"Content-Type": "application/gzip"},
    )
    deadline = time.time() + 120
    while upload.get("status") == "UPLOADING" and time.time() < deadline:
        time.sleep(2)
        upload = _api("GET", f"/uploads/{upload['id']}")
    if upload.get("status") not in (None, "COMPLETED") or not upload.get("tarball_path"):
        raise FactoryError(f"upload of {name} failed: {upload.get('error_message') or upload}")
    return upload["tarball_path"]


# --- Agent profile ----------------------------------------------------------


def _profile(name: str | None) -> dict:
    try:
        listing = _request("GET", f"{_host()}/api/agent-profiles", headers=_auth())
    except FactoryError as err:
        if " -> 404" in str(err):
            raise FactoryError(
                "OPENHANDS_HOST serves no /api/agent-profiles: on a local Agent Canvas use the"
                " Ingress URL from <RUNTIME_SERVICES>, not the automation backend"
            ) from None
        raise
    profiles = listing.get("profiles", [])
    wanted = name or listing.get("active_agent_profile_id")
    match = next((p for p in profiles if wanted in (p.get("id"), p.get("name"))), None)
    if not match:
        raise FactoryError(f"agent profile not found: {wanted}")
    if match.get("agent_kind") == "acp":
        raise FactoryError(f"agent profile {match['name']} is an ACP profile")
    detail = _request(
        "GET",
        f"{_host()}/api/agent-profiles/{urllib.parse.quote(match['name'])}",
        headers=_auth(),
    )
    refs = (detail or {}).get("profile", {}).get("secret_refs")
    if refs is not None and TOKEN_SECRET not in json.dumps(refs):
        raise FactoryError(f"agent profile {match['name']} does not allow {TOKEN_SECRET}")
    return {"id": match["id"], "name": match["name"]}


# --- Commands ---------------------------------------------------------------


def preflight(args) -> dict:
    provider = getattr(args, "provider", "github")
    api_url = _gitlab_api_url(args.gitlab_api_url) if provider == "gitlab" else None
    capabilities = _api("GET", "/capabilities")
    features = set(capabilities.get("features", []))
    out: dict = {"stations": {}}
    if provider == "gitlab":
        out["event_supported"] = "event" in capabilities.get("triggerKinds", [])
        out["event_sources"] = capabilities.get("eventSources", [])
    for station in STATIONS[provider]:
        entry = _manifest(station)
        missing = sorted(set(entry.get("requires", {}).get("features", [])) - features)
        out["stations"][station] = "ok" if not missing else f"missing {missing}"
    if provider == "gitlab":
        out["gitlab_api_url"] = api_url
        out["gitlab_login"] = None
        if not os.environ.get(TOKEN_SECRETS["gitlab"]):
            out["token_error"] = "not_set: name GITLAB_TOKEN in the command so the saved secret is passed in"
            return out
        try:
            out["gitlab_login"] = _gitlab("/user", api_url)["username"]
        except (FactoryError, KeyError) as err:
            rejected = " -> 401" in str(err) or " -> 403" in str(err)
            out["token_error"] = ("rejected: " if rejected else "") + str(err)[:300]
            return out
        out["repos"] = {}
        for repo in _split(args.repos):
            try:
                project = _gitlab(f"/projects/{_gitlab_project(repo)}", api_url)
                permissions = project.get("permissions") or {}
                levels = [(permissions.get(key) or {}).get("access_level")
                          for key in ("project_access", "group_access")]
                levels = [level for level in levels if isinstance(level, int)]
                if not project.get("default_branch"):
                    out["repos"][repo] = "no default branch"
                elif not levels:
                    out["repos"][repo] = "role unknown"
                else:
                    out["repos"][repo] = "push" if max(levels) >= 30 else "no push"
            except (FactoryError, KeyError):
                out["repos"][repo] = "not found or no access"
        return out
    try:
        out["profile"] = _profile(args.profile)
    except FactoryError as err:
        if "OPENHANDS_HOST" in str(err):
            raise
        out["profile"] = {"error": str(err)}
    out["github_login"] = None
    if not os.environ.get(TOKEN_SECRET):
        out["token_error"] = (
            f"not_set: name {TOKEN_SECRET} in the command so the agent server passes the"
            " saved secret in; if it is still not set, it is not saved"
        )
        return out
    try:
        out["github_login"] = _github("/user")["login"]
    except FactoryError as err:
        rejected = " -> 401" in str(err) or " -> 403" in str(err)
        out["token_error"] = ("rejected: " if rejected else "") + str(err)[:300]
        return out
    out["repos"] = {}
    for repo in _split(args.repos):
        try:
            out["repos"][repo] = "push" if _github(f"/repos/{repo}")["permissions"]["push"] else "no push"
        except (FactoryError, KeyError):
            out["repos"][repo] = "not found or no access"
    return out


def _selection(args) -> tuple[list[str], list[str], str | None]:
    provider = getattr(args, "provider", "github")
    repos = _split(args.repos)
    stations = _split(args.ids)
    if not repos or not stations:
        raise FactoryError("at least one repository and station are required")
    if not set(stations).issubset(STATIONS[provider]):
        raise FactoryError(f"station ids must belong to the selected {provider} provider")
    api_url = _gitlab_api_url(getattr(args, "gitlab_api_url", GITLAB_API_URL)) if provider == "gitlab" else None
    if api_url:
        for repo in repos:
            _gitlab_project(repo)
    return repos, stations, api_url


def _trigger_choice(args, entries: dict, current: dict | None = None) -> tuple[str, str | None]:
    requested = getattr(args, "trigger", None)
    selected = requested or (current or {}).get("type", "cron")
    source = getattr(args, "event_source", None) or ((current or {}).get("source") if requested != "cron" else None)
    if selected == "cron":
        if source:
            raise FactoryError("--event-source requires --trigger event")
        return selected, None
    if selected != "event" or getattr(args, "provider", "github") != "gitlab":
        raise FactoryError("event triggers are supported only for GitLab factory stations")
    if any("event" not in entry["setup"]["form"]["triggers"] for entry in entries.values()):
        raise FactoryError("not all selected stations offer event triggers")
    capabilities = _api("GET", "/capabilities")
    if "event" not in capabilities.get("triggerKinds", []):
        raise FactoryError("this deployment does not support event triggers; use a polling schedule")
    if not source:
        raise FactoryError("select a registered --event-source from Canvas /automations/events")
    if source not in capabilities.get("eventSources", []):
        raise FactoryError(f"event source {source!r} is not registered; check Canvas /automations/events")
    return selected, source


def create(args) -> dict:
    repos, stations, api_url = _selection(args)
    entries = {station: _manifest(station) for station in stations}
    selected, event_source = _trigger_choice(args, entries)
    overrides = _overrides(entries, args.set or [], stations)
    root = _extensions()
    profile = None
    created = []
    existing = []
    not_tagged = []
    try:
        for station in stations:
            entry = entries[station]
            bundle = entry.get("setup", {}).get("bundle")
            if not bundle:
                raise FactoryError(f"{station} has no bundle; create it as the skill describes")
            values = _form_values(entry, repos, overrides[station], api_url, selected, event_source)
            body = _create_body(entry, values, repos, selected)
            body["tarball_path"] = _upload(station, _tarball(root, bundle["files"], body["template"]["config"]))
            body["enabled"] = False
            body["tags"] = [FACTORY_TAG]
            if _needs_profile(entry):
                profile = profile or _profile(args.profile)
                body["agent_profile_id"] = profile["id"]
            try:
                status_code, automation = _api("POST", "", body, return_status=True)
            except FactoryError as err:
                if not _rejects_tags(err):
                    raise
                # A service older than automation tags: create the station untagged.
                del body["tags"]
                status_code, automation = _api("POST", "", body, return_status=True)
            summary = _summary(station, body["name"], body["trigger"], automation)
            if status_code == 200:
                summary = _summary(station, automation.get("name", body["name"]),
                                   automation.get("trigger", body["trigger"]), automation)
                # The service returns the org's existing automation for the same
                # template id (see find_existing_template_automation). Report it
                # as pre-existing so a repeat run does not claim it created it.
                # It comes back unchanged, so the factory tag is added here.
                existing.append(summary)
                reason = _add_factory_tag(automation)
                if reason:
                    not_tagged.append({**summary, "reason": reason})
                continue
            if automation.get("enabled") or automation.get("state") == "ACTIVE":
                _api("PATCH", f"/{automation['id']}", {"enabled": False})
            created.append(summary)
            if "tags" not in body:
                not_tagged.append({**summary, "reason": TAGS_UNSUPPORTED})
    except FactoryError as err:
        raise FactoryError(str(err), created=created, existing=existing, not_tagged=not_tagged) from None
    return {"created": created, "existing": existing, "not_tagged": not_tagged}


def _rejects_tags(err: FactoryError) -> bool:
    """Whether the service predates automation tags.

    Its create and update bodies forbid unknown fields, so it answers 422 with
    an ``extra_forbidden`` error at ``tags``.
    """
    if err.status != 422:
        return False
    try:
        errors = json.loads(err.detail)["detail"]
        return any(e["type"] == "extra_forbidden" and e["loc"][-1] == "tags" for e in errors)
    except (ValueError, KeyError, TypeError, IndexError):
        return False


def _add_factory_tag(automation: dict) -> str | None:
    """Add the factory tag to an automation; the reason when it cannot.

    The service replaces the whole tag list on PATCH, so the automation's own
    tags are sent back with the factory tag appended.
    """
    tags = automation.get("tags") or []
    if FACTORY_TAG in tags:
        return None
    try:
        _api("PATCH", f"/{automation['id']}", {"tags": [*tags, FACTORY_TAG]})
    except FactoryError as err:
        if err.status == 403:
            return NOT_CREATOR
        if _rejects_tags(err):
            return TAGS_UNSUPPORTED
        raise
    return None


def tag(args) -> dict:
    """Add the factory tag to automations another skill created (Jira, Linear)."""
    tagged = []
    not_tagged = []
    for automation_id in args.ids:
        automation = _api("GET", f"/{automation_id}")
        reason = _add_factory_tag(automation)
        if reason:
            not_tagged.append({"id": automation_id, "reason": reason})
        else:
            tagged.append(automation_id)
    return {"tagged": tagged, "not_tagged": not_tagged}


def tune(args) -> dict:
    """Apply new settings to an existing station by updating it in place.

    `create` cannot do this: it stamps `template.id`, and the service dedupes on
    that id, so a second `create` returns the original automation with its old
    config instead of a replacement. Here the same values are rendered, the
    bundle is re-uploaded, and the automation is PATCHed, so the new values take
    effect without a delete and without a template-id collision.
    """
    repos, stations, api_url = _selection(args)
    entries = {station: _manifest(station) for station in stations}
    overrides = _overrides(entries, args.set or [], stations)
    root = _extensions()
    profile = None
    tuned = []
    for station in stations:
        entry = entries[station]
        bundle = entry.get("setup", {}).get("bundle")
        if not bundle:
            raise FactoryError(f"{station} has no bundle; tune it as the skill describes")
        automation = _find_existing(station)
        if automation is None:
            raise FactoryError(f"{station} is not set up yet; create it before tuning it")
        current = _api("GET", f"/{automation['id']}")
        selected, event_source = _trigger_choice(args, {station: entry}, current.get("trigger"))
        values = _form_values(entry, repos, overrides[station], api_url, selected, event_source)
        body = _create_body(entry, values, repos, selected)
        patch = {
            "name": body["name"],
            "trigger": body["trigger"],
            "tarball_path": _upload(station, _tarball(root, bundle["files"], body["template"]["config"])),
            "entrypoint": body["entrypoint"],
        }
        if "timeout" in body:
            patch["timeout"] = body["timeout"]
        if "setup_script_path" in body:
            patch["setup_script_path"] = body["setup_script_path"]
        if _needs_profile(entry):
            profile = profile or _profile(args.profile)
            patch["agent_profile_id"] = profile["id"]
        updated = _api("PATCH", f"/{automation['id']}", patch)
        tuned.append(_summary(station, body["name"], body["trigger"], updated))
    return {"tuned": tuned}


def _overrides(entries: dict, items: list[str], stations: list[str]) -> dict[str, dict]:
    """Parse `--set` into per-station overrides.

    FIELD=VALUE applies to every listed station with that field; ID.FIELD=VALUE
    to one. Station lookup uses the parsed manifest, so a field on a station
    that declares no such field is reported instead of applied blindly.
    """
    overrides: dict[str, dict] = {station: {} for station in stations}
    for item in items:
        key, _, value = item.partition("=")
        target, _, field = key.rpartition(".")
        if target and target not in entries:
            raise FactoryError(f"--set names a station not in --ids: {target}")
        targets = [target] if target else [s for s in stations if field in _fields(entries[s])]
        if not targets:
            raise FactoryError(f"no listed station has field {field}")
        for station in targets:
            overrides[station][field] = _parse_value(value)
    return overrides


def _find_existing(station: str) -> dict | None:
    """The org's automation created from this station's template, if any."""
    offset = 0
    while True:
        page = _api("GET", f"?limit=100&offset={offset}")
        automations = page.get("automations", [])
        for automation in automations:
            template = (automation.get("preset_metadata") or {}).get("template") or {}
            if template.get("id") == station:
                return automation
        if len(automations) < 100:
            return None
        offset += 100


def _summary(station: str, name: str, trigger: dict, automation: dict) -> dict:
    return {
        "station": station,
        "id": automation["id"],
        "name": name,
        "trigger": trigger,
        "url": _automation_url(automation["id"]),
    }


def _automation_url(automation_id: str) -> str:
    """The automation's page in Agent Canvas."""
    return f"{_host()}/automations/{automation_id}"


def _latest_run(automation_id: str) -> dict | None:
    runs = _api("GET", f"/{automation_id}/runs?limit=1").get("runs", [])
    return runs[0] if runs else None


def verify(args) -> dict:
    results = {}
    waiting = {}
    for automation_id in args.ids + (args.no_wait or []):
        automation = _api("GET", f"/{automation_id}")
        if (automation.get("trigger") or {}).get("type") == "event":
            _api("PATCH", f"/{automation_id}", {"enabled": True})
            results[automation_id] = {"status": "AWAITING_EVENT", "enabled": True,
                                      "url": _automation_url(automation_id)}
            continue
        run = _api("POST", f"/{automation_id}/dispatch")
        if automation_id in (args.no_wait or []):
            _api("PATCH", f"/{automation_id}", {"enabled": True})
            results[automation_id] = {
                "status": run.get("status"),
                "enabled": True,
                "url": _automation_url(automation_id),
            }
        else:
            waiting[automation_id] = run.get("id")
    deadline = time.time() + args.timeout
    while waiting and time.time() < deadline:
        time.sleep(5)
        for automation_id in list(waiting):
            run = _latest_run(automation_id) or {}
            if run.get("status") not in TERMINAL:
                continue
            passed = run["status"] == "COMPLETED"
            _api("PATCH", f"/{automation_id}", {"enabled": passed})
            results[automation_id] = {
                "status": run["status"],
                "enabled": passed,
                "error_detail": run.get("error_detail"),
                "url": _automation_url(automation_id),
            }
            del waiting[automation_id]
    for automation_id in waiting:
        _api("PATCH", f"/{automation_id}", {"enabled": False})
        results[automation_id] = {
            "status": "TIMEOUT",
            "enabled": False,
            "url": _automation_url(automation_id),
        }
    return results


def status(args) -> dict:
    out = {}
    for automation_id in args.ids:
        run = _latest_run(automation_id) or {}
        out[automation_id] = {k: run.get(k) for k in ("status", "error_detail", "conversation_id", "completed_at")}
    return out


def prs(args) -> dict:
    """Open pull requests whose branch starts with the prefix, per repository."""
    out = {}
    for repo in _split(args.repos):
        pulls = _github(f"/repos/{repo}/pulls?state=open&per_page=100")
        out[repo] = [
            {
                "number": p["number"],
                "title": p["title"],
                "url": p["html_url"],
                "draft": p.get("draft"),
                "created_at": p.get("created_at"),
            }
            for p in pulls
            if p["head"]["ref"].startswith(args.branch_prefix)
        ]
    return out


def reset_token(args) -> dict:
    """Delete the selected provider's saved token (local Agent Canvas only)."""
    secret = TOKEN_SECRETS[getattr(args, "provider", "github")]
    try:
        _request("DELETE", f"{_host()}/api/settings/secrets/{secret}", headers=_auth())
    except FactoryError as err:
        raise FactoryError(f"could not delete {secret}; replace it in Settings -> Secrets: {err}") from None
    return {"deleted": secret}


def _split(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def _provider_options(parser):
    parser.add_argument("--provider", choices=tuple(STATIONS), default="github")
    parser.add_argument("--gitlab-api-url", default=GITLAB_API_URL)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--repos", required=True)
    _provider_options(p)
    p.add_argument("--profile")
    p.set_defaults(func=preflight)
    p = sub.add_parser("create")
    p.add_argument("--repos", required=True)
    p.add_argument("--ids", required=True)
    _provider_options(p)
    p.add_argument("--trigger", choices=("cron", "event"))
    p.add_argument("--event-source")
    p.add_argument("--set", action="append", metavar="[ID.]FIELD=VALUE")
    p.add_argument("--profile")
    p.set_defaults(func=create)
    p = sub.add_parser("tune")
    p.add_argument("--repos", required=True)
    p.add_argument("--ids", required=True)
    _provider_options(p)
    p.add_argument("--trigger", choices=("cron", "event"))
    p.add_argument("--event-source")
    p.add_argument("--set", action="append", metavar="[ID.]FIELD=VALUE")
    p.add_argument("--profile")
    p.set_defaults(func=tune)
    p = sub.add_parser("tag")
    p.add_argument("ids", nargs="+")
    p.set_defaults(func=tag)
    p = sub.add_parser("verify")
    p.add_argument("ids", nargs="*")
    p.add_argument("--no-wait", nargs="+", metavar="ID")
    p.add_argument("--timeout", type=int, default=600)
    p.set_defaults(func=verify)
    p = sub.add_parser("status")
    p.add_argument("ids", nargs="+")
    p.set_defaults(func=status)
    p = sub.add_parser("prs")
    p.add_argument("--repos", required=True)
    p.add_argument("--branch-prefix", default="openhands/agents-md")
    p.set_defaults(func=prs)
    p = sub.add_parser("reset-token")
    p.add_argument("--provider", choices=tuple(STATIONS), default="github")
    p.set_defaults(func=reset_token)
    args = parser.parse_args()
    try:
        print(json.dumps(args.func(args), indent=2))
    except FactoryError as err:
        print(json.dumps({"error": str(err), **err.extra}, indent=2))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
