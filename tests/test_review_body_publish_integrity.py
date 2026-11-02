"""Real serialization and publication paths against a local HTTP boundary."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/github-pr-reviewer/scripts"
if not SCRIPTS.exists():
    SCRIPTS = ROOT / "plugins/github-pr-reviewer-events/scripts"
SPEC = importlib.util.spec_from_file_location("publish_review", SCRIPTS / "publish_review.py")
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


def payload(**changes):
    return {"commit_id": "head", "event": "APPROVE", "body": (
        publisher.DISCLOSURE + "\n\nNo material issues found.\n\n✅ APPROVED"), **changes}


class ReviewBoundary:
    def __init__(self):
        self.reviews, self.posts, self.reads, self.comments = [], [], [], []
        self.head, self.author, self.mode = "head", "human", "normal"
        boundary = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def reply(self, value, code=200):
                raw = json.dumps(value).encode()
                self.send_response(code)
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self):
                path = urlsplit(self.path).path
                boundary.reads.append(path)
                if path == "/user":
                    self.reply({"login": "bot"})
                elif path.endswith("/reviews"):
                    self.reply(boundary.reviews)
                elif path.endswith("/comments"):
                    self.reply(boundary.comments)
                else:
                    self.reply({"head": {"sha": boundary.head}, "state": "open",
                                "user": {"login": boundary.author}})

            def do_POST(self):
                incoming = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                boundary.posts.append(incoming)
                if boundary.mode == "reject":
                    self.reply({"message": "Invalid inline position"}, 422)
                    return
                review = {**incoming, "id": 1, "state": "APPROVED" if incoming["event"] == "APPROVE" else "COMMENTED",
                          "user": {"login": "bot"}, "submitted_at": "2026-01-02T00:00:00Z"}
                if boundary.mode == "empty":
                    review["body"] = ""
                elif boundary.mode == "wrong_head":
                    review["commit_id"] = "other"
                elif boundary.mode == "wrong_author":
                    review["user"] = {"login": "other"}
                elif boundary.mode == "pending":
                    review["state"] = "PENDING"
                boundary.reviews.append(review)
                if boundary.mode == "lost_response":
                    self.close_connection = True
                    return
                self.reply(review)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.api = publisher.GitHub("local-test-only", f"http://127.0.0.1:{self.server.server_port}")

    def close(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()


class PublishIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.journal = Path(self.tmp.name) / "journal"
        self.boundary = ReviewBoundary()
        self.addCleanup(self.boundary.close)

    def publish(self, request=None, head="head"):
        return publisher.publish(self.boundary.api, "Owner/Repo", 1, head,
                                 payload() if request is None else request, self.journal)

    def test_invalid_payloads_do_not_even_read_github(self):
        for request in [None, {}, payload(body=""), payload(body=" \n"), payload(body=publisher.DISCLOSURE + "\n\n✅ APPROVED"),
                        payload(body="Assessment only"), payload(commit_id="stale"), payload(event="REQUEST_CHANGES"),
                        payload(comments=[{"body": "missing location"}]), payload(comments="bad"),
                        payload(body=publisher.DISCLOSURE + "\n\nBug found\n\n🔄 CHANGES REQUESTED")]:
            with self.subTest(request=request):
                with self.assertRaises(ValueError):
                    publisher.publish(self.boundary.api, "Owner/Repo", 1, "head", request, self.journal)
        self.assertEqual(self.boundary.posts, [])
        self.assertEqual(self.boundary.reads, [])

    def test_exact_body_and_inline_findings_are_serialized_once(self):
        request = payload(event="COMMENT", comments=[{"path": "a.py", "line": 2, "side": "RIGHT", "body": "Demonstrated failure"}])
        request["body"] = publisher.DISCLOSURE + "\n\nQuotes: \"x\", backticks `x`, $HOME, Unicode ✓.\n\n🔄 CHANGES REQUESTED"
        self.assertEqual(self.publish(request)["body"], request["body"])
        self.assertEqual(self.boundary.posts, [request])
        with self.assertRaises(RuntimeError):
            self.publish(request)
        self.assertEqual(len(self.boundary.posts), 1)

    def test_scope_stop_and_self_approval_preserve_verdicts(self):
        self.boundary.author = "BOT"
        self.publish()
        self.assertEqual(self.boundary.posts[0]["event"], "COMMENT")
        self.assertTrue(self.boundary.posts[0]["body"].endswith("✅ APPROVED"))
        self.boundary.head = "new-head"
        self.publish(payload(commit_id="new-head", event="COMMENT", body=publisher.DISCLOSURE + "\n\nNeeds an ownership decision.\n\n🛑 MAINTAINER DECISION REQUIRED"), head="new-head")
        self.assertEqual(len(self.boundary.posts), 2)

    def test_moved_head_prevents_post(self):
        self.boundary.head = "moved"
        with self.assertRaisesRegex(RuntimeError, "head moved"):
            self.publish()
        self.assertFalse(self.boundary.posts)

    def test_accepted_invalid_or_lost_response_cannot_be_reposted(self):
        for mode in ["empty", "wrong_head", "wrong_author", "pending", "lost_response"]:
            with self.subTest(mode=mode):
                self.boundary.mode = mode
                with self.assertRaises(Exception):
                    self.publish()
                self.assertEqual(len(self.boundary.posts), 1)
                # Simulate a stale or eventually-consistent review listing.
                self.boundary.reviews.clear()
                self.boundary.mode = "normal"
                with self.assertRaisesRegex(RuntimeError, "do not retry"):
                    self.publish()
                self.assertEqual(len(self.boundary.posts), 1)
                self.boundary.posts.clear()
                for record in self.journal.glob("*.json"):
                    record.unlink()

    def test_existing_empty_review_is_not_permission_to_repair_with_another(self):
        self.boundary.reviews.append({"commit_id": "head", "state": "APPROVED", "body": "", "user": {"login": "bot"}})
        self.boundary.comments.append({"created_at": "2026-02-01T00:00:00Z", "user": {"login": "human"}})
        with self.assertRaisesRegex(RuntimeError, "operator repair"):
            self.publish()
        self.assertFalse(self.boundary.posts)

    def test_explicit_rejection_allows_corrected_request(self):
        self.boundary.mode = "reject"
        with self.assertRaises(Exception):
            self.publish(payload(comments=[{"path": "a.py", "line": 2, "side": "RIGHT", "body": "Finding"}]))
        self.boundary.mode = "normal"
        self.publish(payload(event="COMMENT"))
        self.assertEqual(len(self.boundary.reviews), 1)
        self.assertEqual(len(self.boundary.posts), 2)

    def test_later_clarification_allows_new_valid_review_with_provenance(self):
        self.publish()
        self.boundary.reviews[0]["body"] += "\n\nLLM profile: `reviewer` · Model: `model`"
        self.boundary.comments.append({"created_at": "2026-02-01T00:00:00Z", "user": {"login": "human"}})
        self.publish(payload(event="COMMENT"))
        self.assertEqual(len(self.boundary.posts), 2)

    def test_same_sandbox_concurrency_does_not_duplicate(self):
        errors = []
        def run():
            try:
                self.publish()
            except RuntimeError as exc:
                errors.append(exc)
        threads = [threading.Thread(target=run) for _ in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(self.boundary.posts), 1)
        self.assertEqual(len(errors), 3)

    def test_missing_or_malformed_file_never_prints_success(self):
        path = Path(self.tmp.name) / "payload.json"
        for content in [None, "{", '{"body":""}']:
            if content is not None:
                path.write_text(content)
            result = subprocess.run([sys.executable, str(SCRIPTS / "publish_review.py"), "Owner/Repo", "1", "head", str(path)],
                                    env={**os.environ, "GH_TOKEN": "local-test-only"}, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("GITHUB_REVIEW_POSTED", result.stdout)
        self.assertFalse(self.boundary.posts)

    def test_prompt_embeds_exact_executable_and_bundle_includes_it(self):
        sys.path.insert(0, str(SCRIPTS))
        self.addCleanup(sys.path.remove, str(SCRIPTS))
        spec = importlib.util.spec_from_file_location("review_prompt", SCRIPTS / "main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        prompt = module._build_review_prompt("Owner/Repo", {"number": 1}, "head", {}, github_token_secret="REVIEW_TOKEN")
        self.assertIn((SCRIPTS / "publish_review.py").read_text(), prompt)
        self.assertIn("Do not shorten or bypass its guards", prompt)
        self.assertIn("GH_TOKEN=${REVIEW_TOKEN} python3 - Owner/Repo 1 head", prompt)
        command = prompt.split("```sh\n", 1)[1].split("\n```", 1)[0]
        # Exercise the supplied heredoc unchanged; a missing request fails closed.
        command = command.replace("/tmp/openhands-review.json", str(Path(self.tmp.name) / "absent.json"))
        result = subprocess.run(["sh", "-c", command], capture_output=True, text=True,
                                env={**os.environ, "REVIEW_TOKEN": "local-test-only"})
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("GITHUB_REVIEW_POSTED", result.stdout)
        manifest = ROOT / "automations/catalog/github-pr-reviewer/manifest.json"
        if manifest.exists():
            self.assertIn("publish_review.py", json.loads(manifest.read_text())["setup"]["bundle"]["files"])


if __name__ == "__main__":
    unittest.main()
