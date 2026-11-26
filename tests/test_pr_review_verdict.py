import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).parent.parent / "plugins" / "pr-review" / "scripts" / "verdict.py"
    spec = importlib.util.spec_from_file_location("pr_review_verdict", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.review_event


review_event = _load()


def test_no_findings_approves():
    assert review_event(["Taste: acceptable. No issues."]) == "APPROVE"


def test_only_non_critical_findings_approve():
    assert review_event(["Summary", "🟠 Important: x.", "🟡 Suggestion: y.", None]) == "APPROVE"


def test_a_critical_inline_comment_comments_without_approving():
    assert review_event(["Summary", "🟠 Important: x.", "🔴 Critical: data loss."]) == "COMMENT"


def test_a_critical_in_the_review_body_comments_without_approving():
    assert review_event(["🔴 Critical: the drop matches PR 12."]) == "COMMENT"


def test_a_critical_listed_in_the_review_body_comments_without_approving():
    assert review_event(["Findings:\n- **🔴 Critical:** the drop matches PR 12."]) == "COMMENT"


def test_a_critical_mentioned_mid_sentence_still_approves():
    assert review_event(["Good. The earlier 🔴 Critical no longer applies on this head."]) == "APPROVE"
