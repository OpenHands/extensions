#!/usr/bin/env python3
"""Auto-generate skills/openhands-sdk/SKILL.md from live data sources.

Data sources:
  1. https://docs.openhands.dev/llms.txt  - SDK doc index
  2. GitHub API for OpenHands/software-agent-sdk - examples + hello world

Usage:
  python scripts/sync_openhands_sdk_skill.py           # regenerate SKILL.md
  python scripts/sync_openhands_sdk_skill.py --check   # CI mode: fail if stale
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import textwrap
import urllib.error
import urllib.request
from pathlib import Path

SKILL_PATH = Path(__file__).resolve().parent.parent / "skills" / "openhands-sdk" / "SKILL.md"
LLMS_TXT_URL = "https://docs.openhands.dev/llms.txt"
GH_API = "https://api.github.com/repos/OpenHands/software-agent-sdk/contents/examples"
GH_RAW = "https://raw.githubusercontent.com/OpenHands/software-agent-sdk/main"
GH_BROWSE = "https://github.com/OpenHands/software-agent-sdk/blob/main/examples"
GH_TREE = "https://github.com/OpenHands/software-agent-sdk/tree/main/examples"
HELLO_WORLD = f"{GH_RAW}/examples/01_standalone_sdk/01_hello_world.py"

FRONTMATTER = """\
---
name: openhands-sdk
description: >-
  Reference skill for the OpenHands Software Agent SDK - the Python framework
  for building AI agents that write software. Use when you need to build agents
  with the SDK, create custom tools, configure LLMs, manage conversations,
  delegate to sub-agents, or deploy agents locally or remotely.
