"""Exercise the GitLab factory over real local HTTP (only the external host is redirected)."""

import importlib.util
import io
import json
import os
import tarfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("software_factory", ROOT / "skills/software-factory/scripts/factory.py")
factory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(factory)


class Service(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def reply(self, data, status=200):
        payload = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        path = urlsplit(self.path).path
        data = self.server.data
        if path == "/api/automation/v1/capabilities":
            return self.reply({"features": ["customTarball"],
                               "triggerKinds": data.get("trigger_kinds", ["cron"]),
                               "eventSources": data.get("event_sources", [])})
        if path == "/api/v4/user":
            data["received_token"] = self.headers.get("PRIVATE-TOKEN")
            if data.get("user_status"):
                return self.reply({"message": "401 Unauthorized"}, data["user_status"])
            return self.reply({"username": "review-bot"})
        if path == "/api/v4/projects/group%2Fteam%2Fapi":
            data["received_token"] = self.headers.get("PRIVATE-TOKEN")
            return self.reply({"permissions": {"group_access": {"access_level": data["level"]}},
                               "default_branch": "main"})
        if path == "/api/agent-profiles":
            return self.reply({"error": "GitLab stations do not require profiles"}, 500)
        if path == "/api/automation/v1":
            return self.reply({"automations": [
                {"id": f"automation-{index}", "preset_metadata": {"template": body["template"]}}
                for index, body in enumerate(data["created"], 1)
            ]})
        if path.startswith("/api/automation/v1/automation-"):
            index = int(path.rsplit("-", 1)[-1]) - 1
            return self.reply({"id": f"automation-{index + 1}", "trigger": data["created"][index]["trigger"]})
        return self.reply({"error": path}, 404)

    def do_POST(self):
        path = urlsplit(self.path).path
        raw = self.rfile.read(int(self.headers["Content-Length"]))
        data = self.server.data
        if path == "/api/automation/v1/uploads":
            data["uploads"].append(raw)
            return self.reply({"status": "COMPLETED", "tarball_path": "oh-internal://uploads/test"})
        if path == "/api/automation/v1":
            data["created"].append(json.loads(raw))
            return self.reply({"id": f"automation-{len(data['created'])}", "enabled": False}, 201)
        return self.reply({"error": path}, 404)

    def do_PATCH(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.data["patched"].append(body)
        return self.reply({"id": urlsplit(self.path).path.rsplit("/", 1)[-1]})

    def do_DELETE(self):
        self.server.data["deleted"].append(urlsplit(self.path).path)
        return self.reply({"success": True})


class GitLabFactoryTests(unittest.TestCase):
    def setUp(self):
        self.data = {"level": 30, "created": [], "uploads": [], "patched": [], "deleted": []}
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Service)
        self.server.data = self.data
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.host = "https://gitlab.example.test/api/v4"
        env = os.environ.copy()
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(env)))
        os.environ.update({"OPENHANDS_HOST": self.url,
                           "OPENHANDS_AUTOMATION_API_KEY": "test-session-key",
                           "FACTORY_EXTENSIONS": str(ROOT)})
        os.environ.pop("GITLAB_TOKEN", None)
        os.environ.pop("GITHUB_PERSONAL_ACCESS_TOKEN", None)
        original = factory._request

        def local_transport(method, url, *args, **kwargs):
            # Route only the otherwise inaccessible external GitLab test host
            # to the local HTTP service; exercise the real request and parsing path.
            url = url.replace("https://gitlab.example.test", self.url, 1)
            return original(method, url, *args, **kwargs)

        redirect = patch.object(factory, "_request", side_effect=local_transport)
        redirect.start()
        self.addCleanup(redirect.stop)
        self.args = SimpleNamespace(provider="gitlab", repos="group/team/api",
                                    gitlab_api_url=self.host, profile=None)

    def test_missing_token_reports_request_secret_without_github_checks(self):
        result = factory.preflight(self.args)
        self.assertEqual(result["gitlab_login"], None)
        self.assertIn("not_set", result["token_error"])
        self.assertIn("GITLAB_TOKEN", result["token_error"])
        self.assertEqual(result["stations"]["gitlab-mr-reviewer"], "ok")
        self.assertNotIn("github-pr-reviewer", result["stations"])
        self.assertNotIn("received_token", self.data)

    def test_preflight_checks_host_token_and_project_role(self):
        os.environ["GITLAB_TOKEN"] = "test-pat"
        result = factory.preflight(self.args)
        self.assertEqual(result["gitlab_login"], "review-bot")
        self.assertEqual(result["repos"], {"group/team/api": "push"})
        self.assertEqual(self.data["received_token"], "test-pat")
        self.assertNotIn("test-pat", json.dumps(result))
        self.data["level"] = 20
        self.assertEqual(factory.preflight(self.args)["repos"], {"group/team/api": "no push"})

    def test_invalid_token_is_rejected_without_printing_its_value(self):
        os.environ["GITLAB_TOKEN"] = "bad-pat"
        self.data["user_status"] = 401
        result = factory.preflight(self.args)
        self.assertIsNone(result["gitlab_login"])
        self.assertTrue(result["token_error"].startswith("rejected:"))
        self.assertNotIn("bad-pat", json.dumps(result))

    def test_github_default_still_uses_github_stations_and_secret(self):
        result = factory.preflight(SimpleNamespace(repos="acme/api", profile=None))
        self.assertIsNone(result["github_login"])
        self.assertIn("GITHUB_PERSONAL_ACCESS_TOKEN", result["token_error"])
        self.assertIn("github-pr-reviewer", result["stations"])
        self.assertNotIn("gitlab-mr-reviewer", result["stations"])

    def test_create_uses_gitlab_manifests_and_host_without_github_token(self):
        args = SimpleNamespace(**vars(self.args), ids="gitlab-issue-to-mr,gitlab-mr-reviewer,gitlab-prd-refiner", set=None)
        result = factory.create(args)
        self.assertEqual(len(result["created"]), 3)
        self.assertEqual([body["template"]["id"] for body in self.data["created"]], args.ids.split(","))
        for body, archive in zip(self.data["created"], self.data["uploads"]):
            self.assertEqual(body["template"]["config"]["gitlab_api_url"], self.host)
            self.assertEqual(body["template"]["config"]["projects"], ["group/team/api"])
            self.assertFalse(body["enabled"])
            self.assertEqual(body["tags"], ["software-factory"])
            self.assertNotIn("agent_profile_id", body)
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
                self.assertEqual(json.load(tar.extractfile("config.json")), body["template"]["config"])
        self.assertNotIn("GITHUB_PERSONAL_ACCESS_TOKEN", json.dumps(self.data["created"]))

    def test_preflight_reports_webhook_availability_before_token_setup(self):
        self.data.update(trigger_kinds=["cron", "event"], event_sources=["gitlab-signed"])
        result = factory.preflight(self.args)
        self.assertTrue(result["event_supported"])
        self.assertEqual(result["event_sources"], ["gitlab-signed"])

    def test_create_gitlab_event_stations_from_registered_source(self):
        self.data.update(trigger_kinds=["cron", "event"], event_sources=["gitlab-signed"])
        args = SimpleNamespace(**vars(self.args), ids="gitlab-issue-to-mr,gitlab-mr-reviewer,gitlab-prd-refiner",
                               set=None, trigger="event", event_source="gitlab-signed")
        result = factory.create(args)
        self.assertEqual(len(result["created"]), 3)
        for body in self.data["created"]:
            station = body["template"]["id"]
            self.assertEqual(body["trigger"], {"type": "event", "source": "gitlab-signed",
                                               "on": "merge_request" if station == "gitlab-mr-reviewer" else "issue",
                                               "filter": json.loads((ROOT / "automations/catalog" / station / "manifest.json")
                                                                    .read_text())["setup"]["filter"]})
            self.assertFalse(body["enabled"])
            self.assertNotIn("webhook_secret", json.dumps(body))

    def test_verify_enables_webhook_station_without_empty_dispatch(self):
        self.data.update(trigger_kinds=["cron", "event"], event_sources=["gitlab-signed"])
        args = SimpleNamespace(**vars(self.args), ids="gitlab-mr-reviewer", set=None,
                               trigger="event", event_source="gitlab-signed")
        factory.create(args)
        result = factory.verify(SimpleNamespace(ids=["automation-1"], no_wait=[], timeout=10))
        self.assertEqual(result["automation-1"]["status"], "AWAITING_EVENT")
        self.assertTrue(result["automation-1"]["enabled"])
        self.assertEqual(self.data["patched"], [{"enabled": True}])

    def test_tune_event_keeps_source_and_can_switch_back_to_polling(self):
        self.data.update(trigger_kinds=["cron", "event"], event_sources=["gitlab-signed"])
        args = SimpleNamespace(**vars(self.args), ids="gitlab-mr-reviewer", set=None,
                               trigger="event", event_source="gitlab-signed")
        factory.create(args)
        args.trigger = None
        args.event_source = None
        args.set = ["triggerLabel=review-now"]
        factory.tune(args)
        self.assertEqual(self.data["patched"][-1]["trigger"]["source"], "gitlab-signed")
        self.assertEqual(self.data["patched"][-1]["trigger"]["on"], "merge_request")
        args.trigger = "cron"
        factory.tune(args)
        self.assertEqual(self.data["patched"][-1]["trigger"]["type"], "cron")

    def test_event_mode_does_not_claim_github_support(self):
        args = SimpleNamespace(provider="github", repos="acme/api", ids="github-pr-reviewer",
                               set=None, trigger="event", event_source="gitlab-signed")
        with self.assertRaisesRegex(factory.FactoryError, "only for GitLab"):
            factory.create(args)
        self.assertEqual(self.data["uploads"], [])

    def test_event_requires_advertised_trigger_and_registered_source(self):
        args = SimpleNamespace(**vars(self.args), ids="gitlab-mr-reviewer", set=None,
                               trigger="event", event_source="gitlab-signed")
        with self.assertRaisesRegex(factory.FactoryError, "event triggers"):
            factory.create(args)
        self.data["trigger_kinds"] = ["cron", "event"]
        with self.assertRaisesRegex(factory.FactoryError, "automations/events"):
            factory.create(args)
        self.data["event_sources"] = ["gitlab-signed"]
        args.event_source = None
        with self.assertRaisesRegex(factory.FactoryError, "event-source"):
            factory.create(args)
        self.assertEqual(self.data["uploads"], [])

    def test_tune_keeps_same_host_and_updates_existing_station(self):
        args = SimpleNamespace(**vars(self.args), ids="gitlab-mr-reviewer", set=None)
        factory.create(args)
        args.set = ["triggerLabel=review-now"]
        result = factory.tune(args)
        self.assertEqual([item["id"] for item in result["tuned"]], ["automation-1"])
        self.assertEqual(len(self.data["created"]), 1)
        self.assertEqual(self.data["patched"][0]["name"], self.data["created"][0]["name"])
        self.assertNotIn("template", self.data["patched"][0])
        with tarfile.open(fileobj=io.BytesIO(self.data["uploads"][-1]), mode="r:gz") as tar:
            config = json.load(tar.extractfile("config.json"))
        self.assertEqual(config["gitlab_api_url"], self.host)
        self.assertEqual(config["trigger_label"], "review-now")

    def test_rejects_cross_provider_stations_and_host_override(self):
        args = SimpleNamespace(**vars(self.args), ids="github-pr-reviewer", set=None)
        with self.assertRaisesRegex(factory.FactoryError, "selected gitlab"):
            factory.create(args)
        args.ids = "gitlab-mr-reviewer"
        args.set = ["gitlabApiUrl=https://gitlab.com/api/v4"]
        with self.assertRaisesRegex(factory.FactoryError, "--gitlab-api-url"):
            factory.create(args)
        self.assertEqual(self.data["uploads"], [])

    def test_unknown_project_role_is_not_claimed_as_write_access(self):
        os.environ["GITLAB_TOKEN"] = "test-pat"
        self.data["level"] = None
        self.assertEqual(factory.preflight(self.args)["repos"], {"group/team/api": "role unknown"})

    def test_reset_token_deletes_only_gitlab_token(self):
        result = factory.reset_token(SimpleNamespace(provider="gitlab"))
        self.assertEqual(result, {"deleted": "GITLAB_TOKEN"})
        self.assertEqual(self.data["deleted"], ["/api/settings/secrets/GITLAB_TOKEN"])

    def test_invalid_api_url_fails_before_sending_token(self):
        os.environ["GITLAB_TOKEN"] = "test-pat"
        self.args.gitlab_api_url = "http://gitlab.example.test/api/v4"
        with self.assertRaises(factory.FactoryError):
            factory.preflight(self.args)
        self.assertNotIn("received_token", self.data)


if __name__ == "__main__":
    unittest.main()
