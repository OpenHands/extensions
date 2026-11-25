import importlib.util
from pathlib import Path


def _dedupe():
    path = Path(__file__).parent.parent / "plugins" / "pr-review" / "scripts" / "dedupe.py"
    spec = importlib.util.spec_from_file_location("pr_review_dedupe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.repeated_comment_ids


def _c(id, path, line, body):
    return {"id": id, "path": path, "line": line, "body": body}


PRIOR = [_c(1, "a.py", 40, "🔴 Critical: the drop uses `startswith`. Compare the parsed name.")]


def test_a_new_comment_near_an_earlier_thread_line_is_dropped():
    assert _dedupe()(PRIOR, [_c(10, "a.py", 42, "Different words entirely.")]) == [10]


def test_a_new_comment_with_the_same_first_sentence_elsewhere_in_the_file_is_dropped():
    new = [_c(10, "a.py", 90, "🟠 Important: The drop uses startswith! More detail here.")]
    assert _dedupe()(PRIOR, new) == [10]


def test_an_outdated_thread_matches_on_its_original_line():
    prior = [{"id": 1, "path": "a.py", "line": None, "original_line": 40, "body": "x."}]
    assert _dedupe()(prior, [_c(10, "a.py", 41, "y.")]) == [10]


def test_a_new_finding_far_away_or_in_another_file_is_kept():
    new = [_c(10, "a.py", 60, "A new problem."), _c(11, "b.py", 40, "The drop uses startswith.")]
    assert _dedupe()(PRIOR, new) == []


def test_an_exact_duplicate_within_one_review_is_dropped_but_a_nearby_distinct_one_is_kept():
    new = [_c(10, "c.py", 5, "Missing check."), _c(11, "c.py", 6, "Another issue."),
           _c(12, "c.py", 30, "Missing check.")]
    assert _dedupe()([], new) == [12]
