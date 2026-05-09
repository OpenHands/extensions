"""Tests for the qa-changes evaluation script (evaluate_qa_changes.py)."""

import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

_SCRIPTS_DIR = (
    Path(__file__).parent.parent / "plugins" / "qa-changes" / "scripts"
)


def _load_eval_module():
    """Load evaluate_qa_changes.py, stubbing out lmnr which needs a project key."""
    lmnr_mod = types.ModuleType("lmnr")

    class _FakeLaminar:
        @staticmethod
        def initialize():
            pass

        @staticmethod
        def get_trace_id():
            return None

        @staticmethod
        def get_laminar_span_context():
            return None

        @staticmethod
        def set_trace_metadata(meta):
            pass

        @staticmethod
        def set_span_output(output):
            pass

        @staticmethod
        def flush():
            pass

        @staticmethod
        def start_as_current_span(**kwargs):
            import contextlib
            return contextlib.nullcontext()

    class _FakeClient:
        class evaluators:
            @staticmethod
            def score(**kwargs):
                pass

        class tags:
            @staticmethod
            def tag(trace_id, tags):
                pass

    lmnr_mod.Laminar = _FakeLaminar
    lmnr_mod.LaminarClient = _FakeClient

    saved = sys.modules.get("lmnr")
    sys.modules["lmnr"] = lmnr_mod

    try:
        path = _SCRIPTS_DIR / "evaluate_qa_changes.py"
        spec = importlib.util.spec_from_file_location("evaluate_qa_changes", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if saved is None:
            sys.modules.pop("lmnr", None)
        else:
            sys.modules["lmnr"] = saved


@pytest.fixture(scope="module")
def eval_mod():
    return _load_eval_module()


# ===================================================================
# extract_qa_report
# ===================================================================


class TestExtractQaReport:
    def test_extracts_agent_comments(self, eval_mod):
        comments = [
            {"user": {"login": "openhands-agent"}, "id": 1, "body": "QA report", "created_at": "2024-01-01"},
            {"user": {"login": "human-dev"}, "id": 2, "body": "looks good", "created_at": "2024-01-02"},
            {"user": {"login": "all-hands-bot"}, "id": 3, "body": "another report", "created_at": "2024-01-03"},
        ]
        result = eval_mod.extract_qa_report(comments)
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["type"] == "qa_report"
        assert result[1]["id"] == 3

    def test_empty_comments(self, eval_mod):
        assert eval_mod.extract_qa_report([]) == []

    def test_no_agent_comments(self, eval_mod):
        comments = [
            {"user": {"login": "human"}, "id": 1, "body": "test", "created_at": "2024-01-01"},
        ]
        assert eval_mod.extract_qa_report(comments) == []


# ===================================================================
# extract_human_responses
# ===================================================================


class TestExtractHumanResponses:
    def test_extracts_human_comments(self, eval_mod):
        comments = [
            {"user": {"login": "openhands-agent"}, "id": 1, "body": "QA report", "created_at": "2024-01-01"},
            {"user": {"login": "dev-alice"}, "id": 2, "body": "thanks", "created_at": "2024-01-02"},
            {"user": {"login": "dev-bob"}, "id": 3, "body": "agreed", "created_at": "2024-01-03"},
        ]
        result = eval_mod.extract_human_responses(comments)
        assert len(result) == 2
        assert result[0]["user"] == "dev-alice"
        assert result[1]["user"] == "dev-bob"

    def test_empty_comments(self, eval_mod):
        assert eval_mod.extract_human_responses([]) == []

    def test_all_agent_comments(self, eval_mod):
        comments = [
            {"user": {"login": "openhands-agent"}, "id": 1, "body": "report", "created_at": "2024-01-01"},
        ]
        assert eval_mod.extract_human_responses(comments) == []

    def test_custom_agent_users(self, eval_mod):
        comments = [
            {"user": {"login": "my-bot"}, "id": 1, "body": "report", "created_at": "2024-01-01"},
            {"user": {"login": "human"}, "id": 2, "body": "ok", "created_at": "2024-01-02"},
        ]
        result = eval_mod.extract_human_responses(comments, agent_users={"my-bot"})
        assert len(result) == 1
        assert result[0]["user"] == "human"


# ===================================================================
# truncate_text
# ===================================================================


class TestTruncateText:
    def test_short_text_unchanged(self, eval_mod):
        assert eval_mod.truncate_text("hello") == "hello"

    def test_exact_limit(self, eval_mod):
        text = "x" * 100
        assert eval_mod.truncate_text(text, max_chars=100) == text

    def test_over_limit(self, eval_mod):
        text = "x" * 200
        result = eval_mod.truncate_text(text, max_chars=100)
        assert result.startswith("x" * 100)
        assert "truncated" in result
        assert "200" in result

    def test_default_limit_is_50k(self, eval_mod):
        text = "x" * 50000
        assert eval_mod.truncate_text(text) == text
        text_over = "x" * 50001
        assert "truncated" in eval_mod.truncate_text(text_over)


# ===================================================================
# calculate_engagement_score
# ===================================================================


class TestCalculateEngagementScore:
    def test_no_comments_no_merge(self, eval_mod):
        score = eval_mod.calculate_engagement_score([], [], False)
        assert score == 0.0

    def test_qa_report_posted_no_responses(self, eval_mod):
        qa = [{"type": "qa_report", "body": "report"}]
        score = eval_mod.calculate_engagement_score(qa, [], False)
        assert score == pytest.approx(0.3)

    def test_qa_report_with_responses(self, eval_mod):
        qa = [{"type": "qa_report", "body": "report"}]
        human = [{"type": "issue_comment", "body": "thanks"}]
        score = eval_mod.calculate_engagement_score(qa, human, False)
        # 0.3 (report) + 1.0 * 0.2 (response ratio capped at 1.0)
        assert score == pytest.approx(0.5)

    def test_merged_bonus(self, eval_mod):
        score = eval_mod.calculate_engagement_score([], [], True)
        assert score == pytest.approx(0.3)

    def test_full_engagement(self, eval_mod):
        qa = [{"type": "qa_report", "body": "report"}]
        human = [{"type": "issue_comment", "body": "thanks"}]
        score = eval_mod.calculate_engagement_score(qa, human, True)
        # 0.3 (report) + 0.2 (response) + 0.3 (merged)
        assert score == pytest.approx(0.8)

    def test_many_responses_capped(self, eval_mod):
        qa = [{"type": "qa_report", "body": "report"}]
        human = [{"body": f"msg {i}"} for i in range(10)]
        score = eval_mod.calculate_engagement_score(qa, human, False)
        # ratio capped at 1.0 → 0.3 + 0.2
        assert score == pytest.approx(0.5)

    def test_multiple_qa_comments_with_fewer_responses(self, eval_mod):
        qa = [{"body": f"qa {i}"} for i in range(4)]
        human = [{"body": "reply"}]
        score = eval_mod.calculate_engagement_score(qa, human, False)
        # 0.3 + (1/4) * 0.2 = 0.35
        assert score == pytest.approx(0.35)


# ===================================================================
# load_trace_info
# ===================================================================


class TestLoadTraceInfo:
    def test_file_not_found_returns_empty(self, eval_mod, tmp_path):
        result = eval_mod.load_trace_info(str(tmp_path / "nonexistent.json"))
        assert result == {}

    def test_loads_valid_trace_file(self, eval_mod, tmp_path):
        trace_data = {
            "trace_id": "abc-123",
            "span_context": {"trace_id": "abc", "span_id": "def"},
            "pr_number": "42",
            "repo_name": "org/repo",
            "commit_id": "deadbeef",
            "model": "claude-sonnet",
        }
        trace_file = tmp_path / "trace.json"
        trace_file.write_text(json.dumps(trace_data))

        result = eval_mod.load_trace_info(str(trace_file))
        assert result["trace_id"] == "abc-123"
        assert result["pr_number"] == "42"
        assert result["span_context"]["trace_id"] == "abc"

    def test_trace_without_span_context(self, eval_mod, tmp_path):
        trace_data = {"trace_id": "abc-123"}
        trace_file = tmp_path / "trace.json"
        trace_file.write_text(json.dumps(trace_data))

        result = eval_mod.load_trace_info(str(trace_file))
        assert result["trace_id"] == "abc-123"
        assert result.get("span_context") is None
