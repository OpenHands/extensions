"""Unit tests for github-pr-reviewer main.py.

Run from the skill root:
    python -m pytest tests/
or with the standard library runner:
    python -m unittest discover tests

The focus is the logic that owns files and state: preparing a checkout from an
untrusted archive, removing it again, and keeping one repository's state apart
from another's.
"""

import io
import json
import os
import sys
import tarfile
import tempfile
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


if __name__ == "__main__":
    unittest.main()
