import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "demo_main", Path(__file__).parent / "inbound-automation/main.py"
)
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)


class AutomationTests(unittest.TestCase):
    def test_secret_lookup_for_local_and_cloud_runtimes(self):
        cases = [
            (
                {
                    "AGENT_SERVER_URL": "http://local.example/",
                    "SESSION_API_KEY": "synthetic",
                },
                "http://local.example/api/settings/secrets/DEMO",
            ),
            (
                {
                    "OPENHANDS_CLOUD_API_URL": "https://cloud.example/",
                    "SANDBOX_ID": "synthetic",
                    "SESSION_API_KEY": "synthetic",
                },
                "https://cloud.example/api/v1/sandboxes/synthetic/settings/secrets/DEMO",
            ),
        ]
        for environment, expected_url in cases:
            with (
                self.subTest(environment=environment),
                patch.dict(os.environ, environment, clear=True),
                patch.object(main.urllib.request, "urlopen") as opened,
            ):
                opened.return_value.__enter__.return_value.read.return_value = (
                    b"secret-value"
                )
                self.assertEqual(main.get_secret("DEMO"), "secret-value")
                request = opened.call_args.args[0]
                self.assertEqual(request.full_url, expected_url)
                self.assertEqual(request.get_header("X-session-api-key"), "synthetic")

    def event(self):
        return {
            "trigger": "event",
            "event": {
                "payload": {
                    "type": "message",
                    "id": "synthetic-activity",
                    "conversation": {"id": "synthetic-conversation"},
                    "text": '<p><at id="0">OpenHands Demo</at>&nbsp;verify TEAMS-INBOUND-001</p>',
                }
            },
        }

    def test_manual_dispatch_and_wrong_events_cannot_post(self):
        for context in [{}, {"event": {"payload": {"type": "other"}}}]:
            with self.assertRaises(ValueError):
                main.validate(context)

    def test_valid_event_and_payload(self):
        self.assertEqual(len(main.validate(self.event())), 64)
        self.assertIn(
            "No AI task", main.card()["attachments"][0]["content"]["body"][1]["text"]
        )

    def test_only_exact_command_is_accepted(self):
        for text in ["verify TEAMS-INBOUND-001 extra", "verify OTHER", "hello"]:
            context = self.event()
            context["event"]["payload"]["text"] = text
            with self.subTest(text=text), self.assertRaises(ValueError):
                main.validate(context)

    def test_receipt_identity_includes_conversation(self):
        first = self.event()
        second = self.event()
        second["event"]["payload"]["conversation"]["id"] = "other-conversation"
        self.assertNotEqual(main.validate(first), main.validate(second))

    def test_missing_delivery_identity_is_rejected(self):
        for field in ["id", "conversation"]:
            context = self.event()
            del context["event"]["payload"][field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                main.validate(context)

    def test_uncertain_send_blocks_repeat(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(main.Path, "home", return_value=Path(directory)),
            patch.dict(
                os.environ, {"AUTOMATION_EVENT_PAYLOAD": json.dumps(self.event())}
            ),
            patch.object(
                main,
                "get_secret",
                return_value="https://example.environment.api.powerplatform.com/test",
            ),
            patch.object(main.urllib.request, "build_opener") as opener,
        ):
            opener.return_value.open.side_effect = TimeoutError()
            with self.assertRaises(RuntimeError):
                main.run()
            with self.assertRaises(FileExistsError):
                main.run()
            self.assertEqual(opener.return_value.open.call_count, 1)

    def test_success_posts_fixed_card_and_records_acceptance(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(main.Path, "home", return_value=Path(directory)),
            patch.dict(
                os.environ, {"AUTOMATION_EVENT_PAYLOAD": json.dumps(self.event())}
            ),
            patch.object(
                main,
                "get_secret",
                return_value="https://example.environment.api.powerplatform.com/test",
            ),
            patch.object(main.urllib.request, "build_opener") as opener,
            patch("builtins.print"),
        ):
            response = opener.return_value.open.return_value.__enter__.return_value
            response.status = 202
            main.run()
            request = opener.return_value.open.call_args.args[0]
            self.assertEqual(json.loads(request.data), main.card())
            self.assertFalse(request.has_header("Authorization"))
            receipt = next(Path(directory).rglob("*.json"))
            self.assertEqual(
                json.loads(receipt.read_text())["state"], "accepted_unverified"
            )
            self.assertEqual(receipt.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
