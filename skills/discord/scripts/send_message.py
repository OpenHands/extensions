#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request

from _http import DiscordHTTPError, post_json


API_BASE = "https://discord.com/api/v10"


def _post_message(
    *,
    token: str,
    channel_id: str,
    payload: dict[str, object],
    max_retries: int,
) -> dict[str, object] | None:
    url = f"{API_BASE}/channels/{channel_id}/messages"

    req = urllib.request.Request(
        url,
        method="POST",
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "OpenHands-DiscordSkill/1.0 (+https://github.com/OpenHands/skills)",
        },
    )

    try:
        return post_json(request=req, payload=payload, max_retries=max_retries)
    except DiscordHTTPError as e:
        raise DiscordHTTPError(f"Discord API call failed. channel_id={channel_id}. {e}") from e


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

    try:
        result = _post_message(
            token=args.token,
            channel_id=args.channel_id,
            payload=payload,
            max_retries=max(0, args.max_retries),
        )
    except DiscordHTTPError as e:
        print(str(e), file=sys.stderr)
        return 1

    if result is not None:
        print(json.dumps(result, indent=2, sort_keys=True))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
