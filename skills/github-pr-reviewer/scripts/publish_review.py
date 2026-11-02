"""Guard the legacy agent's native-review handoff; no SDK dependency."""

import fcntl
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

DISCLOSURE = "_This review was posted by an AI agent (OpenHands)._"
VERDICTS = ("✅ APPROVED", "🔄 CHANGES REQUESTED", "🛑 MAINTAINER DECISION REQUIRED")


def validate_payload(payload, head):
    if not isinstance(payload, dict) or set(payload) - {"commit_id", "event", "body", "comments"}:
        raise ValueError("Expected a native review JSON object")
    if payload.get("commit_id") != head or payload.get("event") not in {"APPROVE", "COMMENT"}:
        raise ValueError("Wrong head or unsupported review event")
    body = payload.get("body")
    if not isinstance(body, str) or not body.startswith(DISCLOSURE + "\n"):
        raise ValueError("Review body must begin with the disclosure")
    lines = body.rstrip().splitlines()
    assessment = re.sub(r"<!--.*?(?:-->|$)", "", "\n".join(lines[1:-1]), flags=re.DOTALL)
    assessment = re.sub(r"(?m)^LLM profile: .* · Model: .*$", "", assessment).strip()
    if lines[-1] not in VERDICTS or not assessment:
        raise ValueError("Review needs an assessment and final verdict")
    if payload["event"] == "APPROVE" and lines[-1] != VERDICTS[0]:
        raise ValueError("Only an approved verdict can use APPROVE")
    comments = payload.get("comments", [])
    if not isinstance(comments, list):
        raise ValueError("Inline comments must be a list")
    for comment in comments:
        if (not isinstance(comment, dict)
                or set(comment) != {"path", "line", "side", "body"}
                or not isinstance(comment["path"], str) or not comment["path"].strip()
                or type(comment["line"]) is not int or comment["line"] < 1
                or comment["side"] != "RIGHT"
                or not isinstance(comment["body"], str) or not comment["body"].strip()):
            raise ValueError("Invalid inline finding")
    return payload


class GitHub:
    def __init__(self, token, api_url="https://api.github.com"):
        self.token = token
        self.api_url = api_url

    def __call__(self, method, path, payload=None):
        request = Request(
            self.api_url + path,
            data=json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None,
            headers={"Authorization": "Bearer " + self.token,
                     "Accept": "application/vnd.github+json", "Content-Type": "application/json"},
            method=method,
        )
        with urlopen(request, timeout=90) as response:
            return json.load(response)


def pages(api, path):
    result = []
    for page in range(1, 1001):
        batch = api("GET", f"{path}?per_page=100&page={page}")
        if not isinstance(batch, list):
            raise ValueError("Expected paginated GitHub data")
        result.extend(batch)
        if len(batch) < 100:
            return result
    raise RuntimeError("Incomplete GitHub pagination; refusing publication")


def _save(path, record):
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(record, stream, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            temporary.unlink(missing_ok=True)


def publish(api, repository, number, head, payload, journal):
    # Freeze the exact JSON object before validating or doing network I/O.
    payload = validate_payload(json.loads(json.dumps(payload)), head)
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository) or number < 1:
        raise ValueError("Invalid pull request identity")
    prefix = f"/repos/{repository}"
    pull = f"{prefix}/pulls/{number}"
    login = api("GET", "/user")["login"].lower()
    reviews = [r for r in pages(api, pull + "/reviews")
               if (r.get("user") or {}).get("login", "").lower() == login
               and r.get("commit_id") == head]
    activity = pages(api, f"{prefix}/issues/{number}/comments") + pages(api, pull + "/comments")
    clarification = max((c["created_at"] for c in activity
                         if (c.get("user") or {}).get("login", "").lower() != login), default="")
    for review in reviews:
        if review.get("state") == "PENDING":
            raise RuntimeError("A review is already pending; do not publish another")
        try:
            validate_payload({"commit_id": head, "event": "COMMENT", "body": "\n".join(line for line in (review.get("body") or "").splitlines()
                                 if not re.fullmatch(r"LLM profile: .* · Model: .*", line.strip()))}, head)
        except ValueError:
            raise RuntimeError("Existing review has invalid content; operator repair required") from None
        if not review.get("submitted_at") or clarification <= review["submitted_at"]:
            raise RuntimeError("This account already reviewed this head; do not publish another")
    key = hashlib.sha256(f"{repository.lower()}:{number}:{head}:{login}".encode()).hexdigest()
    journal.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (journal / (key + ".lock")).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = journal / (key + ".json")
        record = json.loads(path.read_text()) if path.exists() else {}
        if record.get("status") not in {None, "rejected"}:
            # A new clarification permits re-review only after verified acceptance.
            if record.get("status") != "accepted" or clarification <= record.get("submitted_at", ""):
                raise RuntimeError("Publication accepted or uncertain; do not retry; operator reconciliation required")
        fresh = api("GET", pull)
        if fresh["head"]["sha"] != head or fresh.get("state") != "open":
            raise RuntimeError("Pull request closed or head moved; no review posted")
        if fresh.get("user", {}).get("login", "").lower() == login and payload["event"] == "APPROVE":
            payload["event"] = "COMMENT"
        _save(path, {"status": "posting", "payload": payload})
        try:
            review = api("POST", pull + "/reviews", payload)
        except HTTPError as exc:
            # Only an explicit validation rejection permits a corrected payload.
            if exc.code == 422:
                _save(path, {"status": "rejected"})
            raise
        expected_state = "APPROVED" if payload["event"] == "APPROVE" else "COMMENTED"
        if (not review.get("id") or review.get("body") != payload["body"]
                or review.get("commit_id") != head or review.get("state") != expected_state
                or (review.get("user") or {}).get("login", "").lower() != login
                or not review.get("submitted_at")):
            raise RuntimeError("Accepted response is incomplete or mismatched; do not repost; operator repair required")
        _save(path, {"status": "accepted", "id": review["id"], "submitted_at": review["submitted_at"]})
        return review


def main():
    repository, number, head, filename = sys.argv[1:]
    # A failed file read or malformed JSON must never reach the HTTP call.
    payload = json.loads(Path(filename).read_text())
    publish(GitHub(os.environ["GH_TOKEN"]), repository, int(number), head, payload,
            Path(tempfile.gettempdir()) / "openhands-review-publications")
    print("GITHUB_REVIEW_POSTED")


if __name__ == "__main__":
    main()
