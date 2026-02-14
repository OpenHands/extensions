#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


def _request_json(url: str, payload: dict, *, wait: bool, max_retries: int) -> dict | None:
    request_url = url
    if wait and "?" not in request_url:
        request_url += "?wait=true"
    elif wait and "wait=" not in request_url:
        request_url += "&wait=true"

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        request_url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "OpenHands-DiscordSkill/1.0 (+https://github.com/OpenHands/skills)",
        },
    )

    attempt = 0
    while True:
        attempt += 1
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                if not body:
                    return None
                return json.loads(body)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""

            if e.code == 429 and attempt <= max_retries:
                retry_after = None
                try:
                    parsed = json.loads(body) if body else {}
                    retry_after = parsed.get("retry_after")
                except Exception:
                    retry_after = None

                if retry_after is None:
                    retry_after_hdr = e.headers.get("Retry-After")
                    if retry_after_hdr is not None:
                        try:
                            retry_after = float(retry_after_hdr)
                        except ValueError:
                            retry_after = None

                if retry_after is None:
                    retry_after = 1.0

                time.sleep(float(retry_after))
                continue

            msg = f"Webhook POST failed (HTTP {e.code})."
            if body:
                msg += f" Response: {body[:500]}"
            raise RuntimeError(msg) from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Webhook POST failed ({e}).") from e


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Post a message to a Discord incoming webhook. "
            "The webhook URL is secret; avoid printing/logging it."
        )
    )
    parser.add_argument(
        "--webhook-url",
        default=os.getenv("DISCORD_WEBHOOK_URL"),
        help="Incoming webhook URL (default: $DISCORD_WEBHOOK_URL)",
    )
    parser.add_argument(
        "--content",
        help="Message content (max 2000 characters). If omitted, read from stdin.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Add ?wait=true to get the created message object.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retries on HTTP 429 (default: 3).",
    )

    args = parser.parse_args()

    if not args.webhook_url:
        print("Missing --webhook-url (or set DISCORD_WEBHOOK_URL).", file=sys.stderr)
        return 2

    content = args.content
    if content is None:
        content = sys.stdin.read().strip()

    if not content:
        print("No content provided (use --content or stdin).", file=sys.stderr)
        return 2

    payload = {
        "content": content,
        "allowed_mentions": {"parse": []},
    }

    result = _request_json(
        args.webhook_url,
        payload,
        wait=args.wait,
        max_retries=max(0, args.max_retries),
    )

    if result is not None:
        print(json.dumps(result, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
