"""Poll real issue openings from GitHub directly; no third-party relay.

The original test used this polling/signing loop. Credential and state paths,
the destination URL and interval are configurable for reviewers.
"""

from pathlib import Path
import hashlib
import hmac
import json
import os
import time
import urllib.request


def main():
    root = Path(os.environ["LIVE_TEST_STATE_DIR"])
    root.mkdir(parents=True, exist_ok=True)
    secret = Path(os.environ["LIVE_TEST_WEBHOOK_SECRET_FILE"]).read_text().strip()
    token = os.environ["GITHUB_TOKEN"]
    repository = "enyst/automation"
    destination = os.environ["LIVE_TEST_EVENT_URL"]

    def github(path):
        request = urllib.request.Request("https://api.github.com" + path, headers={
            "Authorization": "Bearer " + token, "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    repo = github("/repos/" + repository)
    seen_path = root / "relay-seen-issues.json"
    if seen_path.exists():
        seen = set(json.loads(seen_path.read_text()))
    else:
        seen = {item["id"] for item in github("/repos/" + repository
                + "/issues?state=all&sort=created&direction=desc&per_page=100")}
        seen_path.write_text(json.dumps(sorted(seen)))
    (root / "local-relay-ready.txt").write_text("GitHub API polling relay is ready")
    print("Local GitHub API relay ready", flush=True)
    while True:
        try:
            issues = github("/repos/" + repository
                            + "/issues?state=open&sort=created&direction=desc&per_page=100")
            for issue in reversed(issues):
                if issue["id"] in seen or "pull_request" in issue:
                    continue
                if issue["title"].startswith("[display-live]") and issue["user"]["login"] == "enyst":
                    payload = {"action": "opened", "issue": issue,
                               "repository": repo, "sender": issue["user"]}
                    encoded = json.dumps({"payload": payload}).encode()
                    signature = "sha256=" + hmac.new(secret.encode(), encoded, hashlib.sha256).hexdigest()
                    delivery = "local-github-issue-api:" + str(issue["id"])
                    request = urllib.request.Request(destination, data=encoded, method="POST", headers={
                        "Content-Type": "application/json", "X-Hub-Signature-256": signature,
                        "X-GitHub-Delivery": delivery,
                    })
                    with urllib.request.urlopen(request, timeout=30) as response:
                        result = json.load(response)
                    evidence = {"transport": "direct GitHub REST API polling, locally signed event",
                                "issue": issue["number"], "issue_created_at": issue["created_at"],
                                "delivery": delivery, "response": result}
                    with (root / "local-relay-deliveries.jsonl").open("a") as out:
                        out.write(json.dumps(evidence) + "\n")
                    print(json.dumps(evidence), flush=True)
                seen.add(issue["id"])
                seen_path.write_text(json.dumps(sorted(seen)))
        except Exception as exc:
            print(type(exc).__name__ + ": local issue relay request failed", flush=True)
        time.sleep(int(os.environ.get("LIVE_TEST_POLL_SECONDS", "30")))


if __name__ == "__main__":
    main()
