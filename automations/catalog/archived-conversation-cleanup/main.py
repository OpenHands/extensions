"""Delete archived conversations that are older than the retention window.

The archive tag is written by the Agent Canvas UI. Archiving sets the tag and
bumps ``updated_at``, so ``updated_at`` measures how long a conversation has
been archived and idle. Only conversations in a settled state are deleted.

The retention window comes from the ``config.json`` beside this script, which
the catalog setup form renders, so one script serves any number of days. The
constants below are the defaults for a copy that ships without that file.
"""

import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

RETENTION_DAYS = 14
ARCHIVED_TAG = "archived"
PAGE_LIMIT = 100
# Allowlist, because this deletes data: an unknown, missing, or null status
# could still be live work. Canvas counts idle as live too, waiting for input.
SETTLED_STATUSES = {"finished", "error", "stuck"}

CONFIG_FILENAME = "config.json"


def _retention_days(value):
    """A positive number of days. A fraction is a valid window, not a defect."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{CONFIG_FILENAME}: retention_days must be a number of days")
    if not 0 < value < math.inf:
        raise ValueError(f"{CONFIG_FILENAME}: retention_days must be a positive number")
    return int(value) if float(value).is_integer() else value


def load_config(directory: Path | None = None) -> dict:
    """Return the rendered config shipped beside this script, or {} if absent.

    Only these keys are read; anything else in the file is ignored, so a host
    may ship provenance there without this script caring. A bad value raises,
    and main() reports it through the callback, so a broken config fails the
    run instead of ending it before the callback can fire.
    """
    path = (directory or Path(__file__).resolve().parent) / CONFIG_FILENAME
    if not path.is_file():
        return {}

    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{CONFIG_FILENAME} is not valid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{CONFIG_FILENAME} must contain a JSON object")

    config = {}
    if "retention_days" in raw:
        config["retention_days"] = _retention_days(raw["retention_days"])
    if "peer_agent_server_url" in raw:
        peer = raw["peer_agent_server_url"]
        if not isinstance(peer, str):
            raise ValueError(
                f"{CONFIG_FILENAME}: peer_agent_server_url must be a string"
            )
        config["peer_agent_server_url"] = peer.strip()
    return config


AGENT_SERVER_URL = os.environ.get("AGENT_SERVER_URL", "").rstrip("/")
SESSION_KEY = os.environ.get("SESSION_API_KEY") or os.environ.get(
    "OH_SESSION_API_KEYS_0", ""
)
HTTP_TIMEOUT = 60


def agent_servers(peer_url: str) -> list[str]:
    """The server this run talks to, plus an optional peer, without duplicates.

    Each agent server keeps its own in-memory catalog, loaded at start-up, so a
    run sees only the server it runs on. A deployment that runs a second agent
    server over the same conversations directory sets the peer to sweep both.
    """
    return list(
        dict.fromkeys(url for url in (AGENT_SERVER_URL, peer_url.rstrip("/")) if url)
    )


def fire_callback(status="COMPLETED", error=None):
    """Must run on every exit path, success or failure."""
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url:
        return
    body = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error:
        body["error"] = error
    callback = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('AUTOMATION_CALLBACK_API_KEY', '')}",
        },
    )
    try:
        urllib.request.urlopen(callback, timeout=HTTP_TIMEOUT)
    except Exception as exc:  # noqa: BLE001 - a failed callback must not mask the result
        print(f"Callback error: {exc}")


def request(server_url, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"X-Session-API-Key": SESSION_KEY}
    if data is not None:
        headers["Content-Type"] = "application/json"
    call = urllib.request.Request(
        f"{server_url}{path}", data=data, headers=headers, method=method
    )
    with urllib.request.urlopen(call, timeout=HTTP_TIMEOUT) as response:
        payload = response.read()
    return json.loads(payload) if payload else None


def list_conversations(server_url):
    """Return every conversation known to one agent server."""
    conversations = []
    page_id = None
    while True:
        query = f"?limit={PAGE_LIMIT}"
        if page_id:
            query += "&page_id=" + urllib.parse.quote(page_id)
        page = request(server_url, "GET", "/api/conversations/search" + query)
        conversations.extend(page["items"])
        page_id = page.get("next_page_id")
        if not page_id:
            return conversations


def parse_timestamp(value):
    """Parse an ISO-8601 timestamp from the API. Return None when unusable."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def is_archived(conversation):
    """True when the conversation carries the archive tag, as the UI writes it."""
    tags = conversation.get("tags") or {}
    return str(tags.get(ARCHIVED_TAG, "")).strip().lower() == "true"


