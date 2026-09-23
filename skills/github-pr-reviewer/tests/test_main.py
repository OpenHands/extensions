"""Unit tests for github-pr-reviewer main.py.

Run from the skill root:
    python -m pytest tests/
or with the standard library runner:
    python -m unittest discover tests

The focus is the logic that owns files and state: preparing a checkout from an
untrusted archive, removing it again, and keeping one repository's state apart
from another's.
"""

import contextlib
import io
import json
import os
import sys
import tarfile
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

# Allow importing main.py from the sibling scripts/ directory.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import main  # noqa: E402


# ── Helpers ────────────────────────────────────────────────────────────────────

ARCHIVE_ROOT = "owner-repo-abc123"


def _tarball(members) -> bytes:
    """Build a .tar.gz from (name, kind, payload) triples.

    kind is "file", "dir", or "symlink"; payload is the file body or, for a
    symlink, its target.
    """
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, kind, payload in members:
            info = tarfile.TarInfo(name)
            if kind == "dir":
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = payload
                tar.addfile(info)
            else:
                data = payload.encode()
                info.size = len(data)
                info.mode = 0o644
                tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _CheckoutTestCase(unittest.TestCase):
    """Base case that points WORKSPACE_BASE at a scratch directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self._tmp.name)
        self._env = patch.dict(os.environ, {"WORKSPACE_BASE": str(self.workspace)})
        self._env.start()

    def tearDown(self):
        self._env.stop()
        self._tmp.cleanup()


# ── Checkout paths ─────────────────────────────────────────────────────────────


class TestCheckoutPaths(_CheckoutTestCase):
    def test_slug_replaces_the_separator(self):
        self.assertEqual(main._repo_slug("owner/repo"), "owner__repo")

    def test_checkout_path_is_per_repo_and_per_commit(self):
        a = main._checkout_path("owner/repo", 7, "0123456789abcdef")
        b = main._checkout_path("other/repo", 7, "0123456789abcdef")
        c = main._checkout_path("owner/repo", 7, "fedcba9876543210")
        self.assertNotEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertEqual(a.name, "pr-7-0123456789ab")
        self.assertTrue(a.is_relative_to(main._checkouts_root()))


# ── Preparing a checkout from an archive ───────────────────────────────────────


class TestPrepareRepository(_CheckoutTestCase):
    def _prepare(self, members):
        payload = _tarball(members)
        with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
            return main._prepare_repository("token", "owner/repo", 7, "0123456789abcdef")

    def test_extracts_files_under_the_checkout(self):
        checkout = self._prepare([
            (f"{ARCHIVE_ROOT}/README.md", "file", "hello"),
            (f"{ARCHIVE_ROOT}/src", "dir", None),
            (f"{ARCHIVE_ROOT}/src/app.py", "file", "print(1)\n"),
        ])
        self.assertEqual((checkout / "README.md").read_text(), "hello")
        self.assertEqual((checkout / "src" / "app.py").read_text(), "print(1)\n")
        self.assertTrue(checkout.is_relative_to(main._checkouts_root()))

    def test_symlinks_are_skipped_not_materialised(self):
        checkout = self._prepare([
            (f"{ARCHIVE_ROOT}/real.txt", "file", "data"),
            (f"{ARCHIVE_ROOT}/escape", "symlink", "../../../../etc/passwd"),
        ])
        self.assertTrue((checkout / "real.txt").is_file())
        self.assertFalse((checkout / "escape").exists())

    def test_path_traversal_is_rejected_and_cleaned_up(self):
        with self.assertRaises(RuntimeError):
            self._prepare([
                (f"{ARCHIVE_ROOT}/ok.txt", "file", "fine"),
                (f"{ARCHIVE_ROOT}/../escape.txt", "file", "bad"),
            ])
        # The partially written checkout must not survive a rejected archive.
        self.assertFalse(main._checkout_path("owner/repo", 7, "0123456789abcdef").exists())
        self.assertFalse((self.workspace / "escape.txt").exists())

    def test_multiple_roots_are_rejected(self):
        with self.assertRaises(RuntimeError):
            self._prepare([
                (f"{ARCHIVE_ROOT}/ok.txt", "file", "fine"),
                ("another-root/ok.txt", "file", "bad"),
            ])


# ── Releasing a checkout ───────────────────────────────────────────────────────


class TestReleaseCheckout(_CheckoutTestCase):
    def _record(self, path: Path, conversation_id="conv-1") -> dict:
        path.mkdir(parents=True, exist_ok=True)
        (path / "file.txt").write_text("x")
        return {"conversation_id": conversation_id, "workspace_dir": str(path)}

    def test_nothing_to_do_without_a_workspace_dir(self):
        self.assertTrue(main._release_checkout({"conversation_id": "c"}, "http://s", "k"))

    def test_removes_the_checkout_once_the_conversation_is_terminal(self):
        path = main._checkout_path("owner/repo", 1, "0123456789abcdef")
        rec = self._record(path)
        with patch.object(main, "conversation_status", return_value="finished"):
            self.assertTrue(main._release_checkout(rec, "http://s", "k"))
        self.assertFalse(path.exists())
        self.assertNotIn("workspace_dir", rec)

    def test_keeps_the_checkout_while_the_conversation_runs(self):
        path = main._checkout_path("owner/repo", 2, "0123456789abcdef")
        rec = self._record(path)
        with patch.object(main, "conversation_status", return_value="running"):
            self.assertFalse(main._release_checkout(rec, "http://s", "k"))
        self.assertTrue(path.exists())
        self.assertIn("workspace_dir", rec)

    def test_keeps_the_checkout_when_the_status_is_unknown(self):
        path = main._checkout_path("owner/repo", 3, "0123456789abcdef")
        rec = self._record(path)
        with patch.object(main, "conversation_status", side_effect=RuntimeError("boom")):
            self.assertFalse(main._release_checkout(rec, "http://s", "k"))
        self.assertTrue(path.exists())

    def test_a_deleted_conversation_counts_as_finished(self):
        path = main._checkout_path("owner/repo", 4, "0123456789abcdef")
        rec = self._record(path)
        error = urllib.error.HTTPError("http://s", 404, "gone", {}, None)
        with patch.object(main, "conversation_status", side_effect=error):
            self.assertTrue(main._release_checkout(rec, "http://s", "k"))
        self.assertFalse(path.exists())

    def test_refuses_to_remove_anything_outside_the_checkout_root(self):
        outside = self.workspace / "not-a-checkout"
        rec = self._record(outside)
        with patch.object(main, "conversation_status", return_value="finished"):
            self.assertTrue(main._release_checkout(rec, "http://s", "k"))
        self.assertTrue(outside.exists())
        self.assertNotIn("workspace_dir", rec)

    def test_refuses_to_remove_the_checkout_root_itself(self):
        root = main._checkouts_root()
        rec = self._record(root)
        with patch.object(main, "conversation_status", return_value="finished"):
            self.assertTrue(main._release_checkout(rec, "http://s", "k"))
        self.assertTrue(root.exists())


# ── State ──────────────────────────────────────────────────────────────────────


class TestState(_CheckoutTestCase):
    """The KV store is unavailable in these tests, so the file fallback is used."""

    def setUp(self):
        super().setUp()
        # WORKSPACE_BASE/automation-runs/<run> is what the dispatcher passes, and
        # the state directory is derived two levels up from it.
        run_dir = self.workspace / "automation-runs" / "run-1"
        run_dir.mkdir(parents=True)
        os.environ["WORKSPACE_BASE"] = str(run_dir)

    def test_each_repo_gets_its_own_document(self):
        a = main.load_state("owner/one")
        a["reviews"]["1:label:100"] = {"status": "active"}
        main.save_state("owner/one", a)

        b = main.load_state("owner/two")
        self.assertEqual(b["reviews"], {})
        self.assertEqual(b["repo"], "owner/two")
        self.assertEqual(main.load_state("owner/one")["reviews"].keys(), {"1:label:100"})

    def test_legacy_single_repo_state_is_adopted_once(self):
        legacy = {
            "version": 2,
            "repo": "owner/one",
            "trigger_label": "openhands-review",
            "reviews": {"5:label:900": {"status": "closed"}},
            "prs": {},
        }
        Path(main._legacy_state_file_path()).write_text(json.dumps(legacy))

        adopted = main.load_state("owner/one")
        self.assertIn("5:label:900", adopted["reviews"])

    def test_legacy_state_is_not_adopted_by_a_different_repo(self):
        legacy = {"version": 2, "repo": "owner/one", "reviews": {"5:label:900": {}}, "prs": {}}
        Path(main._legacy_state_file_path()).write_text(json.dumps(legacy))

        fresh = main.load_state("owner/other")
        self.assertEqual(fresh["reviews"], {})


# ── Review verification ────────────────────────────────────────────────────────


class TestMatchingReviewExists(unittest.TestCase):
    def setUp(self):
        self._login = main._AUTH_LOGIN
        main._AUTH_LOGIN = "review-bot"

    def tearDown(self):
        main._AUTH_LOGIN = self._login

    def _exists(self, reviews):
        with patch.object(main, "_github_paginate", return_value=reviews):
            return main._matching_review_exists("token", "owner/repo", 7, "abc123")

    def test_true_for_our_review_at_this_commit(self):
        self.assertTrue(self._exists([{"user": {"login": "Review-Bot"}, "commit_id": "abc123"}]))

    def test_false_for_someone_elses_review(self):
        self.assertFalse(self._exists([{"user": {"login": "human"}, "commit_id": "abc123"}]))

    def test_false_for_our_review_at_another_commit(self):
        self.assertFalse(self._exists([{"user": {"login": "review-bot"}, "commit_id": "older"}]))

    def test_false_when_the_listing_fails(self):
        with patch.object(main, "_github_paginate", side_effect=RuntimeError("boom")):
            self.assertFalse(main._matching_review_exists("token", "owner/repo", 7, "abc123"))


# ── Claiming a label event before the review starts ────────────────────────────


class TestClaimBeforeReview(_CheckoutTestCase):
    """State must record the claim before the slow work, or two overlapping
    polls both start a review of the same label event."""

    PR = {"number": 7, "title": "t", "html_url": "u", "head": {"sha": "abc123def456"}}
    EVENT = {"id": 4242, "created_at": "2026-01-01T00:00:00Z"}

    def setUp(self):
        super().setUp()
        self.reviews: dict = {}
        self.snapshots: list = []

    def _persist(self):
        self.snapshots.append(json.loads(json.dumps(self.reviews)))

    def _run(self, prepare=None, create=None):
        prepare = prepare or (lambda *a, **k: self.workspace / "checkout")
        create = create or (lambda *a, **k: "conv-1")
        with (
            patch.object(main, "_prepare_repository", side_effect=prepare),
            patch.object(main, "create_conversation", side_effect=create),
            patch.object(main, "_post_github_comment"),
        ):
            return main._process_review_request(
                "token", "http://agent", "key", "http://oh",
                "owner/repo", self.PR, self.EVENT, self.reviews, self._persist,
            )

    def test_the_claim_is_persisted_before_the_conversation_is_created(self):
        seen_at_create: list = []

        def create(*_args, **_kwargs):
            # What a concurrent poll would read at this moment.
            seen_at_create.append(json.loads(json.dumps(self.snapshots[-1])))
            return "conv-1"

        self._run(create=create)
        key = main._review_key(7, 4242)
        self.assertEqual(len(seen_at_create), 1)
        self.assertIn(key, seen_at_create[0], "claim must be persisted before the conversation")
        self.assertEqual(seen_at_create[0][key]["status"], "starting")
        self.assertIsNone(seen_at_create[0][key]["conversation_id"])

    def test_the_claim_becomes_active_with_the_conversation(self):
        self.assertEqual(self._run(), "conv-1")
        rec = self.reviews[main._review_key(7, 4242)]
        self.assertEqual(rec["status"], "active")
        self.assertEqual(rec["conversation_id"], "conv-1")
        self.assertEqual(self.snapshots[-1][main._review_key(7, 4242)]["status"], "active")

    def test_a_failed_start_releases_the_claim_so_the_next_poll_retries(self):
        def boom(*_args, **_kwargs):
            raise RuntimeError("archive unavailable")

        self.assertIsNone(self._run(prepare=boom))
        key = main._review_key(7, 4242)
        self.assertNotIn(key, self.reviews)
        self.assertIn(key, self.snapshots[0], "the claim was taken")
        self.assertNotIn(key, self.snapshots[-1], "and released again, persisted")


class TestStalledClaims(_CheckoutTestCase):
    """A poll that dies between claiming and creating its conversation must not
    park the label event forever."""

    def _poll(self, records):
        state = {"reviews": dict(records), "prs": {}}
        saved: list = []
        with (
            patch.object(main, "_verify_repo"),
            patch.object(main, "load_state", return_value=state),
            patch.object(main, "_list_open_prs", return_value=[]),
            patch.object(main, "save_state", side_effect=lambda _repo, s: saved.append(s)),
        ):
            main._process_repo("owner/repo", "token", "http://agent", "key", "http://oh")
        return state["reviews"], saved

    def test_a_fresh_claim_is_left_alone(self):
        reviews, _ = self._poll({"7:label:1": {"status": "starting", "last_activity": time.time()}})
        self.assertIn("7:label:1", reviews)

    def test_a_stalled_claim_is_released(self):
        stale = time.time() - main.STALLED_CLAIM_SECONDS - 1
        reviews, saved = self._poll({"7:label:1": {"status": "starting", "last_activity": stale}})
        self.assertNotIn("7:label:1", reviews)
        self.assertNotIn("7:label:1", saved[-1]["reviews"])

    def test_a_claim_without_a_timestamp_is_released(self):
        reviews, _ = self._poll({"7:label:1": {"status": "starting"}})
        self.assertNotIn("7:label:1", reviews)


# ── Stale required-CI reconciliation ───────────────────────────────────────────


DAY = 24 * 60 * 60
HEAD = "0123456789abcdef0123456789abcdef01234567"
OTHER_HEAD = "fedcba9876543210fedcba9876543210fedcba98"


def _check_run(name, conclusion, *, status="completed", completed_at=None, run_id=1):
    return {
        "id": run_id,
        "name": name,
        "status": status,
        "conclusion": conclusion,
        "started_at": completed_at,
        "completed_at": completed_at,
    }


def _state(status="completed", conclusion="failure", completed_at=None):
    return {
        "status": status,
        "conclusion": conclusion,
        "started_at": completed_at,
        "completed_at": completed_at,
    }


class TestClassifyRequiredCi(unittest.TestCase):
    def test_no_required_checks_is_passing(self):
        self.assertEqual(main.classify_required_ci(set(), {"test": _state()}), ("passing", None))

    def test_success_is_passing(self):
        state, since = main.classify_required_ci(
            {"test"}, {"test": _state(conclusion="success")}
        )
        self.assertEqual(state, "passing")
        self.assertIsNone(since)

    def test_optional_failures_are_ignored(self):
        # "lint" failed but is not required; only "test" is.
        states = {"test": _state(conclusion="success"), "lint": _state(conclusion="failure")}
        self.assertEqual(main.classify_required_ci({"test"}, states), ("passing", None))

    def test_failure_reports_the_streak_start(self):
        completed = "2026-01-01T00:00:00Z"
        states = {"test": _state(conclusion="failure", completed_at=completed)}
        state, since = main.classify_required_ci({"test"}, states)
        self.assertEqual(state, "failing")
        self.assertIsNotNone(since)

    def test_failure_since_is_the_earliest_failing_check(self):
        early = "2026-01-01T00:00:00Z"
        late = "2026-01-03T00:00:00Z"
        states = {
            "a": _state(conclusion="failure", completed_at=late),
            "b": _state(conclusion="failure", completed_at=early),
        }
        _, since = main.classify_required_ci({"a", "b"}, states)
        self.assertEqual(since, main._parse_github_time(early))

    def test_missing_required_check_is_pending(self):
        self.assertEqual(main.classify_required_ci({"test"}, {}), ("pending", None))

    def test_in_progress_run_is_pending(self):
        states = {"test": _state(status="in_progress", conclusion=None)}
        self.assertEqual(main.classify_required_ci({"test"}, states), ("pending", None))

    def test_skipped_and_neutral_do_not_fail(self):
        for conclusion in ("skipped", "neutral"):
            self.assertEqual(
                main.classify_required_ci({"test"}, {"test": _state(conclusion=conclusion)}),
                ("passing", None),
            )

    def test_a_failing_and_a_pending_check_is_pending(self):
        # A recovered/pending required check gates the close even if another fails.
        states = {
            "a": _state(conclusion="failure"),
            "b": _state(status="queued", conclusion=None),
        }
        self.assertEqual(main.classify_required_ci({"a", "b"}, states), ("pending", None))


class TestStaleCiLifecycle(unittest.TestCase):
    """End-to-end reconcile_stale_ci decisions over the mocked GitHub boundary."""

    def setUp(self):
        self.comments: list[dict] = []
        self.posted: list[str] = []
        self.closed: list[int] = []
        self.rules = [{"type": "required_status_checks", "parameters": {"required_status_checks": [{"context": "test"}]}}]
        self.runs = [_check_run("test", "failure", completed_at="2026-01-01T00:00:00Z")]
        self.statuses: list[dict] = []

    def _pr(self, *, number=7, head=HEAD, draft=False, author="alice", base="main"):
        return {
            "number": number,
            "draft": draft,
            "user": {"login": author},
            "base": {"ref": base},
            "head": {"sha": head},
        }

    def _post(self, body):
        comment = {
            "id": len(self.comments) + 1,
            "body": body,
            "user": {"login": "review-bot"},
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.now)),
        }
        self.comments.append(comment)
        self.posted.append(body)
        return comment

    def _patch(self):
        return [
            patch.object(main, "_github_paginate", side_effect=self._paginate),
            patch.object(main, "_list_check_runs", side_effect=lambda *a, **k: self.runs),
            patch.object(main, "_github_request", side_effect=self._request),
        ]

    def _paginate(self, token, path, params=None):
        if "/rules/branches/" in path:
            return self.rules
        if path.endswith("/statuses"):
            return self.statuses
        if path.endswith("/comments"):
            return list(self.comments)
        raise AssertionError(f"unexpected pagination {path}")

    def _request(self, token, method, path, params=None, body=None):
        if "/protection" in path:
            return {}, {}
        if method == "POST" and path.endswith("/comments"):
            return self._post(body["body"]), {}
        if method == "PATCH" and "/pulls/" in path:
            self.closed.append(int(path.rsplit("/", 1)[1]))
            return {}, {}
        raise AssertionError(f"unexpected request {method} {path}")

    def _reconcile(self, now, pr=None):
        self.now = now
        with contextlib.ExitStack() as stack:
            for p in self._patch():
                stack.enter_context(p)
            return main.reconcile_stale_ci("token", "owner/repo", pr or self._pr(), now=now)

    def test_no_required_checks_skips(self):
        self.rules = []
        result = self._reconcile(main._parse_github_time("2026-02-01T00:00:00Z") + 30 * DAY)
        self.assertEqual(result["action"], "skipped")
        self.assertEqual(self.posted, [])

    def test_pending_required_ci_skips(self):
        self.runs = [_check_run("test", None, status="in_progress", completed_at=None)]
        result = self._reconcile(main._parse_github_time("2026-03-01T00:00:00Z"))
        self.assertEqual(result["action"], "skipped")
        self.assertIn("pending", result["reason"])

    def test_passing_required_ci_skips(self):
        self.runs = [_check_run("test", "success", completed_at="2026-01-01T00:00:00Z")]
        result = self._reconcile(main._parse_github_time("2026-03-01T00:00:00Z"))
        self.assertEqual(result["action"], "skipped")
        self.assertIn("passing", result["reason"])

    def test_failure_newer_than_grace_does_not_warn(self):
        now = main._parse_github_time("2026-01-05T00:00:00Z")
        result = self._reconcile(now)
        self.assertEqual(result["action"], "waiting")
        self.assertEqual(self.posted, [])

    def test_failure_older_than_grace_warns_once(self):
        now = main._parse_github_time("2026-01-01T00:00:00Z") + 8 * DAY
        result = self._reconcile(now)
        self.assertEqual(result["action"], "warned")
        self.assertEqual(len(self.posted), 1)
        self.assertIn(main._stale_ci_marker("warning", HEAD), self.posted[0])
        self.assertIn("AI agent", self.posted[0])

    def test_rescan_does_not_duplicate_the_warning(self):
        now = main._parse_github_time("2026-01-01T00:00:00Z") + 8 * DAY
        self._reconcile(now)
        self._reconcile(now + 60)
        self.assertEqual(len(self.posted), 1, "the same window must warn exactly once")

    def test_close_after_response_window_without_follow_up(self):
        start = main._parse_github_time("2026-01-01T00:00:00Z")
        self._reconcile(start + 8 * DAY)  # warn
        result = self._reconcile(start + 8 * DAY + main.STALE_CI_RESPONSE_SECONDS + 60)
        self.assertEqual(result["action"], "closed")
        self.assertEqual(self.closed, [7])
        self.assertIn(main._stale_ci_marker("closed", HEAD), self.posted[-1])

    def test_close_is_idempotent_on_rescan(self):
        start = main._parse_github_time("2026-01-01T00:00:00Z")
        self._reconcile(start + 8 * DAY)
        close_at = start + 8 * DAY + main.STALE_CI_RESPONSE_SECONDS + 60
        self._reconcile(close_at)
        result = self._reconcile(close_at + DAY)
        self.assertEqual(result["action"], "closed")
        self.assertEqual(len(self.closed), 2, "the close PATCH is re-applied, not just logged")
        self.assertEqual(len(self.posted), 2, "no second closure comment")

    def test_author_comment_after_warning_prevents_close(self):
        start = main._parse_github_time("2026-01-01T00:00:00Z")
        self._reconcile(start + 8 * DAY)
        self.comments.append(
            {
                "id": 99,
                "body": "Working on the fix",
                "user": {"login": "alice"},
                "created_at": time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime(start + 8 * DAY + 60)
                ),
            }
        )
        result = self._reconcile(start + 8 * DAY + main.STALE_CI_RESPONSE_SECONDS + 60)
        self.assertEqual(result["action"], "warned", "follow-up starts a fresh window")
        self.assertEqual(self.closed, [])

    def test_author_commit_after_warning_prevents_close(self):
        start = main._parse_github_time("2026-01-01T00:00:00Z")
        self._reconcile(start + 8 * DAY)
        # A new head is a follow-up: the warning names the old head.
        result = self._reconcile(start + 8 * DAY + main.STALE_CI_RESPONSE_SECONDS + 60, pr=self._pr(head=OTHER_HEAD))
        self.assertEqual(result["action"], "warned")
        self.assertEqual(self.closed, [])
        self.assertIn(main._stale_ci_marker("warning", OTHER_HEAD), self.posted[-1])

    def test_ci_recovery_prevents_close(self):
        start = main._parse_github_time("2026-01-01T00:00:00Z")
        self._reconcile(start + 8 * DAY)
        self.runs = [_check_run("test", "success", completed_at="2026-01-09T00:00:00Z")]
        result = self._reconcile(start + 8 * DAY + main.STALE_CI_RESPONSE_SECONDS + 60)
        self.assertEqual(result["action"], "skipped")
        self.assertEqual(self.closed, [])

    def test_optional_failed_check_does_not_warn(self):
        self.runs = [
            _check_run("test", "success", completed_at="2026-01-01T00:00:00Z"),
            _check_run("optional-lint", "failure", completed_at="2026-01-01T00:00:00Z", run_id=2),
        ]
        now = main._parse_github_time("2026-01-01T00:00:00Z") + 8 * DAY
        result = self._reconcile(now)
        self.assertEqual(result["action"], "skipped")
        self.assertEqual(self.posted, [])

    def test_missing_head_or_base_skips(self):
        result = self._reconcile(time.time(), pr={"number": 7, "draft": False, "base": {}, "head": {}})
        self.assertEqual(result["action"], "skipped")
        self.assertEqual(self.posted, [])


class TestStaleCiRepoPass(_CheckoutTestCase):
    """The scheduled pass covers every open non-draft PR, not just labelled ones."""

    def test_draft_prs_are_skipped(self):
        seen = []

        def fake(token, repo, pr, **kwargs):
            seen.append(pr["number"])
            return {"pr": pr["number"], "action": "waiting", "reason": ""}

        prs = [{"number": 1, "draft": False}, {"number": 2, "draft": True}, {"number": 3, "draft": False}]
        with patch.object(main, "reconcile_stale_ci", side_effect=fake):
            main._reconcile_repo_stale_ci("token", "owner/repo", prs)
        self.assertEqual(seen, [1, 3])

    def test_one_pr_failure_does_not_stop_the_pass(self):
        seen = []

        def fake(token, repo, pr, **kwargs):
            seen.append(pr["number"])
            if pr["number"] == 1:
                raise RuntimeError("boom")
            return {"pr": pr["number"], "action": "waiting", "reason": ""}

        prs = [{"number": 1, "draft": False}, {"number": 2, "draft": False}]
        with patch.object(main, "reconcile_stale_ci", side_effect=fake):
            main._reconcile_repo_stale_ci("token", "owner/repo", prs)
        self.assertEqual(seen, [1, 2])


class TestLoadConfig(unittest.TestCase):
    """The catalog path ships config.json; the agent path ships none."""

    def _write(self, payload) -> Path:
        directory = Path(tempfile.mkdtemp())
        body = payload if isinstance(payload, str) else json.dumps(payload)
        (directory / main.CONFIG_FILENAME).write_text(body)
        return directory

    def test_absent_config_leaves_the_defaults_alone(self):
        self.assertEqual(main.load_config(Path(tempfile.mkdtemp())), {})

    def test_declared_keys_are_returned(self):
        directory = self._write(
            {
                "repos": ["owner/one", "owner/two"],
                "trigger_label": "please-review",
                "review_tone": "friendly",
                "review_style_instructions": "be kind",
                "repo_review_guide_path": "docs/review.md",
                "openhands_url": "http://localhost:8010",
            }
        )
        self.assertEqual(
            main.load_config(directory),
            {
                "repos": ["owner/one", "owner/two"],
                "trigger_label": "please-review",
                "review_tone": "friendly",
                "review_style_instructions": "be kind",
                "repo_review_guide_path": "docs/review.md",
                "openhands_url": "http://localhost:8010",
            },
        )

    def test_a_partial_config_only_overrides_what_it_states(self):
        directory = self._write({"trigger_label": "please-review"})
        self.assertEqual(main.load_config(directory), {"trigger_label": "please-review"})

    def test_unknown_keys_are_ignored(self):
        directory = self._write({"trigger_label": "x", "shipped_by": "catalog"})
        self.assertEqual(main.load_config(directory), {"trigger_label": "x"})

    def test_a_string_where_a_list_belongs_is_rejected(self):
        # Otherwise the poll loop iterates "owner/repo" one character at a time.
        directory = self._write({"repos": "owner/repo"})
        with self.assertRaises(SystemExit):
            main.load_config(directory)

    def test_an_empty_repo_list_is_rejected(self):
        directory = self._write({"repos": []})
        with self.assertRaises(SystemExit):
            main.load_config(directory)

    def test_a_non_string_repo_is_rejected(self):
        directory = self._write({"repos": ["owner/repo", 7]})
        with self.assertRaises(SystemExit):
            main.load_config(directory)

    def test_a_non_string_label_is_rejected(self):
        directory = self._write({"trigger_label": ["a", "b"]})
        with self.assertRaises(SystemExit):
            main.load_config(directory)

    def test_malformed_json_is_rejected(self):
        directory = self._write("{not json")
        with self.assertRaises(SystemExit):
            main.load_config(directory)

    def test_a_json_array_is_rejected(self):
        directory = self._write(["owner/repo"])
        with self.assertRaises(SystemExit):
            main.load_config(directory)


class TestRepoReviewGuide(unittest.TestCase):
    """The repo-specific review guide is read from the checkout and injected
    into the prompt when present, and silently absent when not."""

    def _pr(self):
        return {
            "number": 42,
            "title": "Add widget",
            "body": "ships it",
            "html_url": "https://github.com/owner/repo/pull/42",
            "user": {"login": "alice"},
            "base": {"ref": "main"},
            "head": {"ref": "feature", "sha": "0123456789abcdef0123456789abcdef01234567"},
            "labels": [],
            "changed_files": 1,
            "additions": 10,
            "deletions": 2,
        }

    def test_reads_the_guide_when_present(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            guide_dir = root / ".agents" / "skills"
            guide_dir.mkdir(parents=True)
            (guide_dir / "custom-codereview-guide.md").write_text("# Guide\nApprove freely.")
            with patch.object(main, "REPO_REVIEW_GUIDE_PATH", ".agents/skills/custom-codereview-guide.md"):
                text = main._load_repo_review_guide(root)
            self.assertEqual(text, "# Guide\nApprove freely.")

    def test_returns_none_when_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(main, "REPO_REVIEW_GUIDE_PATH", ".agents/skills/custom-codereview-guide.md"):
                self.assertIsNone(main._load_repo_review_guide(Path(tmp)))

    def test_empty_path_disables(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "guide.md").write_text("irrelevant")
            with patch.object(main, "REPO_REVIEW_GUIDE_PATH", ""):
                self.assertIsNone(main._load_repo_review_guide(root))

    def test_guide_text_is_injected_into_the_prompt(self):
        pr = self._pr()
        prompt = main._build_review_prompt(
            "owner/repo", pr, "0123456789abcdef", {"id": "1", "created_at": "t"},
            repo_review_guide="APPROVE all low-risk PRs.",
        )
        self.assertIn("APPROVE all low-risk PRs.", prompt)
        self.assertIn("Repo-specific review guide", prompt)

    def test_no_guide_section_when_guide_is_none(self):
        pr = self._pr()
        prompt = main._build_review_prompt(
            "owner/repo", pr, "0123456789abcdef", {"id": "1", "created_at": "t"},
            repo_review_guide=None,
        )
        self.assertNotIn("Repo-specific review guide", prompt)

    def test_prompt_requires_reading_repository_guidance(self):
        prompt = main._build_review_prompt(
            "owner/repo",
            self._pr(),
            "0123456789abcdef",
            {"id": "1", "created_at": "t"},
        )

        self.assertIn("MUST read", prompt)
        self.assertIn("AGENTS.md", prompt)
        self.assertIn("CONTRIBUTING.md", prompt)
        self.assertIn("nested `AGENTS.md`", prompt)

    def test_prompt_uses_native_approval_for_a_clean_review(self):
        prompt = main._build_review_prompt(
            "owner/repo",
            self._pr(),
            "0123456789abcdef",
            {"id": "1", "created_at": "t"},
        )

        self.assertIn("`event: APPROVE`", prompt)
        self.assertIn("otherwise use `event: COMMENT`", prompt)
        self.assertIn("Never use `REQUEST_CHANGES`", prompt)
        self.assertIn("native GitHub review is the only result channel", prompt)
        self.assertIn("Do not create commit statuses or Checks", prompt)
        self.assertIn("Do not add speculative or out-of-scope notes", prompt)
        self.assertIn("forbids the configured bot from approving its own PR", prompt)

    def test_prompt_requires_refreshing_mutable_github_state(self):
        """A resumed conversation must not trust an earlier turn's observations."""
        prompt = main._build_review_prompt(
            "owner/repo",
            self._pr(),
            "0123456789abcdef",
            {"id": "1", "created_at": "t"},
        )

        assert "CURRENT STATE" in prompt
        for surface in (
            "still matches the Head SHA",
            "current PR title and body",
            "current review comments and threads",
            "current review requests",
            "GitHub Actions check results",
            "body and labels of every linked issue",
        ):
            self.assertIn(surface, prompt)
        # The readiness case from the report: a linked issue gaining a label.
        self.assertIn("ready-for-dev", prompt)

    def test_prompt_forbids_repeating_an_earlier_observation(self):
        prompt = main._build_review_prompt(
            "owner/repo",
            self._pr(),
            "0123456789abcdef",
            {"id": "1", "created_at": "t"},
        )

        self.assertIn("fresh review", prompt)
        self.assertIn("re-established now", prompt)
        self.assertIn(
            "never repeat an earlier finding, verdict, or "
            "label/priority claim",
            prompt,
        )

    def test_prompt_refreshes_state_before_the_scope_gate_and_keeps_analysis(self):
        prompt = main._build_review_prompt(
            "owner/repo",
            self._pr(),
            "0123456789abcdef",
            {"id": "1", "created_at": "t"},
        )

        # The refresh precedes the verdict-shaping steps, while the repository
        # analysis the conversation already did stays part of the workflow.
        self.assertLess(prompt.index("CURRENT STATE"), prompt.index("SCOPE GATE"))
        self.assertLess(prompt.index("CURRENT STATE"), prompt.index("MUST read"))
        self.assertIn("useful background", prompt)
        self.assertIn("AGENTS.md", prompt)

    def test_prompt_scope_gate_stops_before_the_technical_review(self):
        prompt = main._build_review_prompt(
            "owner/repo",
            self._pr(),
            "0123456789abcdef",
            {"id": "1", "created_at": "t"},
        )

        gate = prompt.index("SCOPE GATE")
        self.assertLess(gate, prompt.index("Inspect the PR discussion"))
        self.assertLess(gate, prompt.index("Ground every finding"))
        self.assertIn("before inspecting changed files, reading the diff, or running", prompt)
        self.assertIn("scope categories and ownership boundaries", prompt)
        self.assertIn("continue the technical review unchanged", prompt)
        self.assertIn("move repositories, close, or receive a maintainer decision", prompt)


