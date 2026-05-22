"""Unit tests for github-repo-monitor main.py.

Run from the skill root:
    python -m pytest tests/
or with the standard library runner:
    python -m unittest discover tests
"""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

# Allow importing main.py from the sibling scripts/ directory.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import main  # noqa: E402


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_comment(body="hello @openhands", login="octocat", user_type="User"):
    return {"id": 1, "body": body, "user": {"login": login, "type": user_type},
            "issue_url": "https://api.github.com/repos/owner/repo/issues/7"}


# ── State file tests ───────────────────────────────────────────────────────────

class TestLoadState(unittest.TestCase):

    def test_missing_file_returns_default(self):
        state = main.load_state("/nonexistent/path/state.json")
        self.assertIn("conversations", state)
        self.assertIn("processed_comment_ids", state)
        self.assertEqual(state["version"], 1)

    def test_valid_json_is_loaded(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"version": 1, "custom": "value", "conversations": {}}, f)
            path = f.name
        try:
            state = main.load_state(path)
            self.assertEqual(state["custom"], "value")
        finally:
            os.unlink(path)

    def test_corrupted_json_returns_default(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{this is not valid json!!!}")
            path = f.name
        try:
            state = main.load_state(path)
            # Should return the default state rather than raising.
            self.assertIn("conversations", state)
            self.assertEqual(state["version"], 1)
        finally:
            os.unlink(path)

    def test_empty_file_returns_default(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("")
            path = f.name
        try:
            state = main.load_state(path)
            self.assertIn("conversations", state)
        finally:
            os.unlink(path)


class TestSaveAndLoadRoundtrip(unittest.TestCase):

    def test_roundtrip(self):
        data = {
            "version": 1,
            "conversations": {"42": {"conversation_id": "abc", "status": "active"}},
            "processed_comment_ids": [1, 2, 3],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            main.save_state(path, data)
            loaded = main.load_state(path)
            self.assertEqual(loaded["conversations"]["42"]["conversation_id"], "abc")
            self.assertEqual(loaded["processed_comment_ids"], [1, 2, 3])
        finally:
            os.unlink(path)


# ── Bot detection tests ────────────────────────────────────────────────────────

class TestIsBotComment(unittest.TestCase):

    def test_login_ends_with_bot_suffix(self):
        self.assertTrue(main._is_bot_comment(
            {"user": {"login": "dependabot[bot]", "type": "Bot"}}
        ))

    def test_login_ends_with_bot_suffix_human_type(self):
        # Login suffix alone is sufficient.
        self.assertTrue(main._is_bot_comment(
            {"user": {"login": "mybot[bot]", "type": "User"}}
        ))

    def test_user_type_bot_without_suffix(self):
        self.assertTrue(main._is_bot_comment(
            {"user": {"login": "AutomationService", "type": "Bot"}}
        ))

    def test_human_user_returns_false(self):
        self.assertFalse(main._is_bot_comment(
            {"user": {"login": "octocat", "type": "User"}}
        ))

    def test_missing_user_returns_false(self):
        self.assertFalse(main._is_bot_comment({}))

    def test_null_user_returns_false(self):
        self.assertFalse(main._is_bot_comment({"user": None}))

    def test_login_containing_but_not_ending_with_bot(self):
        # "botuser" does not end with "[bot]" — should be treated as human.
        self.assertFalse(main._is_bot_comment(
            {"user": {"login": "botuser", "type": "User"}}
        ))


# ── Trigger phrase tests ───────────────────────────────────────────────────────

class TestHasTrigger(unittest.TestCase):

    def test_exact_match(self):
        c = _make_comment(body="Please fix this @openhands")
        self.assertTrue(main._has_trigger(c, "@openhands"))

    def test_case_insensitive_upper(self):
        c = _make_comment(body="Hey @OpenHands can you help?")
        self.assertTrue(main._has_trigger(c, "@openhands"))

    def test_case_insensitive_phrase_uppercase(self):
        c = _make_comment(body="@openhands please look at this")
        self.assertTrue(main._has_trigger(c, "@OPENHANDS"))

    def test_custom_trigger_phrase(self):
        c = _make_comment(body="yeehaw! this needs fixing")
        self.assertTrue(main._has_trigger(c, "yeehaw!"))

    def test_absent_phrase_returns_false(self):
        c = _make_comment(body="Just a regular comment, nothing special")
        self.assertFalse(main._has_trigger(c, "@openhands"))

    def test_empty_body_returns_false(self):
        c = _make_comment(body="")
        self.assertFalse(main._has_trigger(c, "@openhands"))

    def test_none_body_returns_false(self):
        c = {"id": 1, "body": None, "user": {"login": "u", "type": "User"}}
        self.assertFalse(main._has_trigger(c, "@openhands"))

    def test_missing_body_returns_false(self):
        c = {"id": 1, "user": {"login": "u", "type": "User"}}
        self.assertFalse(main._has_trigger(c, "@openhands"))


# ── Processed-ID deduplication tests ──────────────────────────────────────────

class TestProcessedIdDeduplication(unittest.TestCase):
    """
    The dedup logic lives in main() but the set membership check is trivial.
    These tests verify the state schema: processed_comment_ids is persisted
    and re-hydrated correctly across simulated runs.
    """

    def test_ids_survive_save_and_load(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            state = {"version": 1, "conversations": {},
                     "processed_comment_ids": [101, 202, 303]}
            main.save_state(path, state)
            loaded = main.load_state(path)
            self.assertIn(101, loaded["processed_comment_ids"])
            self.assertIn(303, loaded["processed_comment_ids"])
            self.assertNotIn(404, loaded["processed_comment_ids"])
        finally:
            os.unlink(path)


# ── Conversation state transition tests ───────────────────────────────────────

class TestEnsureConversation(unittest.TestCase):
    """Tests for _ensure_conversation using mocked API calls."""

    BASE_ARGS = dict(
        agent_url="http://agent",
        api_key="key",
        conv_key="7",
        issue_number=7,
        is_pr=False,
        html_url="https://github.com/owner/repo/issues/7",
        prompt="Do something",
        comment=_make_comment(),
        item_type="issue",
    )

    @patch("main.create_conversation", return_value="new-conv-id")
    def test_creates_new_when_no_existing(self, mock_create):
        conversations = {}
        conv_id, resumed = main._ensure_conversation(conversations=conversations,
                                                      **self.BASE_ARGS)
        self.assertEqual(conv_id, "new-conv-id")
        self.assertFalse(resumed)
        mock_create.assert_called_once()
        self.assertEqual(conversations["7"]["status"], "active")

    @patch("main.send_to_conversation")
    def test_reopens_closed_conversation(self, mock_send):
        conversations = {
            "7": {"conversation_id": "old-conv-id", "status": "closed",
                  "issue_number": 7, "last_activity": 0.0}
        }
        conv_id, resumed = main._ensure_conversation(conversations=conversations,
                                                      **self.BASE_ARGS)
        self.assertEqual(conv_id, "old-conv-id")
        self.assertTrue(resumed)
        mock_send.assert_called_once()
        self.assertEqual(conversations["7"]["status"], "active")

    @patch("main.create_conversation", return_value="fallback-conv-id")
    @patch("main.send_to_conversation", side_effect=RuntimeError("gone"))
    def test_fallback_to_new_when_closed_unreachable(self, mock_send, mock_create):
        conversations = {
            "7": {"conversation_id": "stale-conv-id", "status": "closed",
                  "issue_number": 7, "last_activity": 0.0}
        }
        conv_id, resumed = main._ensure_conversation(conversations=conversations,
                                                      **self.BASE_ARGS)
        self.assertEqual(conv_id, "fallback-conv-id")
        self.assertFalse(resumed)
        mock_create.assert_called_once()
        self.assertEqual(conversations["7"]["status"], "active")

    @patch("main.create_conversation", return_value="brand-new-id")
    def test_creates_new_when_status_unknown(self, mock_create):
        # An entry with an unrecognised status should be treated as missing.
        conversations = {
            "7": {"conversation_id": "weird-id", "status": "unknown"}
        }
        conv_id, resumed = main._ensure_conversation(conversations=conversations,
                                                      **self.BASE_ARGS)
        self.assertEqual(conv_id, "brand-new-id")
        self.assertFalse(resumed)

    @patch("main.create_conversation", side_effect=RuntimeError("API down"))
    def test_raises_when_create_fails(self, _mock_create):
        conversations = {}
        with self.assertRaises(RuntimeError):
            main._ensure_conversation(conversations=conversations, **self.BASE_ARGS)


# ── Acknowledgement message tests ─────────────────────────────────────────────

class TestPostAcknowledgement(unittest.TestCase):

    @patch("main._post_github_comment")
    def test_new_conversation_message(self, mock_post):
        main._post_acknowledgement(
            github_token="tok", repo="o/r", issue_number=5,
            item_type="issue", conv_url="http://app/conv/1", resumed=False,
        )
        body = mock_post.call_args[0][3]
        self.assertIn("OpenHands is on it!", body)
        self.assertNotIn("resuming", body.lower())

    @patch("main._post_github_comment")
    def test_resumed_conversation_message(self, mock_post):
        main._post_acknowledgement(
            github_token="tok", repo="o/r", issue_number=5,
            item_type="pull request", conv_url="http://app/conv/2", resumed=True,
        )
        body = mock_post.call_args[0][3]
        self.assertIn("resuming", body.lower())
        self.assertNotIn("OpenHands is on it!", body)

    @patch("main._post_github_comment")
    def test_trigger_phrase_in_footer(self, mock_post):
        original = main.TRIGGER_PHRASE
        main.TRIGGER_PHRASE = "yeehaw!"
        try:
            main._post_acknowledgement(
                github_token="tok", repo="o/r", issue_number=1,
                item_type="issue", conv_url="http://x", resumed=False,
            )
            body = mock_post.call_args[0][3]
            self.assertIn("yeehaw!", body)
        finally:
            main.TRIGGER_PHRASE = original


# ── _get_agent_dict tests ──────────────────────────────────────────────────────

class TestGetAgentDict(unittest.TestCase):
    """Regression tests for agent-name resolution from /api/settings."""

    def _mock_settings(self, agent_value, llm_value=None):
        """Return a mock urlopen context manager that yields the given settings."""
        payload = json.dumps({
            "agent_settings": {"agent": agent_value, "llm": llm_value or {}}
        }).encode()
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read = MagicMock(return_value=payload)
        return mock_resp

    @patch("urllib.request.urlopen")
    def test_null_agent_falls_back_to_agent(self, mock_urlopen):
        """agent=null in settings must fall back to 'Agent', not propagate as null."""
        mock_urlopen.return_value = self._mock_settings(agent_value=None)
        result = main._get_agent_dict("http://agent", "key")
        self.assertEqual(result["kind"], "Agent")

    @patch("urllib.request.urlopen")
    def test_tools_always_included(self, mock_urlopen):
        """terminal and file_editor must always be present so the agent has bash.

        The runtime-registered names ('terminal', 'file_editor') must be used,
        not the Python class names ('TerminalTool', 'FileEditorTool').
        """
        mock_urlopen.return_value = self._mock_settings(agent_value=None)
        result = main._get_agent_dict("http://agent", "key")
        tool_names = [t["name"] for t in result.get("tools", [])]
        self.assertIn("terminal", tool_names)
        self.assertIn("file_editor", tool_names)

    @patch("urllib.request.urlopen")
    def test_full_app_agent_name_not_forwarded(self, mock_urlopen):
        """Full-app agent names (CodeActAgent, BrowsingAgent, …) must not be forwarded.

        settings["agent_settings"]["agent"] belongs to the full OpenHands app
        registry.  The automation SDK only accepts 'Agent' / 'ACPAgent'.
        Forwarding 'CodeActAgent' causes a 500 with 'Unknown kind' in production.
        """
        for app_agent in ("CodeActAgent", "BrowsingAgent", "SomeFutureAgent"):
            with self.subTest(app_agent=app_agent):
                mock_urlopen.return_value = self._mock_settings(agent_value=app_agent)
                result = main._get_agent_dict("http://agent", "key")
                self.assertEqual(result["kind"], "Agent")

    @patch("urllib.request.urlopen")
    def test_missing_agent_key_falls_back_to_agent(self, mock_urlopen):
        payload = json.dumps({"agent_settings": {"llm": {}}}).encode()
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read = MagicMock(return_value=payload)
        mock_urlopen.return_value = mock_resp
        result = main._get_agent_dict("http://agent", "key")
        self.assertEqual(result["kind"], "Agent")


if __name__ == "__main__":
    unittest.main()