triggers:
- openhands-sdk
- openhands sdk
- software-agent-sdk
- agent-sdk
- /sdk
---"""

# Maps llms.txt arch-page title -> class name shown in the table.
ARCH_CLASS_MAP = {
    "Agent": "Agent",
    "LLM": "LLM",
    "Conversation": "Conversation",
    "Events": "Event",
    "Skill": "Skill",
    "Condenser": "Condenser",
    "Security": "SecurityAnalyzer",
    "Tool System & MCP": "Tool / ToolDefinition",
    "Workspace": "Workspace",
}

_ENTRY_RE = re.compile(r"^- \[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\):\s*(?P<desc>.+)$")


# -- network --

def _fetch(url: str, accept: str = "text/plain") -> str:
    headers = {"Accept": accept, "User-Agent": "sync-sdk-skill/1.0"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode()


def _fetch_json(url: str) -> list | dict:
    return json.loads(_fetch(url, accept="application/vnd.github.v3+json"))


def _fetch_or(url: str, fallback, **kw):
    try:
        return _fetch(url, **kw) if "accept" not in kw else _fetch(url, **kw)
    except Exception as e:
        print(f"WARNING: {e} — using fallback", file=sys.stderr)
        return fallback


# -- llms.txt parsing --

def parse_sdk_entries(llms_txt: str) -> list[dict]:
    """Extract entries from the 'OpenHands Software Agent SDK' section."""
    entries, in_section = [], False
    for line in llms_txt.splitlines():
        stripped = line.strip()
        if stripped == "## OpenHands Software Agent SDK":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section and (m := _ENTRY_RE.match(stripped)):
            entries.append(m.groupdict())
    return entries


# -- content builders --

def build_classes_table(entries: list[dict]) -> str:
    lines = ["| Class | Purpose |", "|---|---|"]
    for e in entries:
        if "/arch/" not in e["url"]:
            continue
        class_name = ARCH_CLASS_MAP.get(e["title"])
        if not class_name:
            continue
        desc = re.sub(r"^High-level architecture of (the )?", "", e["desc"])
        desc = desc[0].upper() + desc[1:]
        lines.append(f"| [`{class_name}`]({e['url']}) | {desc} |")
    return "\n".join(lines)


def build_api_refs(entries: list[dict]) -> str:
    return ", ".join(
        f"[`{e['title']}`]({e['url']})"
        for e in entries if "/api-reference/" in e["url"]
    )


def build_guides(entries: list[dict]) -> str:
    return "\n".join(
        f"- [{e['title']}]({e['url']}): {e['desc']}"
        for e in entries
        if "/api-reference/" not in e["url"] and "/arch/" not in e["url"]
    )


def build_examples(categories: dict[str, list[dict]]) -> str:
    lines = [f"Source: [`examples/`]({GH_TREE})", ""]
    for dir_name, items in categories.items():
        lines.append(f"### [`{dir_name}/`]({GH_TREE}/{dir_name})")
        lines.append("")
        for item in sorted(items, key=lambda x: x["name"]):
            name = item["name"]
            if name.startswith(".") or name == "__pycache__":
                continue
            prefix = GH_TREE if item.get("type") == "dir" else GH_BROWSE
            lines.append(f"- [`{name}`]({prefix}/{dir_name}/{name})")
        lines.append("")
    return "\n".join(lines)


def fetch_examples() -> dict[str, list[dict]]:
    top = _fetch_json(GH_API)
    categories: dict[str, list[dict]] = {}
    for item in sorted(top, key=lambda x: x["name"]):
        if item["type"] != "dir":
            continue
        try:
            categories[item["name"]] = _fetch_json(f"{GH_API}/{item['name']}")
        except Exception as e:
            print(f"WARNING: examples/{item['name']}: {e}", file=sys.stderr)
    return categories


# -- generate --

HELLO_WORLD_FALLBACK = textwrap.dedent("""\
    import os
    from openhands.sdk import LLM, Agent, Conversation, Tool
    from openhands.tools.terminal import TerminalTool
    from openhands.tools.file_editor import FileEditorTool

    llm = LLM(model="anthropic/claude-sonnet-4-5-20250929", api_key=os.getenv("LLM_API_KEY"))
    agent = Agent(llm=llm, tools=[Tool(name=TerminalTool.name), Tool(name=FileEditorTool.name)])
    conversation = Conversation(agent=agent, workspace=os.getcwd())
    conversation.send_message("Hello!")
    conversation.run()""")


def generate() -> str:
    print("Fetching llms.txt ...", file=sys.stderr)
    llms_txt = _fetch(LLMS_TXT_URL)
    entries = parse_sdk_entries(llms_txt)

    print("Fetching examples ...", file=sys.stderr)
    try:
        examples = fetch_examples()
    except Exception:
        examples = {}

    print("Fetching hello world ...", file=sys.stderr)
    hello = _fetch_or(HELLO_WORLD, HELLO_WORLD_FALLBACK).strip()

    return f"""{FRONTMATTER}

# OpenHands Software Agent SDK

All SDK documentation lives at <https://docs.openhands.dev/sdk>.

For the full topic index, fetch <https://docs.openhands.dev/llms.txt> and read
the "OpenHands Software Agent SDK" section.

## Quick reference

Install: `pip install openhands-sdk openhands-tools`

```python
{hello}
```

## Core classes (`openhands.sdk`)

{build_classes_table(entries)}

## API reference

{build_api_refs(entries)}

## Guides

{build_guides(entries)}

## Examples

{build_examples(examples)}
"""


# -- main --

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="CI mode: fail if stale")
    args = parser.parse_args()

    generated = generate()

    if args.check:
        current = SKILL_PATH.read_text() if SKILL_PATH.exists() else ""
        if current == generated:
            print("SDK skill is up to date. ✓", file=sys.stderr)
            return 0
        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            generated.splitlines(keepends=True),
            fromfile="current SKILL.md",
            tofile="generated SKILL.md",
        )
        sys.stdout.writelines(diff)
        print(
            "\nERROR: SDK skill is out of date. "
            "Run: python scripts/sync_openhands_sdk_skill.py",
            file=sys.stderr,
        )
        return 1

    SKILL_PATH.write_text(generated)
    print(f"Wrote {SKILL_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
