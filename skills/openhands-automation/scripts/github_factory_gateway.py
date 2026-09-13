"""Repository-scoped GitHub gateway for the four factory roles.

Run in the trusted control plane. Workers receive role tokens, never the GitHub
credential. No arbitrary URLs, GraphQL, repository administration, or main-branch
writes are exposed. The merge operation independently checks current evidence.
"""

import base64
import hashlib
import json
import os
import re
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CONTROL = {}
TOKENS = {}
ROLES = ("triage", "developer", "reviewer", "watchdog")
ROOT = ""
CI_BACKEND = "checks"
REQUIRED_WORKFLOWS = set()


def configure():
    global CONTROL, TOKENS, ROOT, CI_BACKEND, REQUIRED_WORKFLOWS
    repo = os.environ["FACTORY_REPOSITORY"]
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
        raise ValueError("Expected owner/repository")
    control = json.loads(Path(os.environ["FACTORY_CONTROL_FILE"]).read_text())
    watchdog_token_env = os.environ.get(
        "FACTORY_GITHUB_WATCHDOG_TOKEN_ENV", "FACTORY_GITHUB_WATCHDOG_TOKEN"
    )
    if watchdog_token_env not in {
        "FACTORY_GITHUB_WATCHDOG_TOKEN",
        "FACTORY_GITHUB_DEVELOPER_TOKEN",
    }:
        raise ValueError("Watchdog credential must select its own or developer token")
    tokens = {}
    for role in ROLES:
        name = (
            watchdog_token_env
            if role == "watchdog"
            else f"FACTORY_GITHUB_{role.upper()}_TOKEN"
        )
        token = os.environ.get(name, "").strip()
        if not token:
            raise ValueError(
                f"Missing {name}; no implicit credential fallback is allowed"
            )
        tokens[role] = token
    grants = [control.get(role) for role in ROLES]
    if any(not isinstance(value, str) or not value.strip() for value in grants):
        raise ValueError("Every role needs a nonempty worker grant")
    if len(set(grants)) != len(ROLES):
        raise ValueError("Each role must use a distinct worker grant")
    expected_tokens = 3 if watchdog_token_env == "FACTORY_GITHUB_DEVELOPER_TOKEN" else 4
    if len(set(tokens.values())) != expected_tokens:
        raise ValueError(
            "Only explicit developer/watchdog credential sharing is allowed"
        )
    if set(grants) & set(tokens.values()):
        raise ValueError("GitHub credentials must not be exposed as worker grants")
    ci_backend = os.environ.get("FACTORY_CI_BACKEND", "checks")
    if ci_backend not in {"checks", "actions"}:
        raise ValueError("FACTORY_CI_BACKEND must be checks or actions")
    required = json.loads(os.environ.get("FACTORY_REQUIRED_WORKFLOWS", "[]"))
    if not isinstance(required, list) or any(
        type(value) is not int or value < 1 for value in required
    ):
        raise ValueError(
            "FACTORY_REQUIRED_WORKFLOWS must contain positive workflow IDs"
        )
    CONTROL, TOKENS = control, tokens
    CI_BACKEND, REQUIRED_WORKFLOWS = ci_backend, set(required)
    ROOT = f"https://api.github.com/repos/{repo}"


