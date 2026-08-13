"""Tests for the OpenHands TaskMarket adapter."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "plugins" / "taskmarket" / "scripts" / "taskmarket.py"
SPEC = importlib.util.spec_from_file_location("taskmarket_adapter", SCRIPT)
assert SPEC and SPEC.loader
adapter = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adapter
SPEC.loader.exec_module(adapter)


def test_preview_contains_exact_budget_and_base_network():
    args = adapter.build_parser().parse_args(
        [
            "preview",
            "--description",
            "Ship a tested adapter with a reproducible demo",
            "--reward",
            "1.00",
            "--duration",
            "24",
            "--tags",
            "coding,testing",
            "--max-spend-usdc",
            "1.10",
        ]
    )

    preview = adapter.build_preview(args, now=datetime(2026, 1, 1, tzinfo=timezone.utc))

    assert preview["description"] == "Ship a tested adapter with a reproducible demo"
    assert preview["rewardUsdc"] == "1"
    assert preview["deadlineUtc"] == "2026-01-02T00:00:00Z"
    assert preview["network"] == {"name": "Base", "chainId": 8453, "asset": "USDC"}
    assert preview["estimatedMaxSpendUsdc"] == "1.076"


def test_preview_rejects_a_spend_ceiling_below_reward_and_fee_buffer():
    args = adapter.build_parser().parse_args(
        [
            "create",
            "--description",
            "Do the work with tests",
            "--reward",
            "1",
            "--duration",
            "24",
            "--tags",
            "coding",
            "--max-spend-usdc",
            "1.01",
            "--confirm",
        ]
    )

    with patch.object(adapter, "command_from_environment") as command:
        with pytest.raises(adapter.AdapterError, match="below the estimated required spend"):
            adapter.run(args)

    command.assert_not_called()


def test_create_requires_confirmation_before_cli_or_wallet_access(capsys):
    args = adapter.build_parser().parse_args(
        [
            "create",
            "--description",
            "Do the work with tests",
            "--reward",
            "1",
            "--duration",
            "24",
            "--tags",
            "coding",
            "--max-spend-usdc",
            "1.10",
        ]
    )

    with patch.object(adapter, "command_from_environment") as command:
        result = adapter.run(args)

    assert result == 2
    command.assert_not_called()
    output = json.loads(capsys.readouterr().out)
    assert output["confirmationRequired"] is True
    assert output["notSubmitted"] is True


def test_create_checks_base_network_and_invokes_cli_once():
    args = adapter.build_parser().parse_args(
        [
            "create",
            "--description",
            "Do the work with tests",
            "--reward",
            "1",
            "--duration",
            "24",
            "--tags",
            "coding",
            "--max-spend-usdc",
            "1.10",
            "--confirm",
        ]
    )
    calls = []

    def fake_cli(command, *arguments):
        calls.append((tuple(command), arguments))
        if arguments == ("deposit",):
            return adapter.CliResult(
                0,
                json.dumps(
                    {
                        "ok": True,
                        "data": {"address": "0xabc", "network": "Base", "chainId": 8453},
                    }
                ),
                "",
            )
        return adapter.CliResult(0, json.dumps({"taskId": "0x" + "1" * 64}), "")

    with patch.object(adapter, "command_from_environment", return_value=["taskmarket"]), patch.object(
        adapter, "run_cli", side_effect=fake_cli
    ):
        result = adapter.run(args)

    assert result == 0
    assert [call[1][0] for call in calls] == ["deposit", "task"]
    assert calls[1][1][1] == "create"
    assert "--reward" in calls[1][1]
    assert "--tags" in calls[1][1]


def test_create_refuses_non_base_wallet():
    args = adapter.build_parser().parse_args(
        [
            "create",
            "--description",
            "Do the work with tests",
            "--reward",
            "1",
            "--duration",
            "24",
            "--tags",
            "coding",
            "--max-spend-usdc",
            "1.10",
            "--confirm",
        ]
    )

    def fake_cli(command, *arguments):
        assert arguments == ("deposit",)
        return adapter.CliResult(
            0,
            json.dumps(
                {
                    "ok": True,
                    "data": {"address": "0xabc", "network": "Ethereum", "chainId": 1},
                }
            ),
            "",
        )

    with patch.object(adapter, "command_from_environment", return_value=["taskmarket"]), patch.object(
        adapter, "run_cli", side_effect=fake_cli
    ):
        with pytest.raises(adapter.AdapterError, match="must report Base"):
            adapter.run(args)



def test_read_endpoints_validate_task_id_and_use_public_api(capsys):
    task_id = "0x" + "a" * 64
    response = {"id": task_id, "status": "open"}

    with patch.object(adapter, "api_get", return_value=response) as api:
        result = adapter.main(["status", task_id])

    assert result == 0
    api.assert_called_once_with(adapter.DEFAULT_API_URL, f"/api/tasks/{task_id}")
    output = json.loads(capsys.readouterr().out)
    assert output["data"] == response


def test_failed_cli_result_is_not_marked_for_retry(capsys):
    args = adapter.build_parser().parse_args(
        [
            "create",
            "--description",
            "Do the work with tests",
            "--reward",
            "1",
            "--duration",
            "24",
            "--tags",
            "coding",
            "--max-spend-usdc",
            "1.10",
            "--confirm",
        ]
    )

    def fake_cli(command, *arguments):
        if arguments == ("deposit",):
            return adapter.CliResult(
                0,
                json.dumps(
                    {
                        "ok": True,
                        "data": {"address": "0xabc", "network": "Base", "chainId": 8453},
                    }
                ),
                "",
            )
        return adapter.CliResult(1, "", "payment response unavailable")

    with patch.object(adapter, "command_from_environment", return_value=["taskmarket"]), patch.object(
        adapter, "run_cli", side_effect=fake_cli
    ):
        result = adapter.run(args)

    assert result == 1
    output = json.loads(capsys.readouterr().out)
    assert output["retry"] is False
    assert output["paymentState"] == "unknown_or_not_settled"
