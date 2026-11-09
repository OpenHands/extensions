"""Exercise both GitLab workers against local HTTP services, not network mocks."""

import importlib.util
import json
import os
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

SCRIPT = Path(__file__).resolve().parents[1] / "skills/gitlab-mr-reviewer/scripts/common.py"
spec = importlib.util.spec_from_file_location("gitlab_feedback", SCRIPT)
workflow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workflow)


class Service(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, data):
        output = json.dumps(data).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(output)))
        self.end_headers()
        self.wfile.write(output)

    def do_GET(self):
        url = urlsplit(self.path)
        path = url.path
        app = self.server.app
        base = "/api/v4/projects/group%2Fteam%2Fproject/"
        if path == "/api/settings":
            key = "test-llm-key" if self.headers.get("X-Expose-Secrets") == "plaintext" else "**********"
            return self.reply({"agent_settings": {"llm": {"model": "test-model", "api_key": key}}})
        if path == "/api/v1/app-conversations":
            return self.reply([{"execution_status": app["status"]}])
        if path.startswith("/api/conversations/"):
            if path.endswith("/agent_final_response"):
                if app["status"] in {"error", "stuck"}:
                    return self.send_error(404, "No final response")
                return self.reply({"response": app["response"]})
            return self.reply({"execution_status": app["status"]})
        if path == base + "merge_requests":
            return self.reply([app["mr"]] if app["mr"].get("labels") else [])
        if path == base + "merge_requests/7":
            return self.reply(app["mr"])
        if path == base + "merge_requests/7/diffs":
            return self.reply([{"old_path": "src/a.py", "new_path": "src/a.py", "diff": "+ changed"}])
        if path == base + "merge_requests/7/notes":
            return self.reply(app["mr_notes"])
        if path == base + "issues":
            return self.reply([app["issue"]] if app["issue"].get("labels") else [])
        if path == base + "issues/8":
            return self.reply(app["issue"])
        if path == base + "issues/8/resource_label_events":
            return self.reply(app["events"])
        if path == base + "issues/8/notes":
            return self.reply(app["issue_notes"])
        self.send_error(404, path)

    def do_POST(self):
        url = urlsplit(self.path)
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        app = self.server.app
        if url.path == "/api/conversations":
            app["prompts"].append(body)
            return self.reply({"id": f"conversation-{len(app['prompts'])}"})
        if url.path.endswith("/notes"):
            key = "mr_notes" if "/merge_requests/" in url.path else "issue_notes"
            app[key].append(body)
            return self.reply(body)
        self.send_error(404, url.path)


class GitLabFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.environment = os.environ.copy()
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.environment)))
        os.environ["HOME"] = self.tmp.name
        os.environ.pop("OPENHANDS_CLOUD_API_URL", None)
        os.environ.pop("AUTOMATION_KV_TOKEN", None)
        os.environ.pop("AUTOMATION_API_URL", None)
        self.app = {
            "mr": {"iid": 7, "state": "opened", "labels": ["openhands-review"], "sha": "abc", "title": "Change"},
            "issue": {"iid": 8, "state": "opened", "labels": ["openhands-refine"], "title": "Story", "description": "As a user I want X"},
            "events": [{"id": 4, "action": "add", "label": {"name": "openhands-refine"}}],
            "mr_notes": [], "issue_notes": [{"body": "A human clarifies X", "system": False}],
            "prompts": [], "status": "running", "response": "## Open questions\nWhat is X?",
        }
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Service)
        self.server.app = self.app
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        os.environ["AGENT_SERVER_URL"] = self.url
        self.api = workflow.GitLab(self.url + "/api/v4", "private-token")
        self.project = "group/team/project"

    def poll(self, mode):
        label = "openhands-review" if mode == "review" else "openhands-refine"
        workflow.process_project(self.api, self.project, mode, {"trigger_label": label})

    def test_review_exact_head_dedup_and_new_head(self):
        self.poll("review")
        self.assertEqual(len(self.app["prompts"]), 1)
        self.assertIn("src/a.py", self.app["prompts"][0]["initial_message"]["content"][0]["text"])
        self.assertNotIn("PRIVATE-TOKEN", json.dumps(self.app["prompts"]))
        self.poll("review")
        self.assertEqual(len(self.app["prompts"]), 1)
        self.app["status"] = "idle"
        self.app["response"] = "Review: src/a.py needs a test"
        self.poll("review")
        self.assertEqual(len(self.app["mr_notes"]), 1)
        self.assertIn("openhands-gitlab-review:7:abc", self.app["mr_notes"][0]["body"])
        self.poll("review")
        self.assertEqual(len(self.app["mr_notes"]), 1)
        self.app["mr"]["sha"] = "def"
        self.poll("review")
        self.assertEqual(len(self.app["prompts"]), 2)

    def test_refinement_label_event_and_reapplication(self):
        self.poll("refine")
        self.assertIn("A human clarifies X", self.app["prompts"][0]["initial_message"]["content"][0]["text"])
        self.app["status"] = "idle"
        self.poll("refine")
        self.assertEqual(len(self.app["issue_notes"]), 2)
        self.assertIn("openhands-gitlab-refine:8:4", self.app["issue_notes"][-1]["body"])
        self.poll("refine")
        self.assertEqual(len(self.app["prompts"]), 1)
        self.app["events"].append({"id": 9, "action": "add", "label": {"name": "openhands-refine"}})
        self.poll("refine")
        self.assertEqual(len(self.app["prompts"]), 2)

    def test_local_conversations_use_unmasked_llm_key(self):
        self.poll("review")
        self.poll("refine")
        self.assertEqual(
            [body["agent"]["llm"]["api_key"] for body in self.app["prompts"]],
            ["test-llm-key", "test-llm-key"],
        )

    def test_project_path_and_invalid_config(self):
        self.assertEqual(workflow.project_path("https://gitlab.com/group/team/project.git/-/issues/8"), self.project)
        with self.assertRaises(ValueError):
            workflow.project_path("project")
        with self.assertRaises(ValueError):
            workflow.project_path("https://gitlab.com/group/project?evil=1")

    def test_no_draft_review_or_unlabelled_refinement(self):
        self.app["mr"]["draft"] = True
        self.poll("review")
        self.assertEqual(self.app["prompts"], [])
        self.app["issue"]["labels"] = []
        self.poll("refine")
        self.assertEqual(self.app["prompts"], [])

    def test_missing_answer_retries_and_publication_recovers_from_lost_state(self):
        self.poll("refine")
        self.app["status"] = "idle"
        self.app["response"] = ""
        self.poll("refine")
        self.assertEqual(len(self.app["issue_notes"]), 1)
        self.poll("refine")
        self.assertEqual(len(self.app["prompts"]), 2)
        self.app["response"] = "## Recommendations\nClarify X"
        self.poll("refine")
        state = workflow.State("refine", self.project)
        state.write({})
        self.poll("refine")
        self.assertEqual(len(self.app["prompts"]), 2)
        self.assertEqual(len(self.app["issue_notes"]), 2)

    def test_failed_conversations_publish_one_failure_after_two_attempts(self):
        for mode, notes in (("review", "mr_notes"), ("refine", "issue_notes")):
            with self.subTest(mode=mode):
                initial_notes = len(self.app[notes])
                initial_prompts = len(self.app["prompts"])
                self.app["status"] = "error"
                self.poll(mode)
                self.poll(mode)
                self.assertEqual(len(self.app["prompts"]), initial_prompts + 1)
                self.assertEqual(len(self.app[notes]), initial_notes)
                self.poll(mode)
                self.app["status"] = "stuck"
                self.poll(mode)
                self.assertEqual(len(self.app[notes]), initial_notes + 1)
                self.assertIn("could not complete", self.app[notes][-1]["body"])
                self.assertIn("after 2 attempts", self.app[notes][-1]["body"])
                self.poll(mode)
                self.assertEqual(len(self.app[notes]), initial_notes + 1)
                self.assertEqual(len(self.app["prompts"]), initial_prompts + 2)
                key = "7:abc" if mode == "review" else "8:4"
                state = workflow.State(mode, self.project)
                self.assertEqual(state.read()[key]["status"], "done")
                state.write({})
                self.poll(mode)
                self.assertEqual(len(self.app["prompts"]), initial_prompts + 2)

    def test_expired_claim_and_pending_conversation_consume_attempts(self):
        for mode, key, notes in (("review", "7:abc", "mr_notes"), ("refine", "8:4", "issue_notes")):
            for status, age in (("claimed", 901), ("pending", 7201)):
                with self.subTest(mode=mode, status=status):
                    state = workflow.State(mode, self.project)
                    record = {"status": status, "created_at": time.time() - age, "attempts": 1}
                    if status == "pending":
                        record["conversation_id"] = "expired-conversation"
                    state.write({key: record})
                    self.app["status"] = "running"
                    self.poll(mode)
                    self.poll(mode)
                    self.assertEqual(state.read()[key]["attempts"], 2)
                    self.app["status"] = "error"
                    self.poll(mode)
                    self.assertEqual(state.read()[key]["status"], "done")
                    self.assertIn("could not complete", self.app[notes][-1]["body"])
                    self.app[notes].pop()

                    record["attempts"] = 2
                    state.write({key: record})
                    self.app["status"] = "running"
                    self.poll(mode)
                    self.assertEqual(state.read()[key]["status"], "done")
                    self.assertIn("could not complete", self.app[notes][-1]["body"])
                    self.app[notes].pop()

    def test_cloud_failed_conversation_without_final_events(self):
        os.environ.pop("AGENT_SERVER_URL")
        os.environ["OPENHANDS_CLOUD_API_URL"] = self.url
        for status in ("error", "stuck"):
            self.app["status"] = status
            self.assertEqual(workflow._conversation_result("conversation-1"), (status, ""))

    def test_empty_responses_stop_after_retry(self):
        self.app["status"] = "finished"
        self.app["response"] = "   "
        self.poll("review")
        self.poll("review")
        self.poll("review")
        self.poll("review")
        self.assertEqual(len(self.app["prompts"]), 2)
        self.assertEqual(len(self.app["mr_notes"]), 1)
        self.assertIn("could not complete", self.app["mr_notes"][0]["body"])

    def test_local_automation_state_is_isolated(self):
        os.environ["AUTOMATION_EVENT_PAYLOAD"] = json.dumps({"automation_id": "one"})
        first = workflow.State("refine", self.project)
        first.write({"8:4": {"status": "done"}})
        os.environ["AUTOMATION_EVENT_PAYLOAD"] = json.dumps({"automation_id": "two"})
        self.assertEqual(workflow.State("refine", self.project).read(), {})
        self.assertNotEqual(first.key, workflow.State("refine", self.project).key)



if __name__ == "__main__":
    unittest.main()
