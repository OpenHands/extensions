#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import sys
import pathlib
import urllib.parse
import urllib.request

_SCRIPTS_DIR = pathlib.Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _http import DiscordHTTPError, post_json


def _with_wait_param(url: str, *, wait: bool) -> str:
    if not wait:
        return url

    parts = urllib.parse.urlsplit(url)
    query = dict(urllib.parse.parse_qsl(parts.query, keep_blank_values=True))
    query["wait"] = "true"

    return urllib.parse.urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urllib.parse.urlencode(query), parts.fragment)
    )


def _request_json(url: str, payload: dict[str, object], *, wait: bool, max_retries: int) -> dict[str, object] | None:
    request_url = _with_wait_param(url, wait=wait)

    req = urllib.request.Request(
        request_url,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "User-Agent": "OpenHands-DiscordSkill/1.0 (+https://github.com/OpenHands/skills)",
        },
    )

    return post_json(request=req, payload=payload, max_retries=max_retries)


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