def github(role, method, path, body=None):
    request = Request(
        ROOT + path,
        data=json.dumps(body).encode() if body is not None else None,
        method=method,
        headers={
            "Authorization": "Bearer " + TOKENS[role],
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urlopen(request, timeout=60) as response:
        data = response.read()
        return json.loads(data) if data else {}


def archive(role, sha):
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Archive requires an exact commit SHA")
    req = Request(
        ROOT + "/tarball/" + sha, headers={"Authorization": "Bearer " + TOKENS[role]}
    )
    with urlopen(req, timeout=90) as response:
        content = response.read(25_000_001)
    if len(content) > 25_000_000:
        raise ValueError("Repository archive exceeds 25 MB")
    return {"sha": sha, "tarball": base64.b64encode(content).decode()}


def latest_statuses(role, sha):
    result = {}
    for page in range(1, 11):
        statuses = github(
            role, "GET", f"/commits/{sha}/statuses?per_page=100&page={page}"
        )
        for status in statuses:
            result.setdefault(status["context"], status)
        if len(statuses) < 100:
            return result
    raise ValueError("Commit status pagination exceeds the safe scan limit")


def ci_passed(role, sha):
    """Verify the explicitly configured CI source; never infer success from 403."""
    if CI_BACKEND == "checks":
        result = github(role, "GET", f"/commits/{sha}/check-runs?per_page=100")
        checks = result["check_runs"]
        return result.get("total_count", len(checks)) == len(checks) and all(
            c["conclusion"] in ("success", "neutral", "skipped") for c in checks
        )
    runs = {}
    for page in range(1, 11):
        result = github(
            role, "GET", f"/actions/runs?head_sha={sha}&per_page=100&page={page}"
        )
        for run in result["workflow_runs"]:
            if run["head_sha"] != sha:
                return False
            runs[run["id"]] = run
        if len(result["workflow_runs"]) < 100:
            if result["total_count"] != len(runs):
                return False
            return REQUIRED_WORKFLOWS <= {
                r["workflow_id"] for r in runs.values()
            } and all(
                r["status"] == "completed" and r["conclusion"] == "success"
                for r in runs.values()
            )
    # GitHub caps filtered Actions searches at 1,000; refuse an incomplete scan.
    return False


def permitted(role, method, path, body):
    route = path.split("?", 1)[0]
    if method == "GET":
        if role in ("triage", "developer", "reviewer") and re.fullmatch(
            r"/issues(?:/\d+(?:/comments)?)?", route
        ):
            return True
        if role == "triage" and route == "/labels":
            return True
        if role in ("developer", "reviewer", "watchdog") and (
            re.fullmatch(r"/pulls(?:/\d+(?:/reviews|/comments)?)?", route)
            or re.fullmatch(r"/commits/[0-9a-f]{40}/(?:statuses|check-runs)", route)
        ):
            return True
        if role in ("developer", "reviewer", "watchdog") and route == "/actions/runs":
            return True
        if role in ("developer", "reviewer") and re.fullmatch(
            r"/git/ref/heads/(?:main|factory/issue-\d+)", route
        ):
            return True
        return role == "developer" and bool(
            re.fullmatch(r"/git/commits/[0-9a-f]{40}", route)
        )
    if re.fullmatch(r"/issues/\d+/comments", route) and method == "POST":
        return role in ("triage", "developer", "reviewer") and set(body) == {"body"}
    if role == "triage":
        if method == "PATCH" and re.fullmatch(r"/issues/\d+", route):
            return set(body) <= {"body", "labels"}
        if method == "POST" and route == "/labels":
            return body.get("name") in {
                "ready-for-dev",
                "priority:high",
                "factory:attention",
            }
    if role == "developer":
        if method == "POST" and route in {"/git/blobs", "/git/trees", "/git/commits"}:
            return True
        if method == "POST" and route == "/git/refs":
            return bool(
                re.fullmatch(r"refs/heads/factory/issue-\d+", body.get("ref", ""))
            )
        if method == "PATCH" and re.fullmatch(
            r"/git/refs/heads/factory/issue-\d+", route
        ):
            return body.get("force", False) is False and set(body) <= {"sha", "force"}
        if method == "POST" and route == "/pulls":
            return body.get("base") == "main" and bool(
                re.fullmatch(r"factory/issue-\d+", body.get("head", ""))
            )
    if role == "reviewer":
        if method == "POST" and re.fullmatch(r"/pulls/\d+/reviews", route):
            return body.get("event") == "COMMENT" and bool(body.get("commit_id"))
        if method == "POST" and re.fullmatch(r"/statuses/[0-9a-f]{40}", route):
            return body.get("context") in {
                "software-factory/tests",
                "software-factory/review",
            }
    return False


def merge(number, sha):
    if number < 1 or not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ValueError("Merge requires a PR number and exact commit SHA")
    role = "watchdog"
    pr = github(role, "GET", f"/pulls/{number}")
    statuses = latest_statuses(role, sha)
    contexts = ("software-factory/tests", "software-factory/review")
    ci_ok = ci_passed(role, sha)
    # Refuse a stale base and incomplete pagination rather than overlooking CI.
    comparison = github(role, "GET", f"/compare/{pr['base']['sha']}...{sha}")
    eligible = (
        pr["state"] == "open"
        and not pr["draft"]
        and pr["head"]["sha"] == sha
        and pr["base"]["ref"] == "main"
        and re.fullmatch(r"factory/issue-\d+", pr["head"]["ref"])
        and pr["mergeable"] is True
        and comparison["status"] in ("ahead", "identical")
        and all(statuses.get(c, {}).get("state") == "success" for c in contexts)
        and all(s["state"] == "success" for s in statuses.values())
        and ci_ok
    )
    if not eligible:
        raise ValueError("Current head lacks passing acceptance or current base")
    return github(
        role, "PUT", f"/pulls/{number}/merge", {"sha": sha, "merge_method": "squash"}
    )


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def do_POST(self):
        supplied = self.headers.get("Authorization", "").removeprefix("Bearer ")
        role = next(
            (r for r in ROLES if secrets.compare_digest(supplied, CONTROL[r])),
            None,
        )
        if role is None:
            return self.reply(401, {"error": "Invalid role credential"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 12_000_000:
                return self.reply(413, {"error": "Invalid request size"})
            payload = json.loads(self.rfile.read(length))
            method, path = payload["method"], payload["path"]
            body = payload.get("body")
            if "%" in path or ".." in path or "#" in path or "\\" in path:
                return self.reply(403, {"error": "Invalid path"})
            if path == "/factory/archive" and role in ("developer", "reviewer"):
                return self.reply(200, archive(role, body["sha"]))
            if path == "/factory/bootstrap" and role == "developer":
                try:
                    return self.reply(200, github(role, "GET", "/git/ref/heads/main"))
                except HTTPError as exc:
                    if exc.code not in (404, 409):
                        raise
                # GitHub's Git Database API rejects an empty repository. An
                # empty placeholder gives the first application PR a base.
                return self.reply(
                    200,
                    github(
                        role,
                        "PUT",
                        "/contents/.gitkeep",
                        {
                            "message": "Initialize software factory repository",
                            "content": "",
                            "branch": "main",
                        },
                    ),
                )
            if path == "/factory/merge" and role == "watchdog":
                try:
                    result = merge(int(body["number"]), body["sha"])
                except ValueError as exc:
                    return self.reply(409, {"error": str(exc)})
                return self.reply(200, result)
            if not permitted(role, method, path, body or {}):
                return self.reply(403, {"error": "Operation outside role grant"})
            result = github(role, method, path, body)
            if method != "GET":
                print(
                    json.dumps(
                        {
                            "role": role,
                            "method": method,
                            "path": path,
                            "body_sha256": hashlib.sha256(
                                json.dumps(body).encode()
                            ).hexdigest(),
                        }
                    ),
                    flush=True,
                )
            self.reply(200, result)
        except HTTPError as exc:
            self.reply(exc.code, {"error": exc.read().decode()[:1000]})
        except (URLError, TimeoutError):
            self.reply(
                502, {"error": "GitHub upstream request failed; outcome may be unknown"}
            )
        except (ValueError, KeyError, TypeError) as exc:
            self.reply(400, {"error": str(exc)})

    def reply(self, status, data):
        encoded = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    configure()
    ThreadingHTTPServer(
        (os.environ.get("FACTORY_BIND", "172.17.0.1"), 19102), Handler
    ).serve_forever()
