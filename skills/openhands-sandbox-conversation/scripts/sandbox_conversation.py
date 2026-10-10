#!/usr/bin/env python3
"""Find the sandbox behind a conversation (or this agent's own sandbox) and start a
new conversation in it, using only the OpenHands app server V1 API.

Auth: OPENHANDS_CLOUD_API_KEY or OPENHANDS_API_KEY (Bearer).
Server: --base-url, else OPENHANDS_BASE_URL, else https://app.all-hands.dev.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

CONVERSATION_ID_RE = re.compile(r"[0-9a-f]{32}")


def request(base_url, method, path, body=None):
    key = os.environ.get("OPENHANDS_CLOUD_API_KEY") or os.environ.get("OPENHANDS_API_KEY")
    if not key:
        sys.exit("Set OPENHANDS_CLOUD_API_KEY or OPENHANDS_API_KEY")
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path} -> HTTP {e.code}: {e.read().decode()[:500]}")


def agent_server_url(sandbox):
    urls = sandbox["exposed_urls"] or []
    return next((u["url"] for u in urls if u["name"] == "AGENT_SERVER"), None)


def own_sandbox_id(base_url):
    """The sandbox whose AGENT_SERVER url equals $RUNTIME_URL is this agent's own."""
    runtime_url = os.environ.get("RUNTIME_URL")
    if not runtime_url:
        sys.exit("RUNTIME_URL is not set; this does not look like an OpenHands sandbox")
    page_id = None
    while True:
        query = {"limit": 100, **({"page_id": page_id} if page_id else {})}
        page = request(base_url, "GET", "/api/v1/sandboxes/search?" + urllib.parse.urlencode(query))
        for sandbox in page["items"]:
            if (agent_server_url(sandbox) or "").rstrip("/") == runtime_url.rstrip("/"):
                return sandbox["id"]
        page_id = page.get("next_page_id")
        if not page_id:
            sys.exit(f"No sandbox exposes AGENT_SERVER {runtime_url} for this API key")


def conversation_sandbox_id(base_url, conversation):
    match = CONVERSATION_ID_RE.search(conversation.replace("-", ""))
    if not match:
        sys.exit(f"No conversation id found in {conversation!r}")
    items = request(base_url, "GET", f"/api/v1/app-conversations?ids={match.group()}")
    if not items or items[0] is None:
        sys.exit(f"Conversation {match.group()} not found")
    return items[0]["sandbox_id"]


def resolve_sandbox_id(args):
    if args.sandbox_id:
        return args.sandbox_id
    if args.conversation:
        return conversation_sandbox_id(args.base_url, args.conversation)
    return own_sandbox_id(args.base_url)


def start_conversation(args):
    sandbox_id = resolve_sandbox_id(args)
    body = {
        "sandbox_id": sandbox_id,
        "initial_message": {"role": "user", "content": [{"type": "text", "text": args.message}]},
    }
    if args.title:
        body["title"] = args.title
    task = request(args.base_url, "POST", "/api/v1/app-conversations", body)
    deadline = time.time() + args.timeout
    while task["status"] not in ("READY", "ERROR"):
        if time.time() > deadline:
            sys.exit(f"Start task {task['id']} still {task['status']} after {args.timeout}s")
        time.sleep(3)
        task = request(args.base_url, "GET", f"/api/v1/app-conversations/start-tasks?ids={task['id']}")[0]
    if task["status"] == "ERROR":
        sys.exit(f"Start task {task['id']} failed: {task.get('detail')}")
    conversation_id = task["app_conversation_id"]
    print(json.dumps({
        "sandbox_id": sandbox_id,
        "conversation_id": conversation_id,
        "url": f"{args.base_url.rstrip('/')}/canvas/conversations/{conversation_id}",
    }, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--base-url", default=os.environ.get("OPENHANDS_BASE_URL", "https://app.all-hands.dev"))
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("whoami", help="print this agent's own sandbox id")

    find = sub.add_parser("find", help="print the sandbox id of a conversation id or URL")
    find.add_argument("conversation")

    start = sub.add_parser("start", help="start a conversation in a sandbox (default: this agent's own)")
    target = start.add_mutually_exclusive_group()
    target.add_argument("--sandbox-id")
    target.add_argument("--conversation", help="start in the sandbox of this conversation id or URL")
    start.add_argument("--message", required=True, help="self-contained initial prompt")
    start.add_argument("--title")
    start.add_argument("--timeout", type=int, default=300)

    args = parser.parse_args()
    if args.command == "whoami":
        print(own_sandbox_id(args.base_url))
    elif args.command == "find":
        print(conversation_sandbox_id(args.base_url, args.conversation))
    else:
        start_conversation(args)


if __name__ == "__main__":
    main()
