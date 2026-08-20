"""Protocol and safety tests for the Taskmarket delegation plugin."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "plugins" / "taskmarket-delegation" / "scripts" / "taskmarket_mcp.py"


def load_bridge():
    spec = importlib.util.spec_from_file_location("taskmarket_mcp", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_prepare_requires_fields_and_enforces_reward_ceiling(monkeypatch):
    bridge = load_bridge()
    monkeypatch.setattr(bridge, "MAX_REWARD", bridge.Decimal("5"))

    prepared = bridge._prepare_task({
        "description": "Review a small Python package",
        "reward_usdc": 4.5,
        "duration_hours": 8,
    })
    assert prepared["requires_explicit_confirmation"] is True
    assert prepared["review_summary"]["maximum_possible_spend_usdc"] == "4.5"
    assert prepared["authorization_token"] in bridge.prepared_tasks

    try:
        bridge._prepare_task({"description": "Too expensive", "reward_usdc": 6, "duration_hours": 8})
    except RuntimeError as exc:
        assert "ceiling" in str(exc)
    else:
        raise AssertionError("reward ceiling was not enforced")


def test_create_requires_exact_confirmation(monkeypatch):
    bridge = load_bridge()
    monkeypatch.setattr(bridge, "MAX_REWARD", bridge.Decimal("5"))
    prepared = bridge._prepare_task({"description": "Run tests", "reward_usdc": 1, "duration_hours": 2})
    token = prepared["authorization_token"]

    try:
        bridge._create_task({"authorization_token": token, "confirm": False, "confirmation_text": "CREATE_TASK"})
    except RuntimeError as exc:
        assert "Explicit confirmation" in str(exc)
    else:
        raise AssertionError("create accepted missing confirmation")


def test_mcp_protocol_lists_tools_and_handles_notification(tmp_path):
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "2024-11-05"},
    }
    notify = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    tools = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    payload = "\n".join(json.dumps(item) for item in (init, notify, tools)) + "\n"
    env = os.environ.copy()
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=payload.encode("utf-8"),
        text=False,
        capture_output=True,
        check=False,
        timeout=10,
        env=env,
    )
    assert completed.returncode == 0
    raw = completed.stdout
    responses = []
    offset = 0
    while offset < len(raw):
        separator = raw.index(b"\r\n\r\n", offset)
        header = raw[offset:separator].decode("ascii")
        length = int(next(line.split(":", 1)[1] for line in header.splitlines() if line.lower().startswith("content-length:")))
        start = separator + 4
        responses.append(json.loads(raw[start : start + length].decode("utf-8")))
        offset = start + length
    assert [response["id"] for response in responses] == [1, 2]
    names = {tool["name"] for tool in responses[1]["result"]["tools"]}
    assert "taskmarket_prepare_task" in names
    assert "taskmarket_list_submissions" in names
    assert "taskmarket_accept_submission" not in names
