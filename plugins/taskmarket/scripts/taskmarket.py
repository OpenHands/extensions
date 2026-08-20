#!/usr/bin/env python3
"""Safe OpenHands adapter for TaskMarket read and create workflows.

Read operations use the public TaskMarket API. Writes are delegated to the
first-party TaskMarket CLI after this adapter has performed a preview,
explicit-confirmation, Base-network, and spend-ceiling check. This module
never opens or interprets the CLI keystore.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_UP
from typing import Any, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_API_URL = "https://api.taskmarket.dev"
BASE_CHAIN_ID = 8453
PLATFORM_FEE_BPS = 750
RELAY_BUFFER_USDC = Decimal("0.001")
USDC_QUANTUM = Decimal("0.000001")
TASK_ID_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
ALLOWED_MODES = ("bounty", "claim", "pitch", "benchmark", "auction")
ALLOWED_STATUSES = (
    "open",
    "claimed",
    "worker_selected",
    "pending_approval",
    "review",
    "appealing",
    "disputed",
    "completed",
    "expired",
    "cancelled",
    "ALL",
)
ALLOWED_SORTS = ("newest", "reward_desc", "reward_asc", "deadline_asc")


class AdapterError(ValueError):
    """An expected validation, API, or CLI integration error."""


@dataclass(frozen=True)
class CliResult:
    returncode: int
    stdout: str
    stderr: str


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def parse_usdc(value: str, *, field: str, allow_zero: bool = False) -> Decimal:
    try:
        amount = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise AdapterError(f"{field} must be a decimal USDC amount") from exc

    if not amount.is_finite():
        raise AdapterError(f"{field} must be finite")
    if amount < 0 or (amount == 0 and not allow_zero):
        minimum = "non-negative" if allow_zero else "positive"
        raise AdapterError(f"{field} must be {minimum}")
    if amount.as_tuple().exponent < -6:
        raise AdapterError(f"{field} supports at most six decimal places")
    return amount.quantize(USDC_QUANTUM)


def format_usdc(amount: Decimal) -> str:
    return f"{amount.quantize(USDC_QUANTUM):.6f}".rstrip("0").rstrip(".") or "0"


def usdc_base_units(amount: Decimal) -> str:
    return str(int(amount.quantize(USDC_QUANTUM) * 1_000_000))


def parse_duration(value: str) -> Decimal:
    try:
        hours = Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise AdapterError("duration must be a positive number of hours") from exc
    if not hours.is_finite() or hours <= 0:
        raise AdapterError("duration must be a positive number of hours")
    return hours


def parse_tags(value: str) -> list[str]:
    tags = [tag.strip() for tag in value.split(",") if tag.strip()]
    if not tags:
        raise AdapterError("at least one non-empty tag is required")
    if len(tags) > 10:
        raise AdapterError("at most ten tags are allowed")
    if any(len(tag) > 100 for tag in tags):
        raise AdapterError("each tag must be at most 100 characters")
    return tags


def validate_api_base(value: str) -> str:
    from urllib.parse import urlparse

    parsed = urlparse(value)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise AdapterError("api URL must be an absolute http(s) URL")
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise AdapterError("non-local TaskMarket API URLs must use HTTPS")
    return value.rstrip("/")


def validate_task_id(value: str) -> str:
    if not TASK_ID_RE.fullmatch(value):
        raise AdapterError("task ID must be a 0x-prefixed 32-byte hex value")
    return value


def estimated_max_spend(reward: Decimal, fee_bps: int = PLATFORM_FEE_BPS) -> Decimal:
    fee = (reward * Decimal(fee_bps) / Decimal(10_000)).quantize(
        USDC_QUANTUM, rounding=ROUND_UP
    )
    return (reward + fee + RELAY_BUFFER_USDC).quantize(USDC_QUANTUM, rounding=ROUND_UP)


def deadline_from_duration(duration: Decimal, now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    deadline = current + timedelta(seconds=float(duration * Decimal(3600)))
    return deadline.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_preview(args: argparse.Namespace, *, now: datetime | None = None) -> dict[str, Any]:
    description = args.description.strip()
    if not description:
        raise AdapterError("description must not be empty")
    if len(description) > 10_000:
        raise AdapterError("description must be at most 10000 characters")

    reward = parse_usdc(args.reward, field="reward")
    duration = parse_duration(args.duration)
    tags = parse_tags(args.tags)
    mode = args.mode
    if mode not in ALLOWED_MODES:
        raise AdapterError(f"mode must be one of: {', '.join(ALLOWED_MODES)}")

    max_spend = parse_usdc(args.max_spend_usdc, field="max-spend-usdc")
    estimated = estimated_max_spend(reward)
    return {
        "description": description,
        "rewardUsdc": format_usdc(reward),
        "durationHours": format_usdc(duration),
        "deadlineUtc": deadline_from_duration(duration, now=now),
        "tags": tags,
        "mode": mode,
        "network": {
            "name": "Base",
            "chainId": BASE_CHAIN_ID,
            "asset": "USDC",
        },
        "maxSpendUsdc": format_usdc(max_spend),
        "estimatedMaxSpendUsdc": format_usdc(estimated),
        "platformFeeEstimateBps": PLATFORM_FEE_BPS,
        "relayBufferUsdc": format_usdc(RELAY_BUFFER_USDC),
    }


def api_get(api_base: str, path: str, params: dict[str, str] | None = None) -> Any:
    query = f"?{urlencode(params)}" if params else ""
    url = f"{api_base}{path}{query}"
    request = Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise AdapterError(f"TaskMarket API returned HTTP {exc.code}: {body[:500]}") from exc
    except URLError as exc:
        raise AdapterError(f"TaskMarket API request failed: {exc.reason}") from exc
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AdapterError("TaskMarket API returned invalid JSON") from exc


def command_from_environment() -> list[str]:
    configured = os.environ.get("TASKMARKET_CLI")
    if configured:
        command = shlex.split(configured)
        if command:
            return command

    installed = shutil.which("taskmarket")
    if installed:
        return [installed]

    raise AdapterError(
        "TaskMarket CLI not found; install @lucid-agents/taskmarket and run taskmarket init first"
    )


def run_cli(command: Sequence[str], *arguments: str) -> CliResult:
    try:
        completed = subprocess.run(
            [*command, *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AdapterError(f"TaskMarket CLI invocation failed: {exc}") from exc
    return CliResult(completed.returncode, completed.stdout, completed.stderr)


def parse_cli_json(result: CliResult) -> Any:
    text = result.stdout.strip()
    if not text:
        return {"stdout": "", "stderr": result.stderr.strip()}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"stdout": text, "stderr": result.stderr.strip()}


def cli_deposit_info(command: Sequence[str]) -> dict[str, Any]:
    result = run_cli(command, "deposit")
    payload = parse_cli_json(result)
    if result.returncode != 0:
        raise AdapterError(f"TaskMarket CLI deposit check failed: {payload}")
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    if not isinstance(payload, dict) or payload.get("chainId") != BASE_CHAIN_ID:
        chain_id = payload.get("chainId") if isinstance(payload, dict) else None
        raise AdapterError(f"TaskMarket wallet must report Base chain ID {BASE_CHAIN_ID}; got {chain_id}")
    return payload


def task_link(api_base: str, task_id: str) -> str:
    return f"{api_base}/api/tasks/{validate_task_id(task_id)}"


def extract_task_id(payload: Any) -> str | None:
    candidates: list[Any] = [payload]
    if isinstance(payload, dict):
        candidates.extend([payload.get("data"), payload.get("result")])
    for candidate in candidates:
        if isinstance(candidate, dict):
            task_id = candidate.get("taskId") or candidate.get("id")
            if isinstance(task_id, str) and TASK_ID_RE.fullmatch(task_id):
                return task_id
    return None


def add_task_arguments(parser: argparse.ArgumentParser, *, require_spend: bool = True) -> None:
    parser.add_argument(
        "--description", required=True, help="Exact task description and acceptance criteria"
    )
    parser.add_argument("--reward", required=True, help="Positive USDC reward, up to six decimals")
    parser.add_argument("--duration", required=True, help="Task duration in hours")
    parser.add_argument("--tags", required=True, help="Comma-separated tags, one to ten")
    parser.add_argument("--mode", choices=ALLOWED_MODES, default="bounty")
    parser.add_argument(
        "--max-spend-usdc",
        required=require_spend,
        help="User-approved maximum spend including fee buffer",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Safe OpenHands adapter for TaskMarket")
    parser.add_argument(
        "--api-url",
        default=os.environ.get("TASKMARKET_API_URL", DEFAULT_API_URL),
        help="TaskMarket API base URL (default: %(default)s)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List public tasks")
    list_parser.add_argument("--status", choices=ALLOWED_STATUSES, default="open")
    list_parser.add_argument("--sort", choices=ALLOWED_SORTS, default="newest")
    list_parser.add_argument("--limit", type=int, default=20)
    list_parser.add_argument("--min-reward", help="Minimum reward in USDC")
    list_parser.add_argument(
        "--deadline-hours", type=int, help="Only tasks expiring within this many hours"
    )

    status_parser = subparsers.add_parser("status", help="Get one task")
    status_parser.add_argument("task_id")

    submissions_parser = subparsers.add_parser(
        "submissions", help="List submissions for human review"
    )
    submissions_parser.add_argument("task_id")

    preview_parser = subparsers.add_parser("preview", help="Print an exact, non-paying task preview")
    add_task_arguments(preview_parser)

    create_parser = subparsers.add_parser("create", help="Create once through the first-party CLI")
    add_task_arguments(create_parser)
    create_parser.add_argument(
        "--confirm",
        action="store_true",
        help="Explicitly approve the exact preview and authorize one paid CLI call",
    )
    return parser


def run(args: argparse.Namespace) -> int:
    api_base = validate_api_base(args.api_url)

    if args.command == "list":
        if not 1 <= args.limit <= 100:
            raise AdapterError("limit must be between 1 and 100")
        params: dict[str, str] = {
            "status": args.status,
            "sort": args.sort,
            "limit": str(args.limit),
        }
        if args.min_reward is not None:
            params["minReward"] = usdc_base_units(
                parse_usdc(args.min_reward, field="min-reward", allow_zero=True)
            )
        if args.deadline_hours is not None:
            if args.deadline_hours <= 0:
                raise AdapterError("deadline-hours must be positive")
            params["deadlineHours"] = str(args.deadline_hours)
        emit(
            {
                "success": True,
                "endpoint": f"{api_base}/api/tasks",
                "data": api_get(api_base, "/api/tasks", params),
            }
        )
        return 0

    task_id = None
    if args.command in {"status", "submissions"}:
        task_id = validate_task_id(args.task_id)
        path = f"/api/tasks/{task_id}"
        if args.command == "submissions":
            path += "/submissions"
        emit({"success": True, "endpoint": f"{api_base}{path}", "data": api_get(api_base, path)})
        return 0

    preview = build_preview(args)
    if args.command == "preview":
        emit({"success": True, "notSubmitted": True, "preview": preview})
        return 0

    if not args.confirm:
        emit(
            {
                "success": False,
                "notSubmitted": True,
                "confirmationRequired": True,
                "message": "Show this exact preview to the user and rerun only with --confirm after explicit approval.",
                "preview": preview,
            }
        )
        return 2

    max_spend = parse_usdc(args.max_spend_usdc, field="max-spend-usdc")
    estimated = parse_usdc(preview["estimatedMaxSpendUsdc"], field="estimated-max-spend-usdc")
    if max_spend < estimated:
        raise AdapterError(
            f"max-spend-usdc ({format_usdc(max_spend)}) is below the estimated required spend ({format_usdc(estimated)})"
        )

    command = command_from_environment()
    wallet = cli_deposit_info(command)
    cli_arguments = (
        "task",
        "create",
        "--description",
        preview["description"],
        "--reward",
        preview["rewardUsdc"],
        "--duration",
        preview["durationHours"],
        "--mode",
        preview["mode"],
        "--tags",
        ",".join(preview["tags"]),
    )
    result = run_cli(command, *cli_arguments)
    payload = parse_cli_json(result)
    if result.returncode != 0:
        emit(
            {
                "success": False,
                "retry": False,
                "paymentState": "unknown_or_not_settled",
                "message": "The first-party CLI failed; do not retry blindly. Inspect TaskMarket using the same wallet and idempotency information.",
                "wallet": {
                    "address": wallet.get("address"),
                    "network": wallet.get("network"),
                    "chainId": wallet.get("chainId"),
                },
                "preview": preview,
                "result": payload,
            }
        )
        return 1

    response: dict[str, Any] = {
        "success": True,
        "retry": False,
        "paymentState": "accepted_by_cli",
        "wallet": {
            "address": wallet.get("address"),
            "network": wallet.get("network"),
            "chainId": wallet.get("chainId"),
        },
        "preview": preview,
        "result": payload,
    }
    created_id = extract_task_id(payload)
    if created_id:
        response["taskId"] = created_id
        response["taskUrl"] = task_link(api_base, created_id)
    emit(response)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except AdapterError as exc:
        emit({"success": False, "notSubmitted": True, "error": str(exc)})
        return 2


if __name__ == "__main__":
    sys.exit(main())
