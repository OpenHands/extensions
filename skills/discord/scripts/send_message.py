#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request


API_BASE = "https://discord.com/api/v10"


def _post_message(*, token: str, channel_id: str, payload: dict, wait: bool, max_retries: int) -> dict | None:
    url = f"{API_BASE}/channels/{channel_id}/messages"

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bot {token}",
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

            msg = f"Discord API call failed (HTTP {e.code})."
            if body:
                msg += f" Response: {body[:500]}"
            raise RuntimeError(msg) from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"Discord API call failed ({e}).") from e


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a message to a Discord channel using a bot token.")
    parser.add_argument(
        "--token",
        default=os.getenv("DISCORD_BOT_TOKEN"),
        help="Bot token (default: $DISCORD_BOT_TOKEN)",
    )
    parser.add_argument(
        "--channel-id",
        default=os.getenv("DISCORD_CHANNEL_ID"),
        help="Channel ID (default: $DISCORD_CHANNEL_ID)",
    )
    parser.add_argument(
        "--content",
        help="Message content (max 2000 characters). If omitted, read from stdin.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Return the created message object (Discord always returns it; kept for parity with webhook tool).",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Retries on HTTP 429 (default: 3).",
    )
    parser.add_argument(
        "--allow-mentions",
        action="store_true",
        help="Allow Discord to parse mentions. Default is safe (no mentions).",
    )

    args = parser.parse_args()

    if not args.token:
        print("Missing --token (or set DISCORD_BOT_TOKEN).", file=sys.stderr)
        return 2

    if not args.channel_id:
        print("Missing --channel-id (or set DISCORD_CHANNEL_ID).", file=sys.stderr)
        return 2

    content = args.content
    if content is None:
        content = sys.stdin.read().strip()

    if not content:
        print("No content provided (use --content or stdin).", file=sys.stderr)
        return 2

    payload: dict = {"content": content}
    if not args.allow_mentions:
        payload["allowed_mentions"] = {"parse": []}

    result = _post_message(
        token=args.token,
        channel_id=args.channel_id,
        payload=payload,
        wait=args.wait,
        max_retries=max(0, args.max_retries),
    )

    if result is not None:
        print(json.dumps(result, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
