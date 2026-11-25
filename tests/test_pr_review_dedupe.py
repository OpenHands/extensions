import importlib.util
from pathlib import Path


def _load():
    path = Path(__file__).parent.parent / "plugins" / "pr-review" / "scripts" / "dedupe.py"
    spec = importlib.util.spec_from_file_location("pr_review_dedupe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.repeated_comment_ids


repeated_comment_ids = _load()


def _c(id, path, line, body):
    return {"id": id, "path": path, "line": line, "body": body}


PRIOR = [_c(1, "a.py", 40, "🔴 Critical: the drop uses `startswith`. Compare the parsed name.")]


def test_a_new_comment_within_three_lines_of_an_earlier_thread_is_dropped_and_four_lines_away_is_kept():
    new = [_c(10, "a.py", 43, "Different words."), _c(11, "a.py", 44, "Other words.")]
    assert repeated_comment_ids(PRIOR, new) == [10]


def test_a_new_comment_with_the_same_first_sentence_elsewhere_in_the_file_is_dropped():
    new = [_c(10, "a.py", 90, "🟠 Important: The drop uses startswith! More detail here.")]
    assert repeated_comment_ids(PRIOR, new) == [10]


def test_an_outdated_thread_matches_on_its_original_line():
    prior = [{"id": 1, "path": "a.py", "line": None, "original_line": 40, "body": "x."}]
    assert repeated_comment_ids(prior, [_c(10, "a.py", 41, "y.")]) == [10]


def test_comments_without_lines_or_text_are_kept_unless_the_text_matches():
    prior = [_c(1, "a.py", None, ""), _c(2, "a.py", None, "Nit:")]
    new = [_c(10, "a.py", None, ""), _c(11, "a.py", None, "A new point.")]
    assert repeated_comment_ids(prior, new) == []


def test_a_new_finding_far_away_or_in_another_file_is_kept():
    new = [_c(10, "a.py", 60, "A new problem."), _c(11, "b.py", 40, "The drop uses startswith.")]
    assert repeated_comment_ids(PRIOR, new) == []


def test_a_duplicate_within_one_review_is_dropped_on_any_file_but_a_nearby_distinct_one_is_kept():
    new = [_c(10, "c.py", 5, "Missing check."), _c(11, "c.py", 6, "Another issue."),
           _c(12, "d.yml", 30, "Missing CHECK!")]
    assert repeated_comment_ids([], new) == [12]
