"""Unit tests for slack-channel-monitor main.py.

Focused on the atomic save_state + claim_message behavior that prevents
concurrent cron runs from spinning up duplicate conversations for the same
trigger message.

Run from the skill root:
    python -m unittest discover tests
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

# Allow importing main.py from the sibling scripts/ directory.
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import main  # noqa: E402


class TestLoadStateDefault(unittest.TestCase):

    def test_missing_file_returns_default(self):
        state = main.load_state("/nonexistent/path/state.json")
        self.assertEqual(state["version"], 1)
        self.assertIn("conversations", state)
        self.assertIn("processed_message_keys", state)
        self.assertEqual(state["processed_message_keys"], [])


class TestSaveStateAtomic(unittest.TestCase):

    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            data = {
                "version": 1,
                "bot_user_id": "UBOT",
                "last_poll": {"C1": "1234567890.0"},
                "conversations": {"C1:1": {"conversation_id": "x", "status": "active"}},
                "bot_message_ts": ["1.1"],
                "processed_message_keys": ["C1:1234567890.111"],
            }
            main.save_state(path, data)
            loaded = main.load_state(path)
            self.assertEqual(loaded, data)

    def test_no_tmp_sidecar_remains(self):
        """A successful save_state must not leave a `.tmp.*` file behind."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            main.save_state(path, {"version": 1, "processed_message_keys": []})
            files = os.listdir(d)
            self.assertEqual(files, ["state.json"], f"unexpected files: {files}")


class TestClaimMessage(unittest.TestCase):
    """The processed_message_keys strategy prevents concurrent cron runs from
    creating two conversations for the same Slack trigger message."""

    def test_first_claim_wins_second_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            self.assertTrue(main.claim_message(path, "C1", "1716576000.000100"))
            self.assertFalse(main.claim_message(path, "C1", "1716576000.000100"))

    def test_claim_persists_key_on_disk(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            main.claim_message(path, "C1", "1716576000.000100")
            loaded = main.load_state(path)
            self.assertIn("C1:1716576000.000100", loaded["processed_message_keys"])

    def test_claim_is_namespaced_by_channel(self):
        """Same ts in different channels must both succeed (Slack ts is unique
        per-channel, not globally)."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            self.assertTrue(main.claim_message(path, "C1", "1716576000.000100"))
            self.assertTrue(main.claim_message(path, "C2", "1716576000.000100"))
            loaded = main.load_state(path)
            self.assertEqual(
                sorted(loaded["processed_message_keys"]),
                ["C1:1716576000.000100", "C2:1716576000.000100"],
            )

    def test_claim_respects_existing_key(self):
        """Simulates: Run A wrote state, Run B reads disk and tries to claim."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            main.save_state(path, {
                "version": 1,
                "conversations": {},
                "processed_message_keys": ["C1:1716576000.000100"],
            })
            self.assertFalse(main.claim_message(path, "C1", "1716576000.000100"))

    def test_claim_preserves_other_state_fields(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "state.json")
            main.save_state(path, {
                "version": 1,
                "bot_user_id": "UBOT",
                "last_poll": {"C1": "1234567890.0"},
                "conversations": {
                    "C1:1": {"conversation_id": "x", "status": "active"},
                },
                "bot_message_ts": ["1.1"],
                "processed_message_keys": ["C1:1716576000.000100"],
            })
            main.claim_message(path, "C1", "1716576999.999999")
            loaded = main.load_state(path)
            self.assertEqual(loaded["bot_user_id"], "UBOT")
            self.assertEqual(loaded["last_poll"], {"C1": "1234567890.0"})
            self.assertEqual(loaded["conversations"]["C1:1"]["conversation_id"], "x")
            self.assertEqual(loaded["bot_message_ts"], ["1.1"])
            self.assertEqual(
                sorted(loaded["processed_message_keys"]),
                ["C1:1716576000.000100", "C1:1716576999.999999"],
            )


if __name__ == "__main__":
    unittest.main()
