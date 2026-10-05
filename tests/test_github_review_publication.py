"""Real publisher/lease paths; only external KV, GitHub and SDK are simulated."""

import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from agent_conversation import ReviewCoordination

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("review_publication", ROOT / "skills/github-pr-reviewer/scripts/publication.py")
publication = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publication)


def artifact(**changes):
    return json.dumps({"head_sha": "abc", "code_assessment": "clean", "merge_readiness": "ready",
                       "summary": "No material defects found.", "findings": [], "evidence": ["pytest: 10 passed"], **changes})


@pytest.mark.parametrize("assessment,ready,findings,event,footer", [
    ("clean", "ready", [], "APPROVE", "✅ APPROVED"),
    ("clean", "blocked", [], "COMMENT", "⏸ INCONCLUSIVE"),
    ("material_findings", "blocked", ["file.py:2 crashes"], "COMMENT", "🔄 CHANGES REQUESTED"),
    ("inconclusive", "unknown", [], "COMMENT", "⏸ INCONCLUSIVE"),
])
def test_derived_outcome(assessment, ready, findings, event, footer):
    payload = publication.review_payload(artifact(code_assessment=assessment, merge_readiness=ready, findings=findings), "abc", False, "marker")
    assert payload["event"] == event
    assert payload["body"].endswith(footer)
    assert publication.review_payload(artifact(), "abc", True, "marker")["event"] == "COMMENT"


@pytest.mark.parametrize("changes", [
    {"findings": ["bug"]}, {"code_assessment": "material_findings"},
    {"code_assessment": "inconclusive"}, {"evidence": []}, {"head_sha": "stale"},
    {"event": "APPROVE"}, {"summary": "✅ APPROVED"}, {"findings": "not a list"},
])
def test_reject_contradictions(changes):
    with pytest.raises(ValueError):
        publication.review_payload(artifact(**changes), "abc", False, "marker")


