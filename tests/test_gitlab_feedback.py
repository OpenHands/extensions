"""Exercise both GitLab workers against local HTTP services, not network mocks."""

import importlib.util
import io
import json
import os
import tarfile
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


def archive(files):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as tar:
        for name, content in files.items():
            data = content.encode()
            member = tarfile.TarInfo(name)
            member.size = len(data)
            tar.addfile(member, io.BytesIO(data))
    return output.getvalue()


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
        if path.startswith("/v1/kv/"):
            if path not in app["kv"]:
                return self.send_error(404)
            return self.reply({"value": app["kv"][path]})
        if path == "/api/settings":
            key = "test-llm-key" if self.headers.get("X-Expose-Secrets") == "plaintext" else "**********"
            return self.reply({"agent_settings": {"llm": {"model": "test-model", "api_key": key}}})
        if path == "/api/v1/app-conversations":
            return self.reply([{"execution_status": app["status"]}])
        if path.startswith("/api/v1/conversation/") and path.endswith("/events/search"):
            return self.reply({"items": [{"source": "agent", "kind": "ActionEvent", "tool_name": "finish",
                                          "action": {"message": app["response"]}}]})
        if path.startswith("/api/conversations/"):
            if path.endswith("/agent_final_response"):
                if app["status"] in {"error", "stuck"}:
                    return self.send_error(404, "No final response")
                return self.reply({"response": app["response"]})
            return self.reply({"execution_status": app["status"]})
        if path == base[:-1]:
            return self.reply({"default_branch": "main", "http_url_to_repo": "https://gitlab.example.com/group/team/project.git"})
        if path == base + "merge_requests":
            app["list_requests"] += 1
            return self.reply([app["mr"]] if app["mr"].get("labels") else [])
        if path == base + "merge_requests/7":
            return self.reply(app["mr"])
        if path == base + "merge_requests/7/diffs":
            return self.reply([{"old_path": "src/a.py", "new_path": "src/a.py", "diff": "+ changed"}])
        if (path in {base + "repository/archive.tar.gz", "/api/v4/projects/42/repository/archive.tar.gz"}
                and url.query == f"sha={app['mr']['sha']}"):
            app["archive_paths"].append(path)
            data = app["archive"]
            self.send_response(200)
            self.send_header("Content-Type", "application/gzip")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            return self.wfile.write(data)
        if path == base + "merge_requests/7/notes":
            return self.reply(app["mr_notes"])
        if path == base + "issues":
            app["list_requests"] += 1
            return self.reply([app["issue"]] if app["issue"].get("labels") else [])
        if path == base + "issues/8":
            return self.reply(app["issue"])
        if path == base + "issues/8/resource_label_events":
            return self.reply(app["events"])
        if path == base + "issues/8/notes":
            return self.reply(app["issue_notes"])
        self.send_error(404, path)

    def do_PUT(self):
        self.server.app["kv"][urlsplit(self.path).path] = json.loads(
            self.rfile.read(int(self.headers["Content-Length"]))
        )
        return self.reply({})

    def do_POST(self):
        url = urlsplit(self.path)
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        app = self.server.app
        if url.path in {"/api/conversations", "/api/v1/app-conversations"}:
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
        os.environ["WORKSPACE_BASE"] = self.tmp.name
        os.environ.pop("OPENHANDS_CLOUD_API_URL", None)
        os.environ.pop("AUTOMATION_KV_TOKEN", None)
        os.environ.pop("AUTOMATION_API_URL", None)
        self.app = {
            "mr": {"iid": 7, "state": "opened", "labels": ["openhands-review"], "sha": "abc", "title": "Change"},
            "issue": {"iid": 8, "state": "opened", "labels": ["openhands-refine"], "title": "Story", "description": "As a user I want X"},
            "events": [{"id": 4, "action": "add", "label": {"name": "openhands-refine"}}],
            "mr_notes": [], "issue_notes": [{"body": "A human clarifies X", "system": False}],
            "prompts": [], "kv": {}, "archive_paths": [], "list_requests": 0,
            "status": "running", "response": "## Open questions\nWhat is X?",
            "archive": archive({"project-abc/src/a.py": "original context\nchanged\n",
                                "project-abc/tests/test_a.py": "assert True\n"}),
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

    def test_review_checks_out_exact_head_and_removes_it_after_completion(self):
        self.poll("review")
        body = self.app["prompts"][0]
        checkout = Path(body["workspace"]["working_dir"])
        self.assertEqual((checkout / "src/a.py").read_text(), "original context\nchanged\n")
        self.assertEqual((checkout / "tests/test_a.py").read_text(), "assert True\n")
        self.assertIn("abc", body["initial_message"]["content"][0]["text"])
        self.assertIn("focused tests", body["initial_message"]["content"][0]["text"])
        self.poll("review")
        self.assertTrue(checkout.exists())
        self.app["status"] = "idle"
        self.app["response"] = "Reviewed source and tests"
        self.poll("review")
        self.assertFalse(checkout.exists())
        self.assertEqual(len(self.app["mr_notes"]), 1)

    def test_head_change_reaps_old_checkout_without_publishing_old_review(self):
        self.poll("review")
        first = Path(self.app["prompts"][0]["workspace"]["working_dir"])
        self.app["mr"]["sha"] = "def"
        self.poll("review")
        self.assertTrue(first.exists())
        second = Path(self.app["prompts"][1]["workspace"]["working_dir"])
        self.app["status"] = "idle"
        self.app["response"] = "Current head review"
        self.poll("review")
        self.assertFalse(first.exists())
        self.assertFalse(second.exists())
        self.assertEqual(len(self.app["mr_notes"]), 1)
        self.assertIn("review:7:def", self.app["mr_notes"][0]["body"])

    def test_fork_review_fetches_source_project_not_target(self):
        self.app["mr"]["source_project_id"] = 42
        self.poll("review")
        self.assertEqual(self.app["archive_paths"], ["/api/v4/projects/42/repository/archive.tar.gz"])
        self.assertEqual(len(self.app["prompts"]), 1)

    def test_invalid_archive_never_starts_a_review_or_escapes_checkout(self):
        self.app["archive"] = archive({"project-abc/../escape.txt": "bad"})
        with self.assertRaises(ValueError):
            self.poll("review")
        self.assertFalse((Path(self.tmp.name) / "escape.txt").exists())
        self.assertFalse(self.app["prompts"])

    def test_cloud_reviewer_must_fetch_the_exact_head_itself(self):
        os.environ.pop("AGENT_SERVER_URL")
        os.environ["OPENHANDS_CLOUD_API_URL"] = self.url
        os.environ["AUTOMATION_API_URL"] = self.url
        os.environ["AUTOMATION_KV_TOKEN"] = "test-kv-token"
        self.poll("review")
        body = self.app["prompts"][0]
        prompt = body["initial_message"]["content"][0]["text"]
        self.assertNotIn("workspace", body)
        self.assertIn("GITLAB_TOKEN", prompt)
        self.assertIn("${GITLAB_TOKEN:-$gitlab_token}", prompt)
        self.assertIn("abc", prompt)
        self.assertIn("git fetch", prompt)
        self.assertIn("git checkout", prompt)
        self.assertIn("focused tests", prompt)

    def test_timed_out_review_keeps_running_checkout_until_it_stops(self):
        self.poll("review")
        first = Path(self.app["prompts"][0]["workspace"]["working_dir"])
        state = workflow.State("review", self.project)
        tasks = state.read()
        tasks["7:abc"]["created_at"] = time.time() - 7201
        state.write(tasks)
        self.poll("review")
        self.poll("review")
        second = Path(self.app["prompts"][1]["workspace"]["working_dir"])
        self.assertNotEqual(first, second)
        self.assertTrue(first.exists())
        self.assertTrue(second.exists())
        self.app["status"] = "idle"
        self.app["response"] = "Review: no findings"
        self.poll("review")
        self.assertFalse(first.exists())
        self.assertFalse(second.exists())

    def test_cloud_review_requires_verified_head_marker_before_publication(self):
        os.environ.pop("AGENT_SERVER_URL")
        os.environ["OPENHANDS_CLOUD_API_URL"] = self.url
        os.environ["AUTOMATION_API_URL"] = self.url
        os.environ["AUTOMATION_KV_TOKEN"] = "test-kv-token"
        self.poll("review")
        self.app["status"] = "idle"
        self.app["response"] = "Findings from a diff-only review"
        self.poll("review")
        self.assertFalse(self.app["mr_notes"])
        self.poll("review")
        self.app["response"] = "Reviewed the exact checkout\nREVIEWED_HEAD:abc"
        self.poll("review")
        self.assertEqual(len(self.app["mr_notes"]), 1)
        self.assertIn("Reviewed the exact checkout", self.app["mr_notes"][0]["body"])
        self.assertNotIn("REVIEWED_HEAD", self.app["mr_notes"][0]["body"])
        self.assertIn("openhands-gitlab-review:7:abc", self.app["mr_notes"][0]["body"])

    def test_cloud_failed_checkout_does_not_publish_review_findings(self):
        os.environ.pop("AGENT_SERVER_URL")
        os.environ["OPENHANDS_CLOUD_API_URL"] = self.url
        os.environ["AUTOMATION_API_URL"] = self.url
        os.environ["AUTOMATION_KV_TOKEN"] = "test-kv-token"
        self.poll("review")
        self.app["status"] = "idle"
        self.app["response"] = "REVIEW_CHECKOUT_FAILED"
        self.poll("review")
        self.assertEqual(self.app["mr_notes"], [])
        self.assertEqual(workflow.State("review", self.project).read()["7:abc"]["status"], "retry")

    def event(self, *, project=None, iid=7, action="open", kind="merge_request"):
        return {"event": {"source": "gitlab", "payload": {
            "object_kind": kind, "project": {"path_with_namespace": project or self.project},
            "object_attributes": {"iid": iid, "action": action},
            "changes": {"labels": {"previous": [], "current": [{"title": "openhands"}]}}
            if kind == "issue" and action == "update" else {},
        }}}

    def test_event_template_requires_pre_registered_signed_source(self):
        manifest = json.loads((SCRIPT.parents[3] / "automations/catalog/gitlab-mr-reviewer/manifest.json").read_text())
        event = manifest["setup"]["form"]["triggers"]["event"]
        self.assertEqual(event["source"]["default"], "gitlab")
        self.assertEqual(event["source"]["type"], "event-source")
        self.assertEqual(event["on"]["default"], "merge_request")
        self.assertIn("object_attributes.action", manifest["setup"]["filter"])
        self.assertIn("cron", manifest["setup"]["form"]["triggers"])

    def test_issue_templates_offer_signed_event_and_scheduled_variants(self):
        root = SCRIPT.parents[3] / "automations/catalog"
        for name in ("gitlab-prd-refiner", "gitlab-issue-to-mr"):
            manifest = json.loads((root / name / "manifest.json").read_text())
            triggers = manifest["setup"]["form"]["triggers"]
            self.assertEqual(set(triggers), {"cron", "event"})
            self.assertEqual(triggers["event"]["source"]["type"], "event-source")
            self.assertEqual(triggers["event"]["on"]["default"], "issue")
            self.assertIn("object_kind == 'issue'", manifest["setup"]["filter"])
            self.assertIn("changes.labels != `null`", manifest["setup"]["filter"])
            self.assertEqual(manifest["version"], manifest["setup"]["bundle"]["version"])

    def test_event_reviews_only_targeted_mr_and_waits_for_note(self):
        self.app["status"] = "idle"
        self.app["response"] = "Review: src/a.py needs a test"
        config = {"trigger_label": "openhands-review"}
        self.assertTrue(workflow.process_event(self.api, [self.project], config, self.event()))
        self.assertEqual(self.app["list_requests"], 0)
        self.assertEqual(len(self.app["prompts"]), 1)
        self.assertEqual(len(self.app["mr_notes"]), 1)
        self.assertIn("openhands-gitlab-review:7:abc", self.app["mr_notes"][0]["body"])
        self.assertTrue(workflow.process_event(self.api, [self.project], config, self.event()))
        self.assertEqual(len(self.app["prompts"]), 1)
        self.assertEqual(len(self.app["mr_notes"]), 1)

    def test_event_does_not_complete_before_conversation_finishes(self):
        def finish_review():
            time.sleep(0.1)
            self.app["status"] = "idle"
            self.app["response"] = "Completed after event delivery"

        thread = threading.Thread(target=finish_review)
        thread.start()
        self.addCleanup(thread.join)
        self.assertTrue(workflow.process_event(
            self.api, [self.project], {"trigger_label": "openhands-review"}, self.event()))
        self.assertEqual(len(self.app["mr_notes"]), 1)
        self.assertIn("Completed after event delivery", self.app["mr_notes"][0]["body"])
        self.assertEqual(self.app["list_requests"], 0)

    def test_event_rejects_other_projects_actions_and_unlabelled_mrs(self):
        config = {"trigger_label": "openhands-review"}
        for event in (self.event(project="other/repo"), self.event(action="merge"),
                      self.event(iid=8)):
            self.assertFalse(workflow.process_event(self.api, [self.project], config, event))
        self.app["mr"]["labels"] = []
        self.assertFalse(workflow.process_event(self.api, [self.project], config, self.event()))
        self.assertEqual(self.app["prompts"], [])
        self.assertEqual(self.app["list_requests"], 0)

    def test_refinement_event_only_targets_labelled_issue_and_waits_for_note(self):
        payload = self.event(iid=8, kind="issue", action="update")
        config = {"trigger_label": "openhands-refine"}
        self.app["status"] = "idle"
        self.app["response"] = "Open questions: What is X?"
        self.assertTrue(workflow.process_event(self.api, [self.project], config, payload, mode="refine"))
        self.assertEqual(self.app["list_requests"], 0)
        self.assertEqual(len(self.app["issue_notes"]), 2)
        self.assertIn("openhands-gitlab-refine:8:4", self.app["issue_notes"][1]["body"])
        self.assertTrue(workflow.process_event(self.api, [self.project], config, payload, mode="refine"))
        self.assertEqual(len(self.app["prompts"]), 1)
        self.assertFalse(workflow.process_event(self.api, [self.project], config,
                                                self.event(iid=8, kind="merge_request"), mode="refine"))
        unrelated_edit = self.event(iid=8, kind="issue", action="update")
        unrelated_edit["event"]["payload"]["changes"] = {"title": {"current": "Edited"}}
        self.assertFalse(workflow.process_event(self.api, [self.project], config,
                                                unrelated_edit, mode="refine"))

    def test_implementor_event_targets_one_issue_without_backlog_scan(self):
        os.environ["AUTOMATION_API_URL"] = self.url
        os.environ["AUTOMATION_KV_TOKEN"] = "test-token"
        os.environ["AUTOMATION_EVENT_PAYLOAD"] = json.dumps(self.event(iid=8, kind="issue", action="update"))
        script = SCRIPT.parents[2] / "gitlab-issue-to-mr/scripts/main.py"
        spec = importlib.util.spec_from_file_location("gitlab_issue_to_mr_event_test", script)
        implementor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(implementor)
        implementor.GITLAB_API_URL = self.url + "/api/v4"
        implementor.PROJECTS = [self.project]
        implementor.TRIGGER_LABEL = "openhands"
        self.app["issue"]["labels"] = []
        self.assertEqual(implementor._event_target(), (self.project, 8))
        self.assertIsNone(implementor._process_project(
            self.project, "private-token", self.url, "session-key", self.url, issue_iid=8))
        self.assertEqual(self.app["list_requests"], 0)
        os.environ["AUTOMATION_EVENT_PAYLOAD"] = json.dumps(self.event(iid=8, kind="merge_request"))
        self.assertIsNone(implementor._event_target())
        unrelated_edit = self.event(iid=8, kind="issue", action="update")
        unrelated_edit["event"]["payload"]["changes"] = {"title": {"current": "Edited"}}
        self.assertIsNone(implementor._event_target(unrelated_edit))

    def test_implementor_event_finalizes_active_conversation_without_next_poll(self):
        os.environ["AUTOMATION_API_URL"] = self.url
        os.environ["AUTOMATION_KV_TOKEN"] = "test-token"
        script = SCRIPT.parents[2] / "gitlab-issue-to-mr/scripts/main.py"
        spec = importlib.util.spec_from_file_location("gitlab_issue_to_mr_event_completion", script)
        implementor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(implementor)
        implementor.GITLAB_API_URL = self.url + "/api/v4"
        implementor._CLOUD_API_URL = self.url
        implementor.IS_CLOUD = True
        implementor.TRIGGER_LABEL = "openhands-refine"
        self.app["issue"]["labels"] = ["openhands-refine"]
        self.app["mr"]["web_url"] = "https://gitlab.example.com/group/team/project/-/merge_requests/7"
        self.app["status"] = "idle"
        implementor.save_state(self.project, {"tasks": {"8:label:4": {
            "status": "active", "conversation_id": "conv-8", "issue_iid": 8,
            "branch": "openhands/issue-8", "last_activity": 0, "workspace_dir": None,
        }}})
        result = implementor._process_event_target(
            self.project, 8, "private-token", self.url, "session-key", self.url)
        self.assertEqual(result, "conv-8")
        self.assertEqual(implementor.load_state(self.project)["tasks"]["8:label:4"]["status"], "closed")
        self.assertEqual(len(self.app["issue_notes"]), 2)
        self.assertIn("OpenHands opened a merge request", self.app["issue_notes"][1]["body"])
        self.assertEqual(self.app["list_requests"], 1)

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
