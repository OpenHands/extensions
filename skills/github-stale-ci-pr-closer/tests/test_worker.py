import sys
import unittest
from os import environ
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parents[2] / "github" / "scripts"))
import worker

DAY = 24 * 60 * 60


class TestStateKey(unittest.TestCase):
    def test_is_scoped_to_the_automation(self):
        payload = '{"automation_id":"automation-123"}'
        with patch.dict(environ, {"AUTOMATION_EVENT_PAYLOAD": payload}):
            self.assertEqual(
                worker._state_key("OpenHands/extensions"),
                "github-stale-ci-pr-closer:automation-123:OpenHands__extensions",
            )


class TestReconcile(unittest.TestCase):
    def setUp(self):
        self.closer = object.__new__(worker.StaleCIPullRequestCloser)
        self.closer.required_checks = Mock(return_value=[{"context": "test"}])
        self.closer.required_ci_state = Mock(return_value="failing")
        self.closer.post_comment = Mock(return_value={"id": 99})
        self.closer.comments = Mock(return_value=[])
        self.closer.gh = Mock(return_value={})
        self.pr = {
            "number": 7,
            "draft": False,
            "head": {"sha": "abc"},
            "base": {"ref": "main"},
            "user": {"login": "author"},
        }
        self.records = {}

    def reconcile(self, now):
        return self.closer.reconcile(self.pr, self.records, now)

    def test_warns_once_after_seven_days(self):
        self.assertEqual(self.reconcile(0), "observing")
        self.assertEqual(self.reconcile(7 * DAY), "warned")
        self.assertEqual(self.reconcile(8 * DAY), "waiting")
        self.closer.post_comment.assert_called_once()
        self.assertIn(worker.WARNING_MARKER, self.closer.post_comment.call_args.args[1])

    def test_recovers_a_persisted_warning_marker_without_duplication(self):
        self.reconcile(0)
        self.closer.comments.return_value = [
            {
                "id": 41,
                "user": {"login": "all-hands-bot"},
                "created_at": "1970-01-08T00:00:00Z",
                "body": "<!-- openhands-stale-ci-warning head=abc -->",
            }
        ]
        self.assertEqual(self.reconcile(8 * DAY), "waiting")
        self.closer.post_comment.assert_not_called()
        self.assertEqual(self.records["7"]["warning"]["comment_id"], 41)

    def test_closes_after_seven_more_days_without_follow_up(self):
        self.reconcile(0)
        self.reconcile(7 * DAY)
        self.assertEqual(self.reconcile(14 * DAY), "closed")
        self.assertTrue(
            any(
                call.args[:2] == ("PATCH", "/pulls/7")
                for call in self.closer.gh.call_args_list
            )
        )
        self.assertNotIn("7", self.records)

    def test_passing_or_pending_ci_cancels_the_lifecycle(self):
        self.reconcile(0)
        for state in ("passing", "pending"):
            self.closer.required_ci_state.return_value = state
            self.assertEqual(self.reconcile(DAY), state)
            self.assertNotIn("7", self.records)
            self.closer.required_ci_state.return_value = "failing"
            self.reconcile(DAY)

    def test_author_comment_starts_a_fresh_window(self):
        self.reconcile(0)
        self.reconcile(7 * DAY)
        self.closer.comments.return_value = [
            {
                "user": {"login": "author"},
                "created_at": "1970-01-09T00:00:00Z",
                "body": "working",
            }
        ]
        self.assertEqual(self.reconcile(14 * DAY), "followed-up")
        self.assertEqual(self.records["7"]["first_failed_at"], 14 * DAY)
        self.assertNotIn("warning", self.records["7"])

    def test_new_head_starts_a_fresh_window(self):
        self.reconcile(0)
        self.reconcile(7 * DAY)
        self.pr["head"]["sha"] = "def"
        self.assertEqual(self.reconcile(14 * DAY), "observing")
        self.assertEqual(
            self.records["7"], {"head_sha": "def", "first_failed_at": 14 * DAY}
        )

    def test_draft_cancels_the_lifecycle(self):
        self.reconcile(0)
        self.pr["draft"] = True
        self.assertEqual(self.reconcile(DAY), "draft")
        self.assertNotIn("7", self.records)


class TestRequiredCI(unittest.TestCase):
    def setUp(self):
        self.closer = object.__new__(worker.StaleCIPullRequestCloser)
        self.closer.gh_pages = Mock(return_value=[])

    def state(self, runs, required):
        self.closer.gh = Mock(return_value={"check_runs": runs})
        return self.closer.required_ci_state("sha", required)

    def test_optional_failures_are_ignored(self):
        runs = [
            {
                "id": 2,
                "name": "required",
                "app": {"id": 1},
                "status": "completed",
                "conclusion": "success",
            },
            {
                "id": 1,
                "name": "optional",
                "app": {"id": 1},
                "status": "completed",
                "conclusion": "failure",
            },
        ]
        self.assertEqual(
            self.state(runs, [{"context": "required", "integration_id": 1}]), "passing"
        )

    def test_pending_required_check_wins_over_failure(self):
        runs = [
            {
                "id": 2,
                "name": "a",
                "app": {"id": 1},
                "status": "completed",
                "conclusion": "failure",
            },
            {
                "id": 1,
                "name": "b",
                "app": {"id": 1},
                "status": "in_progress",
                "conclusion": None,
            },
        ]
        required = [
            {"context": "a", "integration_id": 1},
            {"context": "b", "integration_id": 1},
        ]
        self.assertEqual(self.state(runs, required), "pending")


class TestCandidateSearch(unittest.TestCase):
    def setUp(self):
        self.closer = object.__new__(worker.StaleCIPullRequestCloser)
        self.closer.repository = "OpenHands/OpenHands"

    def test_searches_only_inactive_failing_pull_requests(self):
        self.closer.api = Mock(
            return_value={
                "incomplete_results": False,
                "items": [{"number": 2}, {"number": 3}],
            }
        )
        self.assertEqual(self.closer.stale_failure_numbers(14 * DAY), {2, 3})
        params = self.closer.api.call_args.kwargs["params"]
        self.assertIn("is:pr is:open draft:false status:failure", params["q"])
        self.assertIn("updated:<1970-01-08", params["q"])

    def test_rejects_incomplete_search_results(self):
        self.closer.api = Mock(return_value={"incomplete_results": True, "items": []})
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            self.closer.stale_failure_numbers(14 * DAY)


if __name__ == "__main__":
    unittest.main()
