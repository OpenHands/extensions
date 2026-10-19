#!/usr/bin/env python3
"""Deterministic helpers for the software-factory skill (stdlib only, no LLM).

Each command prints one JSON document on stdout and exits non-zero on failure.

  factory.py preflight --repos owner/a,owner/b [--profile NAME]
  factory.py create --repos owner/a --ids ID[,ID...] [--set [ID.]FIELD=VALUE ...] [--profile NAME]
  factory.py tune --repos owner/a --ids ID[,ID...] [--set [ID.]FIELD=VALUE ...] [--profile NAME]
  factory.py verify ID [ID ...] [--no-wait ID ...] [--timeout SECONDS]
  factory.py status ID [ID ...]
  factory.py prs --repos owner/a [--branch-prefix openhands/agents-md]
  factory.py reset-token

Environment:
  OPENHANDS_HOST                  automation host, as the openhands-automation skill determines it
  OPENHANDS_API_KEY               Bearer auth (OpenHands Cloud)
  OPENHANDS_AUTOMATION_API_KEY    X-Session-API-Key auth (local Agent Canvas; SESSION_API_KEY also works)
  GITHUB_PERSONAL_ACCESS_TOKEN    GitHub token; read, never printed
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

TOKEN_SECRET = "GITHUB_PERSONAL_ACCESS_TOKEN"
EXTENSIONS_URL = "https://github.com/OpenHands/extensions"
PLACEHOLDER_RE = re.compile(r"\{\{([a-z]+)\.([A-Za-z0-9_.]+)\}\}")
STATIONS = (
    "github-issue-to-pr",
    "github-pr-reviewer",
    "github-agents-md-maintainer",
    "github-issue-triage",
    "github-delivery-watchdog",
    "github-stale-ci-pr-closer",
    "qa-changes",
)
TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "SKIPPED"}


class FactoryError(Exception):
    def __init__(self, message: str, **extra):
        super().__init__(message)
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
        detail = err.read().decode()[:2000]
        raise FactoryError(f"{method} {url} -> {err.code}: {detail}") from None
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


def _fields(entry: dict) -> dict:
    form = entry["setup"]["form"]
    # Only the cron trigger group carries form fields; an entry whose only
    # trigger is an event declares no cron fields, so this must not index it.
    return {**form.get("args", {}), **form.get("triggers", {}).get("cron", {})}


def _form_values(entry: dict, repos: list[str], overrides: dict) -> dict:
    """Answers, else derived values, else manifest defaults."""
    fields = _fields(entry)
    values = {name: spec["default"] for name, spec in fields.items() if "default" in spec}
    for name, spec in fields.items():
        if spec.get("type") == "repo-picker":
            values[name] = repos if spec.get("multiple") else repos[0]
    if "githubTokenSecret" in fields:
        values["githubTokenSecret"] = TOKEN_SECRET
    for name, value in overrides.items():
        if name not in fields:
            raise FactoryError(f"{entry['id']} has no field {name}")
        values[name] = value
    missing = [n for n, s in fields.items() if s.get("required") and values.get(n) in (None, "", [])]
    if missing:
        raise FactoryError(f"{entry['id']} is missing required fields: {missing}")
    return values


def _create_body(entry: dict, values: dict, repos: list[str]) -> dict:
    """The create request, as Agent Canvas builds it for a catalog bundle."""
    bundle = entry["setup"]["bundle"]
    name = entry["name"] + (f" - {repos[0]}" if len(repos) == 1 else f" - {len(repos)} repositories")
    body = {
        "name": name,
        "trigger": {"type": "cron", "schedule": values["schedule"], "timezone": values["timezone"]},
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
    out: dict = {}
    features = set(_api("GET", "/capabilities").get("features", []))
    out["stations"] = {}
    for station in STATIONS:
        entry = _manifest(station)
        missing = sorted(set(entry.get("requires", {}).get("features", [])) - features)
        out["stations"][station] = "ok" if not missing else f"missing {missing}"
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


def create(args) -> dict:
    repos = _split(args.repos)
    stations = _split(args.ids)
    entries = {station: _manifest(station) for station in stations}
    overrides = _overrides(entries, args.set or [], stations)
    root = _extensions()
    profile = None
    created = []
    existing = []
    try:
        for station in stations:
            entry = entries[station]
            bundle = entry.get("setup", {}).get("bundle")
            if not bundle:
                raise FactoryError(f"{station} has no bundle; create it as the skill describes")
            values = _form_values(entry, repos, overrides[station])
            body = _create_body(entry, values, repos)
            body["tarball_path"] = _upload(station, _tarball(root, bundle["files"], body["template"]["config"]))
            body["enabled"] = False
            if _needs_profile(entry):
                profile = profile or _profile(args.profile)
                body["agent_profile_id"] = profile["id"]
            status_code, automation = _api("POST", "", body, return_status=True)
            if status_code == 200:
                # The service returns the org's existing automation for the same
                # template id (see find_existing_template_automation). Report it
                # as pre-existing so a repeat run does not claim it created it.
                existing.append(_summary(station, body["name"], body["trigger"], automation))
                continue
            if automation.get("enabled") or automation.get("state") == "ACTIVE":
                _api("PATCH", f"/{automation['id']}", {"enabled": False})
            created.append(_summary(station, body["name"], body["trigger"], automation))
    except FactoryError as err:
        raise FactoryError(str(err), created=created, existing=existing) from None
    return {"created": created, "existing": existing}


def tune(args) -> dict:
    """Apply new settings to an existing station by updating it in place.

    `create` cannot do this: it stamps `template.id`, and the service dedupes on
    that id, so a second `create` returns the original automation with its old
    config instead of a replacement. Here the same values are rendered, the
    bundle is re-uploaded, and the automation is PATCHed, so the new values take
    effect without a delete and without a template-id collision.
    """
    repos = _split(args.repos)
    stations = _split(args.ids)
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
        values = _form_values(entry, repos, overrides[station])
        body = _create_body(entry, values, repos)
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
    """Delete the saved token so request_secret opens its form (local Agent Canvas)."""
    try:
        _request("DELETE", f"{_host()}/api/settings/secrets/{TOKEN_SECRET}", headers=_auth())
    except FactoryError as err:
        raise FactoryError(f"could not delete {TOKEN_SECRET}; replace it in Settings -> Secrets: {err}") from None
    return {"deleted": TOKEN_SECRET}


def _split(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--repos", required=True)
    p.add_argument("--profile")
    p.set_defaults(func=preflight)
    p = sub.add_parser("create")
    p.add_argument("--repos", required=True)
    p.add_argument("--ids", required=True)
    p.add_argument("--set", action="append", metavar="[ID.]FIELD=VALUE")
    p.add_argument("--profile")
    p.set_defaults(func=create)
    p = sub.add_parser("tune")
    p.add_argument("--repos", required=True)
    p.add_argument("--ids", required=True)
    p.add_argument("--set", action="append", metavar="[ID.]FIELD=VALUE")
    p.add_argument("--profile")
    p.set_defaults(func=tune)
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
