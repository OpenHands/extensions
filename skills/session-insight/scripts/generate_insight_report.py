#!/usr/bin/env python3
"""Build a local HTML usage report from OpenHands JSON/JSONL exports."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SENSITIVE_NAME = re.compile(
    r"(?:^|[-_.])(auth|cookie|credential|secret|token|api[-_]?key|env)(?:[-_.]|$)",
    re.IGNORECASE,
)
FAILURE_WORDS = re.compile(
    r"\b(error|failed|failure|exception|timeout|timed out|denied|invalid)\b",
    re.IGNORECASE,
)
ACTION_KEYS = ("tool_name", "tool", "action", "command", "event_type", "type")
ERROR_KEYS = ("error", "error_detail", "exception", "failure", "status_detail")
CONTAINER_KEYS = ("events", "messages", "actions", "history", "items", "results")


@dataclass
class Analysis:
    files: list[str] = field(default_factory=list)
    malformed: list[str] = field(default_factory=list)
    records: int = 0
    actions: Counter[str] = field(default_factory=Counter)
    failures: Counter[str] = field(default_factory=Counter)


def safe_label(value: Any, fallback: str = "unknown") -> str:
    if not isinstance(value, (str, int, float, bool)):
        return fallback
    label = " ".join(str(value).split())[:120]
    if not label or SENSITIVE_NAME.search(label):
        return fallback
    return label


def iter_records(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from iter_records(item)
        return
    if not isinstance(value, dict):
        return

    nested = False
    for key in CONTAINER_KEYS:
        child = value.get(key)
        if isinstance(child, (dict, list)):
            nested = True
            yield from iter_records(child)
    if not nested or any(key in value for key in ACTION_KEYS + ERROR_KEYS):
        yield value


def read_values(path: Path) -> list[Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return [json.loads(text)]


def classify_failure(record: dict[str, Any]) -> str | None:
    for key in ERROR_KEYS:
        value = record.get(key)
        if value in (None, "", False, [], {}):
            continue
        if isinstance(value, dict):
            return safe_label(value.get("kind") or value.get("code"), key)
        text = safe_label(value, key)
        match = FAILURE_WORDS.search(text)
        return match.group(1).lower() if match else key
    status = safe_label(record.get("status"), "").lower()
    if status in {"error", "failed", "failure", "timed_out", "timeout"}:
        return status.replace("_", " ")
    return None


def action_name(record: dict[str, Any]) -> str | None:
    for key in ACTION_KEYS:
        if key not in record:
            continue
        if key == "command":
            # Command text can contain credentials or other sensitive values.
            return "command"
        value = record[key]
        if isinstance(value, dict):
            value = value.get("name") or value.get("type")
        label = safe_label(value, "")
        if label:
            return label
    return None


def collect_files(inputs: list[Path]) -> list[Path]:
    found: set[Path] = set()
    for item in inputs:
        expanded = item.expanduser()
        candidates = (
            [expanded]
            if expanded.is_file()
            else expanded.rglob("*")
            if expanded.is_dir()
            else []
        )
        for candidate in candidates:
            if not candidate.is_file() or candidate.suffix.lower() not in {
                ".json",
                ".jsonl",
            }:
                continue
            if SENSITIVE_NAME.search(candidate.name):
                continue
            found.add(candidate.resolve())
    return sorted(found)


def analyze(paths: list[Path]) -> Analysis:
    result = Analysis()
    for path in paths:
        try:
            values = read_values(path)
        except (OSError, UnicodeError, json.JSONDecodeError):
            result.malformed.append(str(path))
            continue
        file_records = 0
        for value in values:
            for record in iter_records(value):
                file_records += 1
                result.records += 1
                action = action_name(record)
                if action:
                    result.actions[action] += 1
                failure = classify_failure(record)
                if failure:
                    result.failures[failure] += 1
        if file_records:
            result.files.append(str(path))
    return result


def table(counter: Counter[str], empty: str) -> str:
    if not counter:
        return f"<p>{html.escape(empty)}</p>"
    rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{count}</td></tr>"
        for name, count in counter.most_common(12)
    )
    return f"<table><thead><tr><th>Observed category</th><th>Count</th></tr></thead><tbody>{rows}</tbody></table>"


def render(result: Analysis) -> str:
    sources = "".join(f"<li>{html.escape(path)}</li>" for path in result.files)
    malformed = "".join(f"<li>{html.escape(path)}</li>" for path in result.malformed)
    repetitive = Counter(
        {name: count for name, count in result.actions.items() if count >= 3}
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>OpenHands session insight</title><style>
body{{font:16px/1.5 system-ui,sans-serif;max-width:920px;margin:2rem auto;padding:0 1rem;color:#17202a}}
h1,h2{{line-height:1.2}} .metric{{display:inline-block;margin:.25rem 1rem .25rem 0;padding:.6rem 1rem;background:#eef3f8;border-radius:.5rem}}
table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #ccd6df;padding:.5rem;text-align:left}} th{{background:#eef3f8}}
code{{background:#eef3f8;padding:.1rem .25rem}} .note{{border-left:4px solid #607d9b;padding-left:1rem}}
</style></head><body>
<h1>OpenHands session insight</h1>
<p class="note">Local evidence summary. Message bodies and credential values are not rendered.</p>
<div class="metric"><strong>{len(result.files)}</strong> source files</div><div class="metric"><strong>{result.records}</strong> records</div><div class="metric"><strong>{sum(result.failures.values())}</strong> failure signals</div>
<h2>Recurring failures and bottlenecks</h2>{table(result.failures, "No explicit failure signals were found in the supported records.")}
<h2>Repetitive actions</h2>{table(repetitive, "No action or tool category occurred at least three times.")}
<h2>Evidence sources</h2><ul>{sources}</ul>
<h2>Limitations</h2><p>Counts reflect recognized JSON fields only. Unknown schemas and message prose are not inferred. Validate a finding against its source before changing the environment.</p>
{f"<p>Unreadable or malformed files:</p><ul>{malformed}</ul>" if malformed else ""}
<h2>Next step</h2><p>Use these measured patterns to propose up to three focused improvements. Implement one only after explicit user confirmation.</p>
</body></html>"""


def default_inputs() -> list[Path]:
    cwd = Path.cwd()
    home = Path.home()
    return [
        cwd / ".openhands" / "conversations",
        cwd / ".openhands" / "sessions",
        home / ".openhands" / "conversations",
        home / ".openhands" / "sessions",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", type=Path, default=[])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".openhands/usage-data/insight-report.html"),
    )
    args = parser.parse_args()
    paths = collect_files(args.input or default_inputs())
    result = analyze(paths)
    if not result.files or result.records == 0:
        print(
            "No supported OpenHands session records were found. "
            "Pass one or more JSON/JSONL exports with --input.",
            file=sys.stderr,
        )
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(result), encoding="utf-8")
    print(
        json.dumps(
            {
                "output": str(args.output),
                "files": len(result.files),
                "records": result.records,
                "failure_signals": sum(result.failures.values()),
                "malformed_files": len(result.malformed),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
