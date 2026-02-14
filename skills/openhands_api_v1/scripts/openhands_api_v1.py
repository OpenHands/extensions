"""OpenHands Cloud API (V1) minimal client.

This file is intentionally:
- small (easy to copy into other repos)
- dependency-light (only `httpx`)
- opinionated in a helpful way (defaults to OpenHands Cloud)

Audience: AI agents.

The V1 API is hosted on the OpenHands app server under:
  {BASE_URL}/api/v1/...

Typical workflow for common operations:
1) Discover: GET /api/v1/users/me
2) List/search conversations: GET /api/v1/app-conversations/search
3) Start a conversation (creates sandbox): POST /api/v1/app-conversations
4) Monitor events for a conversation: GET /api/v1/conversation/{id}/events/search
5) (Optional) download trajectory: GET /api/v1/app-conversations/{id}/download

Note: Some operations happen against the *agent server* running inside a sandbox
(not the app server). Those endpoints use X-Session-API-Key instead of Bearer auth.

This client purposefully keeps responses as raw dicts/lists so agents can quickly
adapt it without strict schema maintenance.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx


DEFAULT_BASE_URL = "https://app.all-hands.dev"


@dataclass(frozen=True)
class OpenHandsV1Config:
    api_key: str
    base_url: str = DEFAULT_BASE_URL

    @property
    def api_v1_url(self) -> str:
        return f"{self.base_url.rstrip('/')}/api/v1"


class OpenHandsV1API:
    """Minimal OpenHands Cloud API V1 client (app server + agent server helpers)."""

    def __init__(self, api_key: str | None = None, base_url: str = DEFAULT_BASE_URL):
        resolved_key = api_key or os.getenv("OPENHANDS_API_KEY")
        if not resolved_key:
            raise ValueError("Missing API key. Set OPENHANDS_API_KEY or pass api_key=...")

        self._cfg = OpenHandsV1Config(api_key=resolved_key, base_url=base_url.rstrip("/"))
        self._client = httpx.Client(
            headers={
                "Authorization": f"Bearer {self._cfg.api_key}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

    @property
    def base_url(self) -> str:
        return self._cfg.base_url

    @property
    def api_v1_url(self) -> str:
        return self._cfg.api_v1_url

    def close(self) -> None:
        self._client.close()

    # -----------------------------
    # App server endpoints (Bearer auth)
    # -----------------------------

    def users_me(self) -> dict[str, Any]:
        r = self._client.get(f"{self.api_v1_url}/users/me")
        r.raise_for_status()
        return r.json()

    def app_conversations_search(self, *, limit: int = 20) -> dict[str, Any]:
        limit = max(1, int(limit))
        r = self._client.get(
            f"{self.api_v1_url}/app-conversations/search", params={"limit": limit}
        )
        r.raise_for_status()
        return r.json()

    def app_conversations_count(self) -> dict[str, Any]:
        r = self._client.get(f"{self.api_v1_url}/app-conversations/count")
        r.raise_for_status()
        return r.json()

    def app_conversations_get_batch(self, *, ids: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        r = self._client.get(f"{self.api_v1_url}/app-conversations", params={"ids": ids})
        r.raise_for_status()
        return r.json()

    def app_conversation_get(self, conversation_id: str) -> dict[str, Any] | None:
        items = self.app_conversations_get_batch(ids=[conversation_id])
        return items[0] if items else None

    def sandboxes_search(self, *, limit: int = 20) -> dict[str, Any]:
        limit = max(1, int(limit))
        r = self._client.get(f"{self.api_v1_url}/sandboxes/search", params={"limit": limit})
        r.raise_for_status()
        return r.json()

    def sandbox_specs_search(self, *, limit: int = 20) -> dict[str, Any]:
        limit = max(1, int(limit))
        r = self._client.get(
            f"{self.api_v1_url}/sandbox-specs/search", params={"limit": limit}
        )
        r.raise_for_status()
        return r.json()

    def conversation_events_search(
        self, conversation_id: str, *, limit: int = 50
    ) -> dict[str, Any]:
        limit = max(1, int(limit))
        r = self._client.get(
            f"{self.api_v1_url}/conversation/{conversation_id}/events/search",
            params={"limit": limit},
        )
        r.raise_for_status()
        return r.json()

    def conversation_events_count(self, conversation_id: str) -> dict[str, Any]:
        r = self._client.get(f"{self.api_v1_url}/conversation/{conversation_id}/events/count")
        r.raise_for_status()
        return r.json()

    def app_conversation_start(
        self,
        *,
        initial_message: str,
        selected_repository: str | None = None,
        selected_branch: str | None = None,
        title: str | None = None,
        run: bool = True,
    ) -> dict[str, Any]:
        """Start a new V1 app conversation.

        WARNING: This typically creates a sandbox and may incur costs.

        The payload structure here mirrors what the V1 app server expects:
        - initial_message.content is a list of content parts
        """

        payload: dict[str, Any] = {
            "initial_message": {
                "role": "user",
                "content": [{"type": "text", "text": initial_message}],
                "run": bool(run),
            }
        }
        if selected_repository:
            payload["selected_repository"] = selected_repository
        if selected_branch:
            payload["selected_branch"] = selected_branch
        if title:
            payload["title"] = title

        r = self._client.post(f"{self.api_v1_url}/app-conversations", json=payload, timeout=120)
        r.raise_for_status()
        return r.json()

    def app_conversations_start_tasks_get_batch(self, *, ids: list[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        r = self._client.get(
            f"{self.api_v1_url}/app-conversations/start-tasks", params={"ids": ids}
        )
        r.raise_for_status()
        return r.json()

    def app_conversation_start_task_get(self, task_id: str) -> dict[str, Any] | None:
        items = self.app_conversations_start_tasks_get_batch(ids=[task_id])
        return items[0] if items else None

    def sandboxes_pause(self, sandbox_id: str) -> dict[str, Any]:
        r = self._client.post(f"{self.api_v1_url}/sandboxes/{sandbox_id}/pause", timeout=60)
        r.raise_for_status()
        return r.json()

    def sandboxes_resume(self, sandbox_id: str) -> dict[str, Any]:
        r = self._client.post(f"{self.api_v1_url}/sandboxes/{sandbox_id}/resume", timeout=60)
        r.raise_for_status()
        return r.json()

    def app_conversation_download_zip(self, conversation_id: str, *, output_file: str | Path) -> dict[str, Any]:
        """Download a conversation trajectory zip to disk."""
        url = f"{self.api_v1_url}/app-conversations/{conversation_id}/download"
        r = self._client.get(url, timeout=60)
        r.raise_for_status()
        out = Path(output_file)
        out.write_bytes(r.content)
        return {
            "file": str(out),
            "size": len(r.content),
            "content_type": r.headers.get("content-type"),
        }

    def count_events_via_trajectory_zip(
        self,
        conversation_id: str,
        *,
        zip_file: str | Path,
        extract_dir: str | Path,
    ) -> dict[str, Any]:
        """Fallback event counting: download trajectory zip, extract, count event files.

        This is heavier than calling a count endpoint, but it is still a single API call and
        also gives you the full exported event payloads.

        Returns a small summary dict including `event_count`.
        """

        import zipfile

        zip_path = Path(zip_file)
        extract_path = Path(extract_dir)

        download_meta = self.app_conversation_download_zip(conversation_id, output_file=zip_path)
        extract_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_path)

        event_count = len(list(extract_path.glob("event_*.json")))
        has_meta = (extract_path / "meta.json").exists()

        return {
            "event_count": event_count,
            "has_meta": has_meta,
            "zip": download_meta,
            "extract_dir": str(extract_path),
        }

    # -----------------------------
    # Agent server endpoints (X-Session-API-Key)
    # -----------------------------

    @staticmethod
    def agent_headers(session_api_key: str) -> dict[str, str]:
        return {"X-Session-API-Key": session_api_key, "Content-Type": "application/json"}

    def agent_events_search(
        self,
        *,
        agent_server_url: str,
        session_api_key: str,
        conversation_id: str,
        limit: int = 50,
        sort_order: str | None = None,
        timestamp_gte: str | None = None,
        timestamp_lt: str | None = None,
        kind: str | None = None,
        source: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        """Search events via the sandbox agent-server.

        Notes:
        - `sort_order` must be one of: "TIMESTAMP", "TIMESTAMP_DESC".
        - timestamp filters are passed as ISO-8601 strings (e.g. "2026-02-14T21:54:00Z").
          The server accepts both timezone-aware and naive datetimes.
        """

        url = f"{agent_server_url.rstrip('/')}/api/conversations/{conversation_id}/events/search"
        params: dict[str, Any] = {"limit": max(1, int(limit))}
        if sort_order is not None:
            params["sort_order"] = sort_order
        if timestamp_gte is not None:
            params["timestamp__gte"] = timestamp_gte
        if timestamp_lt is not None:
            params["timestamp__lt"] = timestamp_lt
        if kind is not None:
            params["kind"] = kind
        if source is not None:
            params["source"] = source
        if body is not None:
            params["body"] = body

        r = httpx.get(
            url,
            headers=self.agent_headers(session_api_key),
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def agent_events_count(
        self,
        *,
        agent_server_url: str,
        session_api_key: str,
        conversation_id: str,
        timestamp_gte: str | None = None,
        timestamp_lt: str | None = None,
        kind: str | None = None,
        source: str | None = None,
        body: str | None = None,
    ) -> int:
        """Count events via the sandbox agent-server.

        Timestamp filters are passed as ISO-8601 strings (e.g. "2026-02-14T21:54:00Z").
        """

        url = f"{agent_server_url.rstrip('/')}/api/conversations/{conversation_id}/events/count"
        params: dict[str, Any] = {}
        if timestamp_gte is not None:
            params["timestamp__gte"] = timestamp_gte
        if timestamp_lt is not None:
            params["timestamp__lt"] = timestamp_lt
        if kind is not None:
            params["kind"] = kind
        if source is not None:
            params["source"] = source
        if body is not None:
            params["body"] = body

        r = httpx.get(
            url,
            headers=self.agent_headers(session_api_key),
            params=params,
            timeout=30,
        )
        r.raise_for_status()
        return int(r.json())

    def agent_execute_bash(
        self,
        *,
        agent_server_url: str,
        session_api_key: str,
        command: str,
        cwd: str | None = None,
        timeout_s: int = 30,
    ) -> dict[str, Any]:
        url = f"{agent_server_url.rstrip('/')}/api/bash/execute_bash_command"
        payload: dict[str, Any] = {"command": command, "timeout": int(timeout_s)}
        if cwd:
            payload["cwd"] = cwd
        r = httpx.post(url, headers=self.agent_headers(session_api_key), json=payload, timeout=60)
        r.raise_for_status()
        return r.json()

    def agent_download_file(
        self,
        *,
        agent_server_url: str,
        session_api_key: str,
        path: str,
        output_file: str | Path,
    ) -> dict[str, Any]:
        p = path if path.startswith("/") else f"/{path}"
        url = f"{agent_server_url.rstrip('/')}/api/file/download{p}"
        r = httpx.get(url, headers=self.agent_headers(session_api_key), timeout=30)
        r.raise_for_status()
        out = Path(output_file)
        out.write_bytes(r.content)
        return {"file": str(out), "size": len(r.content)}

    def agent_upload_text_file(
        self,
        *,
        agent_server_url: str,
        session_api_key: str,
        path: str,
        content: str,
        content_type: str = "text/plain",
    ) -> dict[str, Any]:
        p = path if path.startswith("/") else f"/{path}"
        url = f"{agent_server_url.rstrip('/')}/api/file/upload{p}"
        filename = os.path.basename(p)
        headers = {"X-Session-API-Key": session_api_key}
        files = {"file": (filename, content.encode("utf-8"), content_type)}
        r = httpx.post(url, headers=headers, files=files, timeout=30)
        r.raise_for_status()
        return r.json() if r.text else {"success": True}

    # -----------------------------
    # Convenience helpers
    # -----------------------------

    def app_conversation_start_from_prompt_files(
        self,
        prompt_file: str | Path,
        *,
        selected_repository: str | None = None,
        selected_branch: str | None = None,
        title: str | None = None,
        append_file: str | Path | None = None,
        run: bool = True,
    ) -> dict[str, Any]:
        main_text = Path(prompt_file).read_text(encoding="utf-8")
        if append_file and Path(append_file).exists():
            tail = Path(append_file).read_text(encoding="utf-8")
            initial = f"{main_text}\n\n{tail}"
        else:
            initial = main_text

        return self.app_conversation_start(
            initial_message=initial,
            selected_repository=selected_repository,
            selected_branch=selected_branch,
            title=title,
            run=run,
        )

    def poll_start_task_until_ready(
        self,
        task_id: str,
        *,
        timeout_s: int = 10 * 60,
        poll_interval_s: int = 2,
    ) -> dict[str, Any]:
        start = time.time()
        last: dict[str, Any] | None = None
        while time.time() - start < timeout_s:
            last = self.app_conversation_start_task_get(task_id)
            if not last:
                time.sleep(poll_interval_s)
                continue
            status = str(last.get("status") or "").upper()
            if status in {"READY", "ERROR", "FAILED", "CANCELLED"}:
                return last
            time.sleep(poll_interval_s)
        raise TimeoutError(f"Start task {task_id} did not reach terminal state in {timeout_s}s (last={last})")


def _cmd_search_conversations(args: argparse.Namespace) -> int:
    api = OpenHandsV1API(api_key=args.api_key, base_url=args.base_url)
    try:
        print(json.dumps(api.app_conversations_search(limit=args.limit), indent=2))
        return 0
    finally:
        api.close()


def _cmd_start_conversation(args: argparse.Namespace) -> int:
    api = OpenHandsV1API(api_key=args.api_key, base_url=args.base_url)
    try:
        resp = api.app_conversation_start_from_prompt_files(
            args.prompt_file,
            selected_repository=args.repo,
            selected_branch=args.branch,
            title=args.title,
            append_file=args.append_file,
            run=not args.no_run,
        )
        print(json.dumps(resp, indent=2))
        return 0
    finally:
        api.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="openhands_api_v1.py")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_search = sub.add_parser("search-conversations", help="GET /api/v1/app-conversations/search")
    p_search.add_argument("--api-key", default=None, help="Defaults to OPENHANDS_API_KEY env var")
    p_search.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p_search.add_argument("--limit", type=int, default=5)
    p_search.set_defaults(func=_cmd_search_conversations)

    p_start = sub.add_parser("start-conversation", help="POST /api/v1/app-conversations from a prompt file")
    p_start.add_argument("--api-key", default=None, help="Defaults to OPENHANDS_API_KEY env var")
    p_start.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p_start.add_argument("--prompt-file", required=True)
    p_start.add_argument("--append-file", default=None)
    p_start.add_argument("--repo", default=None)
    p_start.add_argument("--branch", default=None)
    p_start.add_argument("--title", default=None)
    p_start.add_argument("--no-run", action="store_true", help="If set, do not auto-run after sending initial message")
    p_start.set_defaults(func=_cmd_start_conversation)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
