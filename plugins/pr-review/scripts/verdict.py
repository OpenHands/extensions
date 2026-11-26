"""Decide the review's GitHub event from what the review posted.

Pure: takes already-fetched bodies and returns the event. The model posts its findings as a COMMENT
review; this decides whether the run also approves.
"""

from __future__ import annotations

CRITICAL_MARKER = "🔴"


def review_event(bodies: list[str | None]) -> str:
    """`APPROVE` when no posted body (review body or kept inline comment) carries a Critical finding,
    else `COMMENT`. Never `REQUEST_CHANGES`."""
    if any(CRITICAL_MARKER in (body or "") for body in bodies):
        return "COMMENT"
    return "APPROVE"
