"""Run github-repo-monitor's main() twice against the real automation KV API.

Usage (from an OpenHands/automation checkout, with its venv):
    uv run python e2e_kv_limit.py <extensions checkout> <automation checkout>

Starts the automation service (local mode, SQLite) with uvicorn, creates a
disabled automation, mints the run's KV token the way the dispatcher does,
seeds the "state" key with what a long-used monitor holds (just under the
64 KiB per-value limit), then runs the template's main() for two cron runs in
which GitHub returns the same new trigger comment. GitHub and the agent server
are stubbed in-process; the KV store is the real service over HTTP.
"""

import io
import json
import os
import socket
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import uuid
from contextlib import redirect_stdout
from pathlib import Path

ext_root, automation_root = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(automation_root))
from openhands.automation.utils.kv import create_kv_token  # noqa: E402

KV_SECRET = "e2e-kv-secret-" + "x" * 32
LOCAL_KEY = "e2e-local-key"
work = Path(tempfile.mkdtemp(prefix="e2e-kv-"))
with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
base = f"http://127.0.0.1:{port}/api/automation"
env = {
    **os.environ,
    "AUTOMATION_DB_URL": f"sqlite+aiosqlite:///{work}/automation.db",
    "AUTOMATION_AGENT_SERVER_URL": "http://127.0.0.1:9",
    "AUTOMATION_LOCAL_API_KEY": LOCAL_KEY,
    "AUTOMATION_KV_SECRET": KV_SECRET,
    "FILE_STORE": "local",
    "FILE_STORE_PATH": str(work / "files"),
    "OPENHANDS_SUPPRESS_BANNER": "1",
    "LOG_LEVEL": "WARNING",
}
service = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "openhands.automation.app:app", "--port", str(port)],
    cwd=automation_root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
)


def api(method, path, body=None, headers=None, raw=None):
    req = urllib.request.Request(
        base + path, method=method,
        data=raw if raw is not None else (json.dumps(body).encode() if body is not None else None),
        headers={"X-Session-API-Key": LOCAL_KEY, "Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read() or b"null")


try:
    for _ in range(100):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/ready")
            break
        except Exception:
            time.sleep(0.3)
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = b"print('noop')\n"
        info = tarfile.TarInfo("main.py")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    upload = api("POST", "/v1/uploads?name=e2e", raw=buf.getvalue(),
                 headers={"Content-Type": "application/gzip"})
    automation = api("POST", "/v1", {
        "name": "github-repo-monitor e2e", "enabled": False,
        "trigger": {"type": "cron", "schedule": "*/5 * * * *", "timezone": "UTC"},
        "tarball_path": upload["tarball_path"], "entrypoint": "python3 main.py",
    })
    kv_token = create_kv_token(KV_SECRET, uuid.UUID(automation["id"]), uuid.uuid4())

    def kv(method, key, value=None):
        req = urllib.request.Request(
            f"{base}/v1/kv/{key}", method=method,
            data=json.dumps(value).encode() if value is not None else None,
            headers={"Authorization": f"Bearer {kv_token}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())

    def size(value):
        return len(json.dumps(value, ensure_ascii=False).encode())

    # A long-used monitor: MAX_PROCESSED_IDS comment IDs plus closed
    # conversations that are never pruned, just under the 64 KiB limit.
    state = {
        "version": 1, "repo": "owner/repo", "last_poll": "2026-01-01T00:00:00Z",
        "conversations": {},
        "processed_comment_ids": list(range(3_000_000_000, 3_000_005_000)),
        "own_comment_ids": list(range(3_100_000_000, 3_100_000_020)),
    }
    for n in range(1, 10_000):
        state["conversations"][str(n)] = {
            "conversation_id": str(uuid.UUID(int=n)), "issue_number": n, "issue_type": "issue",
            "html_url": f"https://github.com/owner/repo/issues/{n}",
            "status": "closed", "last_activity": 1_700_000_000.0 + n,
        }
        if size(state) > 64 * 1024 - 200:
            del state["conversations"][str(n)]
            break
    kv("PUT", "state", state)
    print(f"seeded KV 'state': {size(kv('GET', 'state')['value'])} bytes (limit 65536)")

    trigger = {
        "id": 3_999_999_999, "body": "@openhands please fix this",
        "user": {"login": "maintainer", "type": "User"}, "created_at": "2026-01-01T00:05:00Z",
        "html_url": "https://github.com/owner/repo/issues/9999#issuecomment-3999999999",
        "issue_url": "https://api.github.com/repos/owner/repo/issues/9999",
    }
    acks, conversations = [], []

    def github_request(token, method, path, params=None, body=None):
        if path.endswith("/permission"):
            return {"permission": "write"}, {}
        if method == "POST":
            acks.append(path)
            return {"id": 3_200_000_000 + len(acks)}, {}
        return {"number": 9999, "title": "Bug", "body": "", "html_url": trigger["html_url"]}, {}

    def create_conversation(agent_url, api_key, prompt, *a, **k):
        conversations.append(prompt)
        return f"conv-{len(conversations)}"

    script = ext_root / "skills/github-repo-monitor/scripts/main.py"
    sys.path.insert(0, str(ext_root / "skills/github/scripts"))
    os.environ.update({"AUTOMATION_KV_TOKEN": kv_token, "AUTOMATION_API_URL": base})
    for run in (1, 2):
        ns = {"__name__": "github_repo_monitor"}
        exec(compile(script.read_text(), str(script), "exec"), ns)
        ns.update({
            "_resolve_github_token": lambda: "gh-token",
            "_verify_token_and_repo": lambda token, repo: "repo-owner",
            "get_secret": lambda name: "",
            "_github_request": github_request,
            "_github_paginate": lambda t, p, params=None: [trigger] if p.endswith("/issues/comments") else [],
            "create_conversation": create_conversation,
            "send_to_conversation": lambda *a: None,
            "conversation_status": lambda *a: "running",
        })
        log = io.StringIO()
        try:
            with redirect_stdout(log):
                ns["main"]()
            outcome = "completed"
        except Exception as exc:
            outcome = f"FAILED: {type(exc).__name__}: {exc}"
        for line in log.getvalue().splitlines():
            if any(word in line for word in ("Trigger detected", "Warning", "State saved")):
                print(f"↳ {line.strip()}")
        print(f"cron run {run}: {outcome}")
        print(f"↳ conversations started so far: {len(conversations)}, "
              f"acknowledgement comments posted so far: {len(acks)}, "
              f"KV 'state' now {size(kv('GET', 'state')['value'])} bytes")
    print("RESULT:", "OK - one trigger, one conversation" if len(conversations) == 1
          else f"BUG - one trigger, {len(conversations)} conversations")
finally:
    service.terminate()
    service.wait()
