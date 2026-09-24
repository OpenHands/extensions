import sys
import unittest
from os import environ
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError

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

    def test_old_warning_is_not_reused_after_ci_recovers(self):
        self.reconcile(0)
        self.reconcile(7 * DAY)
        self.closer.required_ci_state.return_value = "passing"
        self.reconcile(8 * DAY)
        self.closer.required_ci_state.return_value = "failing"
        self.closer.comments.return_value = [
            {
                "id": 41,
                "user": {"login": "all-hands-bot"},
                "created_at": "1970-01-08T00:00:00Z",
                "body": "<!-- openhands-stale-ci-warning head=abc -->",
            }
        ]
        self.assertEqual(self.reconcile(8 * DAY), "observing")
        self.assertEqual(self.reconcile(15 * DAY), "warned")
        self.assertEqual(self.closer.post_comment.call_count, 2)
        self.assertIn("warning", self.records["7"])

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

    def test_old_check_failure_warns_despite_recent_pr_activity(self):
        self.pr["updated_at"] = "1970-01-08T00:00:00Z"
        self.pr["_ci_state"] = "failing"
        self.pr["_failed_at"] = 0
        self.assertEqual(self.reconcile(7 * DAY), "warned")

    def test_backfills_legacy_observation_time_from_check_failure(self):
        self.records["7"] = {"head_sha": "abc", "first_failed_at": 6 * DAY}
        self.pr["_ci_state"] = "failing"
        self.pr["_failed_at"] = 0
        self.assertEqual(self.reconcile(7 * DAY), "warned")

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

    def test_newest_required_failure_sets_the_age(self):
        contexts = [
            {
                "__typename": "CheckRun",
                "databaseId": 2,
                "name": "a",
                "status": "COMPLETED",
                "conclusion": "FAILURE",
                "completedAt": "1970-01-01T00:00:00Z",
                "checkSuite": {"app": {"databaseId": 1}},
            },
            {
                "__typename": "CheckRun",
                "databaseId": 3,
                "name": "b",
                "status": "COMPLETED",
                "conclusion": "FAILURE",
                "completedAt": "1970-01-03T00:00:00Z",
                "checkSuite": {"app": {"databaseId": 1}},
            },
        ]
        state, failed_at = self.closer._graphql_ci_result(
            contexts,
            [
                {"context": "a", "integration_id": 1},
                {"context": "b", "integration_id": 1},
            ],
        )
        self.assertEqual(state, "failing")
        self.assertEqual(failed_at, 2 * DAY)


class TestPullRequestPagination(unittest.TestCase):
    def setUp(self):
        self.closer = object.__new__(worker.StaleCIPullRequestCloser)
        self.closer.repository = "OpenHands/OpenHands"

    @staticmethod
    def page(number, has_next, cursor):
        return {
            "data": {
                "repository": {
                    "pullRequests": {
                        "pageInfo": {
                            "hasNextPage": has_next,
                            "endCursor": cursor,
                        },
                        "nodes": [
                            {
                                "number": number,
                                "isDraft": False,
                                "baseRefName": "main",
                                "headRefOid": f"sha-{number}",
                                "author": {"login": "author"},
                                "commits": {
                                    "nodes": [
                                        {
                                            "commit": {
                                                "statusCheckRollup": {
                                                    "contexts": {
                                                        "totalCount": 0,
                                                        "nodes": [],
                                                    }
                                                }
                                            }
                                        }
                                    ]
                                },
                            }
                        ],
                    }
                }
            }
        }

    def test_paginates_every_open_pull_request(self):
        self.closer.required_checks = Mock(return_value=[])
        self.closer.api = Mock(
            side_effect=[self.page(2, True, "next"), self.page(3, False, None)]
        )
        self.assertEqual(
            [pr["number"] for pr in self.closer.open_pull_requests()], [2, 3]
        )
        second_variables = self.closer.api.call_args_list[1].kwargs["body"]["variables"]
        self.assertEqual(second_variables["cursor"], "next")

    def test_falls_back_to_rest_when_check_contexts_are_paginated(self):
        page = self.page(2, False, None)
        contexts = page["data"]["repository"]["pullRequests"]["nodes"][0]["commits"][
            "nodes"
        ][0]["commit"]["statusCheckRollup"]["contexts"]
        contexts["totalCount"] = 101
        self.closer.required_checks = Mock(return_value=[{"context": "test"}])
        self.closer.required_ci_result = Mock(return_value=("failing", 0))
        self.closer.api = Mock(return_value=page)

        pull_request = self.closer.open_pull_requests()[0]

        self.assertEqual(pull_request["_ci_state"], "failing")
        self.assertEqual(pull_request["_failed_at"], 0)
        self.closer.required_ci_result.assert_called_once_with(
            "sha-2", [{"context": "test"}]
        )

    @patch("worker.time.sleep")
    def test_retries_a_transient_graphql_page_failure(self, sleep):
        self.closer.required_checks = Mock(return_value=[])
        self.closer.api = Mock(
            side_effect=[
                HTTPError(
                    "https://api.github.com/graphql", 502, "bad gateway", {}, None
                ),
                self.page(2, False, None),
            ]
        )

        self.assertEqual(self.closer.open_pull_requests()[0]["number"], 2)
        sleep.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
