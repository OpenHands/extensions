"""Tests for PR review feedback collection."""

import importlib.util
import sys
import types
from pathlib import Path

import yaml


def _load_eval_module():
    """Load evaluate_review.py with Laminar stubbed."""
    lmnr_mod = types.ModuleType("lmnr")

    class _FakeLaminar:
        @staticmethod
        def initialize():
            return None

        @staticmethod
        def get_trace_id():
            return None

        @staticmethod
        def get_laminar_span_context():
            return None

        @staticmethod
        def set_trace_metadata(metadata):
            return None

        @staticmethod
        def set_span_output(output):
            return None

        @staticmethod
        def flush():
            return None

        @staticmethod
        def start_as_current_span(**kwargs):
            import contextlib

            return contextlib.nullcontext()

    class _FakeClient:
        class evaluators:
            @staticmethod
            def score(**kwargs):
                return None

        class tags:
            @staticmethod
            def tag(trace_id, tags):
                return None

    lmnr_mod.Laminar = _FakeLaminar
    lmnr_mod.LaminarClient = _FakeClient

    saved = sys.modules.get("lmnr")
    sys.modules["lmnr"] = lmnr_mod
    try:
        path = (
            Path(__file__).parent.parent
            / "plugins"
            / "pr-review"
            / "scripts"
            / "evaluate_review.py"
        )
        spec = importlib.util.spec_from_file_location("pr_review_evaluate", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if saved is None:
            sys.modules.pop("lmnr", None)
        else:
            sys.modules["lmnr"] = saved


def test_action_collect_feedback_defaults_to_true():
    action_yml = (
        Path(__file__).parent.parent / "plugins" / "pr-review" / "action.yml"
    )
    with open(action_yml) as f:
        action = yaml.safe_load(f)

    collect_feedback = action["inputs"]["collect-feedback"]
    assert collect_feedback["default"] == "true"

    feedback_step = next(
        step
        for step in action["runs"]["steps"]
        if step["name"] == "Post PR review feedback prompt"
    )
    assert "inputs.collect-feedback == 'true'" in feedback_step["if"]
    assert "openhands-pr-review-feedback" in feedback_step["run"]
    assert "React to this comment with 👍 or 👎" in feedback_step["run"]


def test_extract_review_feedback_counts_thumbs_reactions():
    module = _load_eval_module()

    comments = [
        {
            "id": 101,
            "user": {"login": "openhands-agent"},
            "body": "## OpenHands PR review feedback\n<!-- openhands-pr-review-feedback -->",
            "created_at": "2026-05-19T12:00:00Z",
            "reactions": {"+1": 3, "-1": 1, "total_count": 4},
        },
        {
            "id": 102,
            "user": {"login": "openhands-agent"},
            "body": "Regular review comment",
            "reactions": {"+1": 100, "-1": 100},
        },
        {
            "id": 103,
            "user": {"login": "human-dev"},
            "body": "<!-- openhands-pr-review-feedback -->",
            "reactions": {"+1": 5, "-1": 0},
        },
    ]

    assert module.extract_review_feedback(comments) == [
        {
            "comment_id": 101,
            "created_at": "2026-05-19T12:00:00Z",
            "thumbs_up": 3,
            "thumbs_down": 1,
            "total": 4,
        }
    ]


def test_extract_review_feedback_handles_missing_reactions():
    module = _load_eval_module()

    result = module.extract_review_feedback(
        [
            {
                "id": 201,
                "user": {"login": "all-hands-bot"},
                "body": "<!-- openhands-pr-review-feedback -->",
            }
        ]
    )

    assert result == [
        {
            "comment_id": 201,
            "created_at": None,
            "thumbs_up": 0,
            "thumbs_down": 0,
            "total": 0,
        }
    ]


def test_extract_review_feedback_accepts_github_actions_bot():
    module = _load_eval_module()

    result = module.extract_review_feedback(
        [
            {
                "id": 301,
                "user": {"login": "github-actions[bot]"},
                "body": "<!-- openhands-pr-review-feedback -->",
                "reactions": {"+1": 1, "-1": 2},
            }
        ]
    )

    assert result[0]["thumbs_up"] == 1
    assert result[0]["thumbs_down"] == 2