@pytest.fixture
def kv(monkeypatch):
    # HTTP boundary implements the documented namespace-global CAS contract.
    state, lock = {"version": 0, "values": {}}, threading.Lock()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def handle_request(self):
            from urllib.parse import parse_qs, urlsplit
            query = parse_qs(urlsplit(self.path).query)
            key = urlsplit(self.path).path.rsplit("/", 1)[-1]
            assert query["automation_id"] == ["11111111-1111-1111-1111-111111111111"]
            assert self.headers["X-Session-API-Key"] == "local-test-only"
            with lock:
                value = state["values"].get(key)
                code = 200
                if self.command == "PUT":
                    incoming = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                    if ("nx" in query and value is not None) or ("if_version" in query and int(query["if_version"][0]) != state["version"]):
                        code = 409
                    else:
                        state["values"][key] = value = incoming
                        state["version"] += 1
                elif value is None:
                    code = 404
                body = json.dumps({"value": value, "version": state["version"]}).encode()
                self.send_response(code)
                self.end_headers()
                self.wfile.write(body)

        do_GET = do_PUT = handle_request

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setenv("AUTOMATION_API_URL", f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setenv("REVIEW_COORDINATION_API_KEY", "local-test-only")
    monkeypatch.setenv("REVIEW_COORDINATION_AUTOMATION_ID", "11111111-1111-1111-1111-111111111111")
    yield state
    server.shutdown()
    thread.join()
    server.server_close()


def test_atomic_claim_and_fencing(kv):
    store = ReviewCoordination()
    barrier = threading.Barrier(8)
    leases = []
    def claim():
        barrier.wait()
        leases.append(store.claim("common-subject"))
    threads = [threading.Thread(target=claim) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    winners = [lease for lease in leases if lease]
    assert len(winners) == 1
    old = winners[0]
    old.release()
    new = store.claim("common-subject")
    with pytest.raises(RuntimeError, match="lease lost"):
        old.save(status="posting")
    new.release()


@pytest.fixture
def runner(kv):
    pr = {"number": 3, "head": {"sha": "abc"}, "user": {"login": "human"}, "state": "open"}
    reviews, starts = [], []
    run = SimpleNamespace(repository="Owner/Repo", github_login="bot", token_name="WRITE_TOKEN",
                          config={"review_profile_read_only": True, "review_read_token_secret": "READ_TOKEN"})
    run.dispatcher = SimpleNamespace(start_review_work=lambda *args: starts.append(args), review_snapshot=lambda cid: ("finished", artifact()))
    def gh(method, path, body=None):
        if method == "GET":
            return pr
        review = {**body, "id": len(reviews) + 1, "state": "APPROVED" if body["event"] == "APPROVE" else "COMMENTED", "user": {"login": "bot"}}
        reviews.append(review)
        return review
    run.latest_label_event = lambda number: {"id": 1}
    run._finish_completed_review = lambda *args: True
    run.gh = gh
    run.gh_pages = lambda path: reviews
    return run, pr, reviews, starts


def test_async_publish_and_stop(runner):
    run, pr, reviews, starts = runner
    publisher = publication.StructuredReviews(run)
    assert publisher.advance(pr, start=True)["disposition"] == "created"
    assert not reviews
    assert publisher.advance(pr)["disposition"] == "published"
    for _ in range(3):
        assert publisher.advance(pr, start=True)["disposition"] == "deduplicated"
    assert len(reviews) == len(starts) == 1


def test_uncertain_post_reconciles_without_retry(runner, kv):
    run, pr, reviews, starts = runner
    publisher = publication.StructuredReviews(run)
    publisher.advance(pr, start=True)
    original = run.gh
    def uncertain(method, path, body=None):
        result = original(method, path, body)
        if method == "POST":
            raise TimeoutError("response lost")
        return result
    run.gh = uncertain
    with pytest.raises(TimeoutError):
        publisher.advance(pr)
    run.gh_pages = lambda path: []
    assert publisher.advance(pr)["disposition"] == "in_progress"
    assert len(reviews) == 1
    run.gh_pages = lambda path: reviews
    assert publisher.advance(pr)["disposition"] == "deduplicated"
    assert next(iter(kv["values"].values()))["receipt"]["id"] == 1
    assert len(reviews) == 1


def test_stale_head_and_invalid_artifact_never_post(runner):
    run, pr, reviews, starts = runner
    publisher = publication.StructuredReviews(run)
    publisher.advance(pr, start=True)
    pr["head"]["sha"] = "new"
    publisher.advance(pr)
    assert not reviews
    publisher.advance(pr, start=True)
    with pytest.raises(ValueError, match="head"):
        publisher.advance(pr)
    assert not reviews


def test_active_work_blocks_new_generation(runner):
    run, pr, reviews, starts = runner
    publisher = publication.StructuredReviews(run)
    publisher.advance(pr, start=True)
    run.dispatcher.review_snapshot = lambda cid: ("running", "")
    assert publisher.advance(pr, "request:2", start=True)["disposition"] == "in_progress"
    assert len(starts) == 1


def test_generation_replay_does_not_republish(runner):
    run, pr, reviews, starts = runner
    publisher = publication.StructuredReviews(run)
    for generation in ("request:1", "request:2"):
        publisher.advance(pr, generation, start=True)
        publisher.advance(pr)
    assert publisher.advance(pr, "request:1", start=True)["disposition"] == "deduplicated"
    assert len(reviews) == len(starts) == 2


def test_untracked_scan_does_not_create_state(runner, kv):
    run, pr, _, _ = runner
    publication.StructuredReviews(run).advance(pr)
    assert not kv["values"]


@pytest.mark.parametrize("event", [None, {"repository": {"full_name": "elsewhere/repo"}}])
def test_worker_reconciles_before_event_or_scan_selection(runner, tmp_path, monkeypatch, event):
    from github_automation_helpers import worker

    run, pr, reviews, starts = runner
    publisher = publication.StructuredReviews(run)
    publisher.advance(pr, start=True)
    module = worker("github-pr-reviewer", tmp_path, monkeypatch)
    actual = object.__new__(module.PullRequestReviewer)
    actual.config = {}
    actual.repository = run.repository
    actual.github_login = run.github_login
    actual.structured_reviews = publisher
    actual.gh = lambda method, path: {"id": 1}
    actual.gh_pages = lambda path: [pr] if path == "/pulls?state=open" else []
    actual._event_payload = lambda: event
    actual.run()
    assert len(reviews) == 1


def test_final_response_transport(monkeypatch):
    from agent_conversation import AgentConversationDispatcher
    calls = []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            calls.append(self.path)
            body = {"response": artifact()} if self.path.endswith("/agent_final_response") else {"execution_status": "finished"}
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(body).encode())
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        dispatcher = object.__new__(AgentConversationDispatcher)
        dispatcher._cloud = None
        dispatcher.agent_url = f"http://127.0.0.1:{server.server_port}"
        dispatcher.api_key = "test-only"
        assert dispatcher.review_snapshot("id") == ("finished", artifact())
        assert calls == ["/api/conversations/id", "/api/conversations/id/agent_final_response"]
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_explicit_draft_is_publishable(runner):
    run, pr, reviews, starts = runner
    pr["draft"] = True
    publisher = publication.StructuredReviews(run)
    publisher.advance(pr, start=True, explicit=True)
    assert publisher.advance(pr)["disposition"] == "published"
    assert len(reviews) == 1


def test_crash_after_acceptance_before_receipt(runner, monkeypatch):
    from agent_conversation import ReviewLease
    run, pr, reviews, starts = runner
    publisher = publication.StructuredReviews(run)
    publisher.advance(pr, start=True)
    save = ReviewLease.save
    def crash(self, **changes):
        if changes.get("status") == "published":
            raise RuntimeError("receipt persistence crashed")
        return save(self, **changes)
    with monkeypatch.context() as patch:
        patch.setattr(ReviewLease, "save", crash)
        with pytest.raises(RuntimeError, match="persistence"):
            publisher.advance(pr)
    assert publisher.advance(pr)["disposition"] == "deduplicated"
    assert len(reviews) == 1


@pytest.mark.parametrize("raw", ["```json\n{}\n```", "not json", "{}", "[]"])
def test_invalid_final_output_quarantined(runner, raw):
    run, pr, reviews, starts = runner
    publisher = publication.StructuredReviews(run)
    publisher.advance(pr, start=True)
    run.dispatcher.review_snapshot = lambda cid: ("finished", raw)
    with pytest.raises(ValueError):
        publisher.advance(pr)
    assert publisher.advance(pr, start=True)["disposition"] == "deduplicated"
    assert not reviews


def test_new_request_is_not_consumed_by_old_result(runner):
    run, pr, reviews, starts = runner
    publisher = publication.StructuredReviews(run)
    publisher.advance(pr, "request:1", start=True)
    assert publisher.advance(pr, "request:2", start=True)["disposition"] == "published"
    assert publisher.advance(pr, "request:2", start=True)["disposition"] == "created"
    assert len(starts) == 2


def test_completion_uses_claimed_trigger_not_new_request(runner):
    run, pr, reviews, starts = runner
    completions = []
    run._finish_completed_review = lambda *args: completions.append(args)
    publisher = publication.StructuredReviews(run)
    publisher.advance(pr, "request:1", start=True, trigger={"id": 1}, label="review")
    publisher.advance(pr, "request:2", start=True, trigger={"id": 2})
    assert completions[0][1:] == ({"id": 1}, "review")
    publisher.advance(pr)
    assert len(completions) == 1
