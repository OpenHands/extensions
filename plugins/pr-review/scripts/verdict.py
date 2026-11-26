"""Decide the review's GitHub event from what the review posted.

Pure: takes already-fetched bodies and returns the event. The model posts its findings as a COMMENT
review; this decides whether the run also approves.
"""

from __future__ import annotations

import re

CRITICAL_MARKER = "🔴"
# A finding opens with its priority label, after any list bullet, quote or bold markup; a 🔴 mentioned
# mid-sentence ("the earlier 🔴 Critical no longer applies") is not a finding.
_FINDING_LINE = re.compile(r"^[\s>*_\-+\d.]*" + CRITICAL_MARKER)


def review_event(bodies: list[str | None]) -> str:
    """`APPROVE` when no line of a posted body (review body or kept inline comment) opens a 🔴 Critical
    finding, else `COMMENT`. Never `REQUEST_CHANGES`."""
    for body in bodies:
        if any(_FINDING_LINE.match(line) for line in (body or "").splitlines()):
            return "COMMENT"
    return "APPROVE"
