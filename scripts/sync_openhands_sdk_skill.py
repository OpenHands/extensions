#!/usr/bin/env python3
"""Auto-generate skills/openhands-sdk/SKILL.md from live data sources.

Data sources:
  1. https://docs.openhands.dev/llms.txt  - SDK doc index (classes, guides, arch)
  2. GitHub API for OpenHands/software-agent-sdk - examples listing + hello world

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

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_PATH = REPO_ROOT / "skills" / "openhands-sdk" / "SKILL.md"

LLMS_TXT_URL = "https://docs.openhands.dev/llms.txt"
EXAMPLES_API_URL = (
    "https://api.github.com/repos/OpenHands/software-agent-sdk"
    "/contents/examples/01_standalone_sdk"
)
HELLO_WORLD_RAW_URL = (
    "https://raw.githubusercontent.com/OpenHands/software-agent-sdk"
    "/main/examples/01_standalone_sdk/01_hello_world.py"
)
EXAMPLES_BASE_URL = (
    "https://github.com/OpenHands/software-agent-sdk"
    "/blob/main/examples/01_standalone_sdk"
)

# ---------- frontmatter (static) ----------

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

# Maps arch page title -> (class name, description override).
# Descriptions come from llms.txt but we clean them up for the table.
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

# ---------- network helpers ----------


def _fetch(url: str, *, accept: str = "text/plain") -> str:
    headers = {"Accept": accept, "User-Agent": "sync-openhands-sdk-skill/1.0"}
    token = os.environ.get("GITHUB_TOKEN")
    if token and "api.github.com" in url:
        headers["Authorization"] = f"token {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode()
    except urllib.error.HTTPError as exc:
        print(f"WARNING: HTTP {exc.code} fetching {url}", file=sys.stderr)
        raise
    except urllib.error.URLError as exc:
        print(f"WARNING: URL error fetching {url}: {exc.reason}", file=sys.stderr)
        raise


def fetch_llms_txt() -> str:
    return _fetch(LLMS_TXT_URL)


def fetch_examples_listing() -> list[dict]:
    raw = _fetch(EXAMPLES_API_URL, accept="application/vnd.github.v3+json")
    return json.loads(raw)


def fetch_hello_world() -> str:
    return _fetch(HELLO_WORLD_RAW_URL)


# ---------- parsers ----------

_LLMS_ENTRY = re.compile(
    r"^- \[(?P<title>[^\]]+)\]\((?P<url>[^)]+)\):\s*(?P<desc>.+)$"
)


def parse_sdk_section(llms_txt: str) -> list[dict]:
    """Return entries from the 'OpenHands Software Agent SDK' section."""
    entries: list[dict] = []
    in_section = False
    for line in llms_txt.splitlines():
        if line.strip() == "## OpenHands Software Agent SDK":
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if not in_section:
            continue
        m = _LLMS_ENTRY.match(line.strip())
        if m:
            entries.append(m.groupdict())
    return entries


def classify_entries(
    entries: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    """Split entries into (api_refs, arch_pages, guides)."""
    api_refs, arch, guides = [], [], []
    for e in entries:
        url = e["url"]
        if "/api-reference/" in url:
            api_refs.append(e)
        elif "/arch/" in url:
            arch.append(e)
        else:
            guides.append(e)
    return api_refs, arch, guides


# ---------- content builders ----------


def build_core_classes_table(
    arch_pages: list[dict], api_refs: list[dict]
) -> str:
    """Build the core classes table from architecture pages and API refs."""
    rows: list[tuple[str, str, str]] = []

    # From arch pages, extract class name + description
    for entry in arch_pages:
        title = entry["title"]
        desc = entry["desc"]
        url = entry["url"]
        class_name = ARCH_CLASS_MAP.get(title)
        if not class_name:
            continue
        # Clean up description
        desc = desc.replace("High-level architecture of the ", "").replace(
            "High-level architecture of ", ""
        )
        desc = desc[0].upper() + desc[1:] if desc else desc
        rows.append((class_name, desc, url))

    lines = ["| Class | Purpose |", "|---|---|"]
    for class_name, desc, url in rows:
        lines.append(f"| [`{class_name}`]({url}) | {desc} |")
    return "\n".join(lines)


def build_api_reference_list(api_refs: list[dict]) -> str:
    """Build a compact list of API reference modules."""
    lines = []
    for entry in api_refs:
        module = entry["title"]  # e.g. "openhands.sdk.agent"
        url = entry["url"]
        lines.append(f"[`{module}`]({url})")
    return ", ".join(lines)


def build_guides_table(guides: list[dict]) -> str:
    """Build the guides table grouped by category."""
    categories: dict[str, list[dict]] = {
        "Getting Started": [],
        "Agent": [],
        "LLM": [],
        "Conversation": [],
        "Tools & MCP": [],
        "Security & Observability": [],
        "Deployment": [],
        "Workflows": [],
    }

    def categorize(entry: dict) -> str:
        url = entry["url"].lower()
        title = entry["title"].lower()
        if any(
            k in url
            for k in ["getting-started", "hello-world", "faq", "/sdk.md"]
        ):
            return "Getting Started"
        if any(k in url for k in ["agent-server/", "workspace", "sandbox"]):
            return "Deployment"
        if any(
            k in url
            for k in [
                "agent-delegation",
                "agent-custom",
                "agent-file-based",
                "agent-settings",
                "agent-stuck",
                "agent-browser",
                "agent-interactive",
                "agent-acp",
                "agent-tom",
                "skill",
                "plugin",
                "hooks",
                "iterative-refinement",
                "critic",
            ]
        ):
            return "Agent"
        if "llm" in url or "reasoning" in url or "streaming" in url:
            return "LLM"
        if "convo" in url or "persistence" in url:
            return "Conversation"
        if any(
            k in url for k in ["tool", "mcp", "parallel-tool", "task-tool"]
        ):
            return "Tools & MCP"
        if any(
            k in url
            for k in ["security", "secret", "observability", "metrics"]
        ):
            return "Security & Observability"
        if any(
            k in url for k in ["github-workflow", "pr-review", "todo", "assign"]
        ):
            return "Workflows"
        if "condenser" in title or "condenser" in url:
            return "Agent"
        return "Agent"  # default

    for entry in guides:
        cat = categorize(entry)
        if cat in categories:
            categories[cat].append(entry)

    lines = []
    for cat, entries in categories.items():
        if not entries:
            continue
        lines.append(f"\n**{cat}**")
        for e in entries:
            lines.append(f"- [{e['title']}]({e['url']}): {e['desc']}")
    return "\n".join(lines)


def build_examples_table(listing: list[dict]) -> str:
    """Build an examples table from the GitHub API listing."""
    rows = []
    for item in sorted(listing, key=lambda x: x["name"]):
        name = item["name"]
        # Convert filename to readable title: 01_hello_world.py -> Hello World
        base = name.removesuffix(".py")
        # Strip numeric prefix like "01_"
        base = re.sub(r"^\d+_", "", base)
        title = base.replace("_", " ").title()
        # Build link
        url = f"{EXAMPLES_BASE_URL}/{name}"
        rows.append(f"- [`{name}`]({url}) - {title}")
    return "\n".join(rows)


def build_hello_world_snippet(source: str) -> str:
    """Extract a clean hello-world snippet from the example source."""
    # Use the actual source, trimmed
    lines = source.strip().splitlines()
    return "\n".join(lines)


def generate_skill_md(
    llms_txt: str,
    examples_listing: list[dict],
    hello_world_source: str,
) -> str:
    """Generate the full SKILL.md content."""
    entries = parse_sdk_section(llms_txt)
    api_refs, arch_pages, guides = classify_entries(entries)

    core_classes = build_core_classes_table(arch_pages, api_refs)
    api_ref_list = build_api_reference_list(api_refs)
    guides_section = build_guides_table(guides)
    examples = build_examples_table(examples_listing)
    hello_world = build_hello_world_snippet(hello_world_source)

    return f"""{FRONTMATTER}

