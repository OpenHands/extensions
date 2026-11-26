"""Find the inline review comments a review run must not keep: repeats of earlier findings.

Pure: takes already-fetched comments and returns ids. The model is told not to repeat itself; this
removes a repeat when it does anyway.
"""

from __future__ import annotations

import re
from typing import Any

LINE_WINDOW = 3


def _first_sentence(body: str) -> str:
    """The body's first sentence, lowercased, without its priority label, markup or punctuation."""
    text = re.sub(r"[*`_>#]", "", body or "").strip()
    text = re.sub(r"^\W*(critical|important|suggestion|nit)\s*:\s*", "", text, flags=re.I)
    first = re.split(r"(?<=[.!?])\s|\n", text, maxsplit=1)[0]
    return re.sub(r"[^a-z0-9 ]", "", first.lower()).strip()


def _line(comment: dict[str, Any]) -> int | None:
    return comment.get("line") or comment.get("original_line")


def _same_finding(new: dict[str, Any], old: dict[str, Any]) -> bool:
    sentence = _first_sentence(new.get("body", ""))
    return bool(sentence) and sentence == _first_sentence(old.get("body", ""))


def _repeats(new: dict[str, Any], old: dict[str, Any]) -> bool:
    if new.get("path") != old.get("path"):
        return False
    new_line, old_line = _line(new), _line(old)
    if new_line is not None and old_line is not None and abs(new_line - old_line) <= LINE_WINDOW:
        return True
    return _same_finding(new, old)


def repeated_comment_ids(
    prior: list[dict[str, Any]], new: list[dict[str, Any]]
) -> list[int]:
    """Ids of `new` comments that repeat a `prior` thread's opening comment, or an earlier `new` comment.

    `prior`: the opening comment of every review thread on the PR before this run.
    `new`: the top-level inline comments this run posted, oldest first.
    Each comment carries `id`, `path`, `line` (or `original_line`) and `body`. A comment repeats a prior
    one on the same path when its line is within LINE_WINDOW lines or its first sentence matches; it
    repeats an earlier comment of this run, on any path, when the first sentence matches.
    """
    drop: list[int] = []
    kept: list[dict[str, Any]] = []
    for comment in new:
        if any(_repeats(comment, old) for old in prior) or any(
            _same_finding(comment, old) for old in kept
        ):
            drop.append(comment["id"])
        else:
            kept.append(comment)
    return drop