def is_expired(conversation, cutoff):
    if not is_archived(conversation):
        return False
    if conversation.get("execution_status") not in SETTLED_STATUSES:
        return False
    last_activity = parse_timestamp(conversation.get("updated_at"))
    return last_activity is not None and last_activity < cutoff


def collect_expired(cutoff, servers):
    """Return ``(server_url, conversation)`` pairs past the retention window.

    A conversation can appear in more than one catalog. Keep the first entry and
    send its delete to the server that listed it, because that server owns the
    record; the other server would reject the delete.
    """
    seen = set()
    candidates = []
    listed = 0
    for server_url in servers:
        try:
            conversations = list_conversations(server_url)
        except Exception as exc:  # noqa: BLE001 - one unreachable server must not block the rest
            print(f"Cannot list {server_url}: {exc}")
            continue
        listed += 1
        archived = sum(1 for c in conversations if is_archived(c))
        expired = [c for c in conversations if is_expired(c, cutoff)]
        print(
            f"{server_url}: {len(conversations)} conversations, "
            f"{archived} archived, {len(expired)} archived before {cutoff.isoformat()}"
        )
        for conversation in expired:
            if conversation["id"] in seen:
                continue
            seen.add(conversation["id"])
            candidates.append((server_url, conversation))
    if servers and not listed:
        raise RuntimeError("no agent server could be listed")
    return candidates


def run():
    config = load_config()
    servers = agent_servers(
        config.get("peer_agent_server_url")
        or os.environ.get("PEER_AGENT_SERVER_URL", "")
    )
    if not servers or not SESSION_KEY:
        raise RuntimeError("AGENT_SERVER_URL and a session API key are required")

    retention_days = config.get("retention_days", RETENTION_DAYS)
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    candidates = collect_expired(cutoff, servers)

    deleted, gone, failures = 0, 0, []
    for server_url, conversation in candidates:
        identifier = conversation["id"]
        try:
            request(server_url, "DELETE", f"/api/conversations/{identifier}")
            deleted += 1
            print(f"Deleted {identifier} (idle since {conversation['updated_at']})")
        except urllib.error.HTTPError as exc:
            # Both servers share one conversations directory, but each keeps its
            # own catalog. Deleting through one leaves the other listing a row
            # whose data is gone, and that peer answers 400 rather than 404, so
            # both codes mean the row is already removed.
            # ponytail: a genuine 400 is indistinguishable from that stale row;
            # it is logged rather than retried, because a retry cannot succeed.
            if exc.code in (400, 404):
                gone += 1
                print(f"Already removed {identifier}: HTTP {exc.code}")
                continue
            failures.append(f"{identifier}: HTTP {exc.code}")
            print(f"Failed to delete {identifier}: HTTP {exc.code}")
        except Exception as exc:  # noqa: BLE001 - one bad conversation must not stop the sweep
            failures.append(f"{identifier}: {exc}")
            print(f"Failed to delete {identifier}: {exc}")

    print(
        f"Deleted {deleted} of {len(candidates)} archived conversations "
        f"({gone} already removed)"
    )
    if failures:
        raise RuntimeError(f"{len(failures)} deletions failed: {'; '.join(failures)}")


def main():
    try:
        run()
        fire_callback("COMPLETED")
    except Exception as exc:  # noqa: BLE001 - the run must always report its outcome
        print(f"ERROR: {exc}", file=sys.stderr)
        fire_callback("FAILED", str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()