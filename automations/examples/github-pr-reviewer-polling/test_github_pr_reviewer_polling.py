import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).with_name("main.py")
spec = importlib.util.spec_from_file_location("github_pr_reviewer_polling_example", MODULE_PATH)
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)


class TestPollingGate(unittest.TestCase):
    def test_no_actionable_prs_exits_without_creating_conversation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env = {
                "HOME": temp_dir,
                "AUTOMATION_EVENT_PAYLOAD": json.dumps({"automation_id": "test"}),
                "AGENT_SERVER_URL": "http://agent.example",
                "SESSION_API_KEY": "session-key",
            }
            with patch.dict(os.environ, env, clear=False), \
                 patch.object(main, "get_secret", return_value="github-token"), \
                 patch.object(main, "_poll_actionable_prs", return_value=[]), \
                 patch.object(main, "create_conversation") as create_conversation:
                main.main()

        create_conversation.assert_not_called()

    def test_actionable_pr_starts_conversation_after_polling_gate(self):
        pr = {
            "number": 12,
            "title": "Fix bug",
            "html_url": "https://github.com/owner/repo/pull/12",
            "head": {"sha": "abc123", "ref": "feature"},
            "base": {"ref": "main"},
            "user": {"login": "octocat"},
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            env = {
                "HOME": temp_dir,
                "AUTOMATION_EVENT_PAYLOAD": json.dumps({"automation_id": "test"}),
                "AGENT_SERVER_URL": "http://agent.example",
                "SESSION_API_KEY": "session-key",
            }
            with patch.dict(os.environ, env, clear=False), \
                 patch.object(main, "get_secret", return_value="github-token"), \
                 patch.object(main, "_poll_actionable_prs", return_value=[pr]), \
                 patch.object(main, "create_conversation", return_value="conv-1") as create_conversation:
                main.main()

            state_path = Path(temp_dir) / ".openhands" / "workspaces" / "automation-state" / "github_pr_reviewer_test.json"
            with state_path.open() as f:
                state = json.load(f)

        create_conversation.assert_called_once()
        self.assertEqual(state["reviewed_heads"]["12"], "abc123")
        self.assertEqual(state["started_conversations"]["12"]["conversation_id"], "conv-1")


if __name__ == "__main__":
    unittest.main()
