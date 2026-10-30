#!/usr/bin/env python3
"""Deterministic hello-world entrypoint for the hello-world-automation plugin.

This script is the entrypoint for a plugin-backed executable automation that
uses the ``script`` runner (``entrypoint.runner == "script"``). It reads the
plugin config, prints a greeting, and fires the automation completion
callback. Because it does not start an agent conversation, it needs no
agent/LLM profile to be pre-provisioned — the automation is created and
dispatched without any ``runtime.agent_profile`` requirement.

Environment variables consumed:
  AUTOMATION_CONFIG_PATH     - path to the resolved plugin config JSON
  AUTOMATION_CALLBACK_URL    - completion callback endpoint (optional)
  AUTOMATION_RUN_ID          - run id for the callback payload (optional)
  AUTOMATION_EVENT_PAYLOAD   - JSON event payload, if event-triggered (optional)
  AUTOMATION_AGENT_PROFILE_NAME / AUTOMATION_LLM_PROFILE_NAME - injected when
                               present; echoed for observability.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def load_config() -> dict:
    path = os.environ.get("AUTOMATION_CONFIG_PATH")
    if not path or not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as exc:
        print(f"WARNING: could not read config at {path}: {exc}", file=sys.stderr)
        return {}


def fire_callback(status: str, error: str | None = None) -> None:
    url = os.environ.get("AUTOMATION_CALLBACK_URL", "")
    if not url:
        return
    body: dict[str, object] = {
        "status": status,
        "run_id": os.environ.get("AUTOMATION_RUN_ID", ""),
    }
    if error:
        body["error"] = error
    token = (
        os.environ.get("AUTOMATION_CALLBACK_API_KEY")
        or os.environ.get("OPENHANDS_API_KEY")
        or ""
    )
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), headers=headers
        )
        urllib.request.urlopen(req, timeout=10)
    except (urllib.error.URLError, OSError) as exc:
        print(f"WARNING: callback failed: {exc}", file=sys.stderr)


def main() -> int:
    config = load_config()
    message = config.get("message") or "Hello from the automation plugin"

    print("=== HELLO WORLD AUTOMATION ===")
    print(f"  message: {message}")
    print(
        "  agent_profile_name: "
        f"{os.environ.get('AUTOMATION_AGENT_PROFILE_NAME') or '(none)'}"
    )
    print(
        "  llm_profile_name: "
        f"{os.environ.get('AUTOMATION_LLM_PROFILE_NAME') or '(none)'}"
    )

    event_payload = os.environ.get("AUTOMATION_EVENT_PAYLOAD", "")
    if event_payload:
        try:
            event = json.loads(event_payload)
            event_type = event.get("type") or event.get("event_type") or "(unknown)"
            print(f"  event_context: {event_type}")
            print("  (responding with the standard greeting plus event notice)")
        except json.JSONDecodeError:
            print("  event_context: (unparseable)")
    else:
        print("  event_context: (none)")

    print(f"\n{message} \U0001f44b")
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:  # pragma: no cover - defensive top-level guard
        fire_callback("FAILED", str(exc))
        raise
    fire_callback("COMPLETED" if code == 0 else "FAILED")
    sys.exit(code)