# OpenHands Software Agent SDK

All SDK documentation lives at <https://docs.openhands.dev/sdk>.

For the full topic index, fetch <https://docs.openhands.dev/llms.txt> and read
the "OpenHands Software Agent SDK" section.

## Quick reference

Install: `pip install openhands-sdk openhands-tools`

```python
{hello_world}
```

## Core classes (`openhands.sdk`)

{core_classes}

## API reference

{api_ref_list}

## Guides
{guides_section}

## Examples

Source: [`examples/01_standalone_sdk/`]({EXAMPLES_BASE_URL})

{examples}
"""


# ---------- main ----------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check mode: fail if SKILL.md is out of date (for CI).",
    )
    args = parser.parse_args()

    print("Fetching llms.txt ...", file=sys.stderr)
    llms_txt = fetch_llms_txt()

    print("Fetching examples listing ...", file=sys.stderr)
    try:
        examples_listing = fetch_examples_listing()
    except Exception:
        print(
            "WARNING: Could not fetch examples listing, using empty list",
            file=sys.stderr,
        )
        examples_listing = []

    print("Fetching hello world example ...", file=sys.stderr)
    try:
        hello_world_source = fetch_hello_world()
    except Exception:
        print(
            "WARNING: Could not fetch hello world, using fallback",
            file=sys.stderr,
        )
        hello_world_source = textwrap.dedent("""\
            import os
            from openhands.sdk import LLM, Agent, Conversation, Tool
            from openhands.tools.terminal import TerminalTool
            from openhands.tools.file_editor import FileEditorTool

            llm = LLM(model="anthropic/claude-sonnet-4-5-20250929", api_key=os.getenv("LLM_API_KEY"))
            agent = Agent(llm=llm, tools=[Tool(name=TerminalTool.name), Tool(name=FileEditorTool.name)])
            conversation = Conversation(agent=agent, workspace=os.getcwd())
            conversation.send_message("Hello!")
            conversation.run()""")

    generated = generate_skill_md(llms_txt, examples_listing, hello_world_source)

    if args.check:
        if not SKILL_PATH.exists():
            print(f"ERROR: {SKILL_PATH} does not exist", file=sys.stderr)
            return 1
        current = SKILL_PATH.read_text()
        if current == generated:
            print("SDK skill is up to date. ✓", file=sys.stderr)
            return 0
        else:
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
