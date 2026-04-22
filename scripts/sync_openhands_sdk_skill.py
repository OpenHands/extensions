#!/usr/bin/env python3
"""Sync the openhands-sdk skill with the OpenHands docs repo.

Fetches the SDK section of llms.txt from OpenHands/docs and updates the
"Additional Features" table in skills/openhands-sdk/SKILL.md so that newly
added (or removed) guides are reflected automatically.

Usage:
    python scripts/sync_openhands_sdk_skill.py              # write changes
    python scripts/sync_openhands_sdk_skill.py --check      # CI mode — exit 1 if out of sync
    python scripts/sync_openhands_sdk_skill.py --diff       # print what would change

The script is intentionally conservative: it only touches the "Additional
Features" table, leaving the rest of the hand-curated SKILL.md intact.
New guides that already have a dedicated section in the SKILL.md body
(identified by their URL appearing elsewhere) are excluded from the table
to avoid duplication.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = REPO_ROOT / "skills" / "openhands-sdk" / "SKILL.md"
LLMS_TXT_URL = "https://raw.githubusercontent.com/OpenHands/docs/main/llms.txt"

# Markers that delimit the auto-synced table in SKILL.md
TABLE_BEGIN = "<!-- BEGIN AUTO-SYNCED ADDITIONAL FEATURES -->"
TABLE_END = "<!-- END AUTO-SYNCED ADDITIONAL FEATURES -->"

# Guide URL categories to EXCLUDE from the "Additional Features" table.
# These are either covered by dedicated sections in SKILL.md or are
# architecture/API reference pages (not actionable guides).
EXCLUDE_PATTERNS = [
    r"/sdk/arch/",           # architecture pages (not actionable guides)
    r"/sdk/api-reference/",  # API reference (already listed in its own section)
    r"/sdk/faq",             # FAQ
    r"/sdk/getting-started", # covered by Installation section
    r"/sdk\.md$",            # SDK index page
]


def fetch_llms_txt() -> str:
    """Download llms.txt from the docs repo."""
    req = urllib.request.Request(LLMS_TXT_URL)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def extract_sdk_guides(llms_txt: str) -> list[tuple[str, str]]:
    """Parse the SDK section of llms.txt, returning (title, url) pairs.

    Only returns guide-level entries (under /sdk/guides/).
    """
    in_sdk_section = False
    entries: list[tuple[str, str]] = []

    for line in llms_txt.splitlines():
        if line.startswith("## OpenHands Software Agent SDK"):
            in_sdk_section = True
            continue
        if line.startswith("## ") and in_sdk_section:
            break
        if not in_sdk_section:
            continue

        # Lines look like: - [Title](https://docs.openhands.dev/sdk/guides/foo.md): Description
        m = re.match(r"^- \[(.+?)\]\((https://docs\.openhands\.dev/sdk/.+?)\)", line)
        if m:
            title = m.group(1)
            url = m.group(2)
            # Strip trailing .md from URL
            if url.endswith(".md"):
                url = url[:-3]
            entries.append((title, url))

    return entries


def urls_in_skill_body(skill_text: str) -> set[str]:
    """Return all docs.openhands.dev/sdk URLs found in the SKILL.md body
    OUTSIDE the auto-synced table markers."""
    # Remove the auto-synced block if present
    cleaned = skill_text
    if TABLE_BEGIN in cleaned and TABLE_END in cleaned:
        before = cleaned[: cleaned.index(TABLE_BEGIN)]
        after = cleaned[cleaned.index(TABLE_END) + len(TABLE_END) :]
        cleaned = before + after

    urls = set()
    for m in re.finditer(r"https://docs\.openhands\.dev/sdk[^\s>)]*", cleaned):
        url = m.group(0).rstrip(".")
        urls.add(url)
    return urls


def should_exclude(url: str) -> bool:
    """Return True if the URL matches an exclude pattern."""
    return any(re.search(pat, url) for pat in EXCLUDE_PATTERNS)


def build_table(entries: list[tuple[str, str]]) -> str:
    """Build a Markdown table for the Additional Features section."""
    lines = [
        "",
        "| Feature | Guide |",
        "|---|---|",
    ]
    for title, url in sorted(entries, key=lambda e: e[0]):
        lines.append(f"| {title} | <{url}> |")
    lines.append("")
    return "\n".join(lines)


def sync(*, check: bool = False, diff: bool = False) -> int:
    """Main sync logic. Returns 0 on success, 1 if out of sync (check mode)."""
    if not SKILL_MD.is_file():
        print(f"ERROR: {SKILL_MD} not found", file=sys.stderr)
        return 1

    skill_text = SKILL_MD.read_text()

    # Fetch and parse docs index
    try:
        llms_txt = fetch_llms_txt()
    except Exception as e:
        print(f"ERROR: Failed to fetch llms.txt: {e}", file=sys.stderr)
        return 1

    all_sdk_entries = extract_sdk_guides(llms_txt)
    body_urls = urls_in_skill_body(skill_text)

    # Filter: only guides not already covered elsewhere in SKILL.md and
    # not matching exclude patterns
    table_entries = []
    for title, url in all_sdk_entries:
        if should_exclude(url):
            continue
        if url in body_urls:
            continue
        table_entries.append((title, url))

    new_table = build_table(table_entries)

    # Check if markers exist
    if TABLE_BEGIN not in skill_text or TABLE_END not in skill_text:
        print(
            f"WARNING: Auto-sync markers not found in SKILL.md.\n"
            f"Add these markers around the Additional Features table:\n"
            f"  {TABLE_BEGIN}\n"
            f"  ... table content ...\n"
            f"  {TABLE_END}",
            file=sys.stderr,
        )
        # Report what the table SHOULD contain
        print("\nSuggested Additional Features table:")
        print(new_table)

        if check:
            return 1
        return 0

    # Extract current table content
    before = skill_text[: skill_text.index(TABLE_BEGIN) + len(TABLE_BEGIN)]
    after = skill_text[skill_text.index(TABLE_END) :]
    current_table = skill_text[len(before) : skill_text.index(TABLE_END)]

    if current_table == new_table:
        print("Additional Features table is up to date. ✓")
        return 0

    if diff:
        print("--- current table ---")
        print(current_table)
        print("--- new table ---")
        print(new_table)
        return 1

    if check:
        print("Additional Features table is out of date.")
        print(f"Run: python scripts/sync_openhands_sdk_skill.py")
        return 1

    # Write updated file
    updated = before + new_table + after
    SKILL_MD.write_text(updated)
    print(f"Updated {SKILL_MD.relative_to(REPO_ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync openhands-sdk skill with OpenHands docs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--check", action="store_true", help="Exit 1 if out of sync.")
    parser.add_argument("--diff", action="store_true", help="Show what would change.")
    args = parser.parse_args()
    return sync(check=args.check, diff=args.diff)


if __name__ == "__main__":
    sys.exit(main())
