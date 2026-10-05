"""Rebuild the recorded live issue example, then deploy to a local stack.

The original test used the same upload/create requests. Only its checkout,
credential-file, profile and output paths have been made configurable here.
"""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-only", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    branch = root.parents[1]
    state = Path(os.environ["LIVE_TEST_STATE_DIR"])
    state.mkdir(parents=True, exist_ok=True)
    revision = json.loads((root / "live-evidence.json").read_text())["extensions_commit"]
    sources = {
        "agent_conversation.py": "skills/github/scripts/agent_conversation.py",
        "github_client.py": "skills/github/scripts/github_client.py",
        "reviewer_main.py": "skills/github-pr-reviewer/scripts/main.py",
    }
    python_files = {"issue-worker.py": (root / "issue-worker.py").read_bytes()}
    for name, source in sources.items():
        python_files[name] = subprocess.run(
            ["git", "show", f"{revision}:{source}"], cwd=branch,
            capture_output=True, check=True,
        ).stdout
    hashes = {name: hashlib.sha256(content).hexdigest()
              for name, content in python_files.items()}
    if hashes != json.loads((root / "bundle-source-hashes.json").read_text()):
        raise RuntimeError("Example or branch helpers differ from the recorded live test")
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        for name, content in python_files.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            member.mode = 0o644
            archive.addfile(member, io.BytesIO(content))
    tarball = buffer.getvalue()
    (state / "issue-analysis.tar.gz").write_bytes(tarball)
    (state / "bundle-source-hashes.json").write_text(json.dumps(hashes, indent=2))
    if args.bundle_only:
        print(json.dumps({"bundle": str(state / "issue-analysis.tar.gz"),
                          "source_hashes_match_live_test": True}))
        return

    key = Path(os.environ["LIVE_TEST_SESSION_API_KEY_FILE"]).read_text().strip()
    profile_id = os.environ["LIVE_TEST_AGENT_PROFILE_ID"]
    base = os.environ["AUTOMATION_API_URL"].rstrip("/")
    headers = {"Content-Type": "application/gzip", "X-Session-API-Key": key}
    request = urllib.request.Request(base + "/v1/uploads?name=display-live-issue-analysis",
                                     data=tarball, method="POST", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        upload = json.load(response)
    request_body = {
        "name": "PR 547 live issue analysis and LLM display",
        "agent_profile_id": profile_id,
        "trigger": {"type": "event", "source": "github", "on": "issues.opened",
                    "filter": "repository.full_name == 'enyst/automation' && sender.login == 'enyst' && starts_with(issue.title, '[display-live]')"},
        "tarball_path": upload["tarball_path"], "entrypoint": "python3 issue-worker.py",
        "timeout": 300,
    }
    (state / "automation-create-request.json").write_text(json.dumps(request_body, indent=2))
    existing_path = state / "test-automation.json"
    existing = json.loads(existing_path.read_text()) if existing_path.exists() else None
    url = base + "/v1" + ("/" + existing["id"] if existing else "")
    request = urllib.request.Request(
        url, data=json.dumps(request_body).encode(), method="PATCH" if existing else "POST",
        headers={"Content-Type": "application/json", "X-Session-API-Key": key})
    with urllib.request.urlopen(request, timeout=30) as response:
        automation = json.load(response)
    (state / "test-automation.json").write_text(json.dumps(automation, indent=2))
    print(json.dumps({"automation_id": automation["id"], "name": automation["name"],
                      "trigger": automation["trigger"], "agent_profile_id": profile_id,
                      "tarball_bytes": len(tarball)}))


if __name__ == "__main__":
    main()
