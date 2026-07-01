"""Tests for PR review feedback collection."""

import importlib.util
import sys
import types
from pathlib import Path

import yaml


_ROOT = Path(__file__).parent.parent
_PR_REVIEW_SCRIPTS = _ROOT / "plugins" / "pr-review" / "scripts"


def _load_prompt_module():
    path = _PR_REVIEW_SCRIPTS / "prompt.py"
    spec = importlib.util.spec_from_file_location("pr_review_prompt_feedback", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module



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
        path = _PR_REVIEW_SCRIPTS / "evaluate_review.py"
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



def _format_prompt(*, collect_feedback: bool, review_run_url: str = "") -> str:
    module = _load_prompt_module()
    return module.format_prompt(
        skill_trigger="/codereview",
        title="Add review feedback footer",
        body="## Summary\nCapture review reactions without extra PR spam.",
        repo_name="OpenHands/extensions",
        base_branch="main",
        head_branch="feature/feedback-footer",
        pr_number="249",
        commit_id="abc123",
        diff="diff --git a/file b/file",
        review_context="",
        require_evidence=False,
        collect_feedback=collect_feedback,
        review_run_url=review_run_url,
        use_sub_agents=False,
    )



def test_action_collect_feedback_defaults_to_true_and_uses_agent_prompt():
    action_yml = _ROOT / "plugins" / "pr-review" / "action.yml"
    with open(action_yml) as f:
        action = yaml.safe_load(f)

    collect_feedback = action["inputs"]["collect-feedback"]
    assert collect_feedback["default"] == "true"

    run_step = next(
        step for step in action["runs"]["steps"] if step["name"] == "Run PR review"
    )
    assert run_step["env"]["COLLECT_FEEDBACK"] == "${{ inputs.collect-feedback }}"
    assert run_step["env"]["REVIEW_RUN_URL"] == (
        "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
    )
    assert all(
        step["name"] != "Post PR review feedback prompt"
        for step in action["runs"]["steps"]
    )



def test_prompt_omits_feedback_footer_by_default():
    prompt = _format_prompt(collect_feedback=False)

    assert "## Review Feedback Footer" not in prompt
    assert "React with 👍 or 👎 to this review" not in prompt
    assert "<!-- openhands-pr-review-feedback -->" not in prompt



def test_prompt_includes_feedback_footer_when_enabled():
    prompt = _format_prompt(
        collect_feedback=True,
        review_run_url="https://github.com/OpenHands/extensions/actions/runs/123",
    )

    assert "## Review Feedback Footer" in prompt
    assert "main review body, not in a separate issue comment" in prompt
    assert "React with 👍 or 👎 to this review" in prompt
    assert "https://github.com/OpenHands/extensions/actions/runs/123" in prompt
    assert "<!-- openhands-pr-review-feedback -->" in prompt



def test_extract_review_feedback_counts_thumbs_reactions_from_reviews():
    module = _load_eval_module()

    reviews = [
        {
            "id": 101,
            "user": {"login": "openhands-agent"},
            "body": "Automated review\n<!-- openhands-pr-review-feedback -->",
            "submitted_at": "2026-05-19T12:00:00Z",
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

    assert module.extract_review_feedback([], reviews) == [
        {
            "comment_id": 101,
            "created_at": "2026-05-19T12:00:00Z",
            "thumbs_up": 3,
            "thumbs_down": 1,
            "total": 4,
        }
    ]



def test_extract_review_feedback_keeps_legacy_issue_comment_support():
    module = _load_eval_module()

    result = module.extract_review_feedback(
        [
            {
                "id": 201,
                "user": {"login": "all-hands-bot"},
                "body": "<!-- openhands-pr-review-feedback -->",
                "created_at": "2026-05-19T12:00:00Z",
                "reactions": {"+1": 2, "-1": 0},
            }
        ]
    )

    assert result == [
        {
            "comment_id": 201,
            "created_at": "2026-05-19T12:00:00Z",
            "thumbs_up": 2,
            "thumbs_down": 0,
            "total": 2,
        }
    ]



def test_extract_review_feedback_handles_missing_reactions():
    module = _load_eval_module()

    result = module.extract_review_feedback(
        [],
        [
            {
                "id": 301,
                "user": {"login": "all-hands-bot"},
                "body": "<!-- openhands-pr-review-feedback -->",
            }
        ],
    )

    assert result == [
        {
            "comment_id": 301,
            "created_at": None,
            "thumbs_up": 0,
            "thumbs_down": 0,
            "total": 0,
        }
    ]



def test_extract_review_feedback_accepts_github_actions_bot():
    module = _load_eval_module()

    result = module.extract_review_feedback(
        [],
        [
            {
                "id": 401,
                "user": {"login": "github-actions[bot]"},
                "body": "<!-- openhands-pr-review-feedback -->",
                "reactions": {"+1": 1, "-1": 2},
            }
        ],
    )

    assert result[0]["thumbs_up"] == 1
    assert result[0]["thumbs_down"] == 2