class TestNormalizeRepo(unittest.TestCase):
    """A repository is written down in more than one way, and every API path in
    this script is built from owner/repo."""

    def test_a_repository_name_passes_through(self):
        self.assertEqual(main.normalize_repo("OpenHands/automation"), "OpenHands/automation")

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(main.normalize_repo("  owner/repo\n"), "owner/repo")

    def test_the_clone_url_a_repository_page_offers_is_accepted(self):
        # The value a user is most likely to paste, and the one that used to
        # 404 as "not accessible with the current token".
        self.assertEqual(
            main.normalize_repo("https://github.com/VascoSch92/symmetria"),
            "VascoSch92/symmetria",
        )

    def test_a_dot_git_suffix_is_dropped(self):
        self.assertEqual(
            main.normalize_repo("https://github.com/owner/repo.git"), "owner/repo"
        )

    def test_a_trailing_slash_is_dropped(self):
        self.assertEqual(main.normalize_repo("https://github.com/owner/repo/"), "owner/repo")

    def test_an_ssh_remote_is_accepted(self):
        self.assertEqual(
            main.normalize_repo("git@github.com:owner/repo.git"), "owner/repo"
        )

    def test_a_bare_name_is_rejected(self):
        with self.assertRaises(ValueError):
            main.normalize_repo("symmetria")

    def test_an_owner_without_a_repository_is_rejected(self):
        with self.assertRaises(ValueError):
            main.normalize_repo("https://github.com/VascoSch92")

    def test_extra_path_segments_are_rejected(self):
        # A pull request URL names a page, not a repository.
        with self.assertRaises(ValueError):
            main.normalize_repo("https://github.com/owner/repo/pull/7")

    def test_the_message_names_the_value_it_could_not_read(self):
        with self.assertRaises(ValueError) as caught:
            main.normalize_repo("not a repo")
        self.assertIn("not a repo", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
