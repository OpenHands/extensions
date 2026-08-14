#!/usr/bin/env python3
"""Small, dependency-free MCP bridge for the first-party Taskmarket CLI/API.

Reads use the public REST API. Paid writes deliberately go through the
first-party ``taskmarket`` CLI so it owns wallet signing, legal receipts, and
X402 payment handling. The bridge never accepts or stores private keys.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


API_URL = os.environ.get("TASKMARKET_API_URL", "https://api.taskmarket.dev").rstrip("/")
CLI = os.environ.get("TASKMARKET_CLI", "taskmarket")
MAX_REWARD = Decimal(os.environ.get("TASKMARKET_MAX_REWARD_USDC", "100"))
PREPARE_TTL_SECONDS = 30 * 60
prepared_tasks: dict[str, dict[str, Any]] = {}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _error(message: str) -> RuntimeError:
    return RuntimeError(message)


def _api_get(path: str, params: dict[str, str] | None = None) -> Any:
    url = f"{API_URL}{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "openhands-taskmarket-delegation/0.1",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise _error(f"Taskmarket API returned HTTP {exc.code}: {body[:500]}") from exc
    except (URLError, TimeoutError) as exc:
        raise _error(f"Taskmarket API request failed: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise _error("Taskmarket API returned invalid JSON") from exc


def _required_string(args: dict[str, Any], name: str, *, max_length: int = 4000) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise _error(f"{name} must be a non-empty string")
    value = value.strip()
    if len(value) > max_length:
        raise _error(f"{name} is limited to {max_length} characters")
    return value


def _decimal_reward(value: Any) -> tuple[Decimal, str]:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise _error("reward_usdc must be a decimal USDC amount") from exc
    if not amount.is_finite() or amount <= 0:
        raise _error("reward_usdc must be greater than zero")
    if amount > MAX_REWARD:
        raise _error(f"reward_usdc exceeds the configured ceiling of {MAX_REWARD} USDC")
    if amount.as_tuple().exponent < -6:
        raise _error("reward_usdc supports at most six decimal places")
    return amount, format(amount, "f")


def _duration(args: dict[str, Any]) -> int:
    value = args.get("duration_hours")
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 720:
        raise _error("duration_hours must be an integer from 1 to 720")
    return value


def _list_tasks(args: dict[str, Any]) -> Any:
    params: dict[str, str] = {}
    status = args.get("status", "open")
    if status:
        if status not in {"open", "claimed", "completed", "expired", "cancelled"}:
            raise _error("status is not a supported Taskmarket status")
        params["status"] = status
    mode = args.get("mode")
    if mode:
        if mode not in {"bounty", "claim", "pitch", "benchmark", "auction"}:
            raise _error("mode is not a supported Taskmarket mode")
        params["mode"] = mode
    tags = args.get("tags")
    if tags:
        if not isinstance(tags, list) or not all(isinstance(tag, str) and tag.strip() for tag in tags):
            raise _error("tags must be a list of non-empty strings")
        params["tags"] = ",".join(tag.strip() for tag in tags)
    limit = args.get("limit", 20)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise _error("limit must be an integer from 1 to 100")
    params["limit"] = str(limit)
    return _api_get("/api/tasks", params)


def _prepare_task(args: dict[str, Any]) -> Any:
    description = _required_string(args, "description")
    reward, reward_text = _decimal_reward(args.get("reward_usdc"))
    duration = _duration(args)
    mode = args.get("mode", "bounty")
    if mode not in {"bounty", "claim", "pitch", "benchmark"}:
        raise _error("mode must be bounty, claim, pitch, or benchmark")
    task_visibility = args.get("task_visibility", "public")
    if task_visibility not in {"public", "unlisted"}:
        raise _error("task_visibility must be public or unlisted")
    submission_visibility = args.get("submission_visibility", "public")
    if submission_visibility not in {"public", "reveal_all", "winner_only", "never"}:
        raise _error("submission_visibility is not supported")

    token = str(uuid.uuid4())
    prepared_tasks[token] = {
        "created_at": time.time(),
        "payload": {
            "description": description,
            "reward_usdc": reward,
            "reward_text": reward_text,
            "duration_hours": duration,
            "mode": mode,
            "task_visibility": task_visibility,
            "submission_visibility": submission_visibility,
        },
    }
    return {
        "authorization_token": token,
        "expires_in_seconds": PREPARE_TTL_SECONDS,
        "requires_explicit_confirmation": True,
        "review_summary": {
            "description": description,
            "reward_usdc": reward_text,
            "duration_hours": duration,
            "mode": mode,
            "task_visibility": task_visibility,
            "submission_visibility": submission_visibility,
            "maximum_possible_spend_usdc": reward_text,
        },
        "next_step": "Show review_summary to the user. Create only after exact confirmation with CREATE_TASK.",
    }


def _create_task(args: dict[str, Any]) -> Any:
    token = _required_string(args, "authorization_token", max_length=80)
    if args.get("confirm") is not True or args.get("confirmation_text") != "CREATE_TASK":
        raise _error("Explicit confirmation is required: confirm=true and confirmation_text=CREATE_TASK")
    prepared = prepared_tasks.get(token)
    if not prepared:
        raise _error("authorization_token is unknown or already used")
    if time.time() - prepared["created_at"] > PREPARE_TTL_SECONDS:
        prepared_tasks.pop(token, None)
        raise _error("authorization_token has expired; prepare the task again")

    payload = prepared_tasks.pop(token)["payload"]
    cli_path = shutil.which(CLI) or (CLI if os.path.isfile(CLI) else None)
    if not cli_path:
        raise _error("The first-party taskmarket CLI is not installed or not on PATH")
    command = [
        cli_path,
        "task",
        "create",
        "--description",
        payload["description"],
        "--reward",
        payload["reward_text"],
        "--duration",
        str(payload["duration_hours"]),
        "--mode",
        payload["mode"],
        "--task-visibility",
        payload["task_visibility"],
        "--submission-visibility",
        payload["submission_visibility"],
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
            shell=False,
        )
    except OSError as exc:
        raise _error(f"Unable to start the taskmarket CLI: {exc}") from exc
    if completed.returncode != 0:
        stderr = completed.stderr.strip()[-1000:]
        raise _error(f"Taskmarket create failed before completion: {stderr or 'unknown CLI error'}")
    output = completed.stdout.strip()
    try:
        parsed: Any = json.loads(output)
    except json.JSONDecodeError:
        parsed = {"raw_cli_output": output[-4000:]}
    return {
        "created": True,
        "taskmarket_result": parsed,
        "review_note": "Creation was explicitly authorized. Use taskmarket_get_task and taskmarket_list_submissions for follow-up; no submission was accepted automatically.",
    }


def _get_task(args: dict[str, Any]) -> Any:
    task_id = _required_string(args, "task_id", max_length=160)
    return _api_get(f"/api/tasks/{quote(task_id, safe='')}")


def _list_submissions(args: dict[str, Any]) -> Any:
    task_id = _required_string(args, "task_id", max_length=160)
    data = _api_get(f"/api/tasks/{quote(task_id, safe='')}/submissions")
    return {
        "task_id": task_id,
        "human_review_required": True,
        "submissions": data,
        "policy": "This integration only presents submissions. It never accepts or rejects work automatically.",
    }


def _dispatch(name: str, args: dict[str, Any]) -> Any:
    if name == "taskmarket_list_tasks":
        return _list_tasks(args)
    if name == "taskmarket_prepare_task":
        return _prepare_task(args)
    if name == "taskmarket_create_task":
        return _create_task(args)
    if name == "taskmarket_get_task":
        return _get_task(args)
    if name == "taskmarket_list_submissions":
        return _list_submissions(args)
    raise _error(f"Unknown tool: {name}")


TOOLS = [
    {
        "name": "taskmarket_list_tasks",
        "description": "Browse public Taskmarket tasks. Read-only; never spends funds.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "default": "open"},
                "mode": {"type": "string", "enum": ["bounty", "claim", "pitch", "benchmark", "auction"]},
                "tags": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            },
        },
    },
    {
        "name": "taskmarket_prepare_task",
        "description": "Validate and stage a Taskmarket task for human review. Does not create or fund anything.",
        "inputSchema": {
            "type": "object",
            "required": ["description", "reward_usdc", "duration_hours"],
            "properties": {
                "description": {"type": "string", "maxLength": 4000},
                "reward_usdc": {"type": "number", "exclusiveMinimum": 0},
                "duration_hours": {"type": "integer", "minimum": 1, "maximum": 720},
                "mode": {"type": "string", "enum": ["bounty", "claim", "pitch", "benchmark"], "default": "bounty"},
                "task_visibility": {"type": "string", "enum": ["public", "unlisted"], "default": "public"},
                "submission_visibility": {"type": "string", "enum": ["public", "reveal_all", "winner_only", "never"], "default": "public"},
            },
        },
    },
    {
        "name": "taskmarket_create_task",
        "description": "Create and fund a prepared Taskmarket task through the first-party CLI. Requires a fresh explicit user confirmation and obeys TASKMARKET_MAX_REWARD_USDC.",
        "inputSchema": {
            "type": "object",
            "required": ["authorization_token", "confirm", "confirmation_text"],
            "properties": {
                "authorization_token": {"type": "string"},
                "confirm": {"type": "boolean", "const": True},
                "confirmation_text": {"type": "string", "const": "CREATE_TASK"},
            },
        },
    },
    {
        "name": "taskmarket_get_task",
        "description": "Read a Taskmarket task and its current lifecycle state.",
        "inputSchema": {"type": "object", "required": ["task_id"], "properties": {"task_id": {"type": "string"}}},
    },
    {
        "name": "taskmarket_list_submissions",
        "description": "Retrieve submissions for a Taskmarket task and present them for human review. Never accepts or rejects work.",
        "inputSchema": {"type": "object", "required": ["task_id"], "properties": {"task_id": {"type": "string"}}},
    },
]


def _response(request_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def _error_response(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _handle(request: dict[str, Any]) -> dict[str, Any] | None:
    method = request.get("method")
    request_id = request.get("id")
    if method in {"notifications/initialized", "notifications/cancelled"}:
        return None
    if method == "initialize":
        return _response(
            request_id,
            {
                "protocolVersion": request.get("params", {}).get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "taskmarket-delegation", "version": "0.1.0"},
            },
        )
    if method == "ping":
        return _response(request_id, {})
    if method == "tools/list":
        return _response(request_id, {"tools": TOOLS})
    if method == "tools/call":
        params = request.get("params") or {}
        try:
            result = _dispatch(params.get("name", ""), params.get("arguments") or {})
            return _response(request_id, {"content": [{"type": "text", "text": _json(result)}]})
        except Exception as exc:  # MCP callers should receive actionable errors, not a crashed server.
            return _response(
                request_id,
                {"content": [{"type": "text", "text": str(exc)}], "isError": True},
            )
    if request_id is None:
        return None
    return _error_response(request_id, -32601, f"Unsupported method: {method}")


def _read_message() -> dict[str, Any] | None:
    first = sys.stdin.buffer.readline()
    if not first:
        return None
    if first.lstrip().startswith(b"{"):
        return json.loads(first)
    headers = first + b"\n"
    while b"\r\n\r\n" not in headers and b"\n\n" not in headers:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        headers += line
    header_text = headers.decode("ascii", errors="replace")
    content_length = None
    for line in header_text.replace("\r\n", "\n").split("\n"):
        if line.lower().startswith("content-length:"):
            content_length = int(line.split(":", 1)[1].strip())
    if content_length is None:
        raise _error("MCP message did not include Content-Length")
    payload = sys.stdin.buffer.read(content_length)
    return json.loads(payload.decode("utf-8"))


def _write_message(message: dict[str, Any]) -> None:
    payload = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii"))
    sys.stdout.buffer.write(payload)
    sys.stdout.buffer.flush()


def main() -> None:
    while True:
        try:
            request = _read_message()
            if request is None:
                return
            response = _handle(request)
            if response is not None:
                _write_message(response)
        except Exception as exc:
            print(f"taskmarket MCP bridge error: {exc}", file=sys.stderr, flush=True)
            return


if __name__ == "__main__":
    main()
