"""Shared GitHub transport and repository operations for GitHub automations."""

import argparse
import json
import os
import re
import subprocess
from functools import cached_property
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urlsplit
from urllib.request import Request, urlopen


def _load_secret(name: str) -> str:
    """Read one named secret from the environment or configured Agent Server."""
    value = os.environ.get(name)
    if value:
        return value

    from openhands.sdk.workspace import RemoteWorkspace

    workspace = RemoteWorkspace(
        host=os.environ["AGENT_SERVER_URL"],
        api_key=os.environ["SESSION_API_KEY"],
        working_dir=os.environ.get("WORKSPACE_BASE", "/workspace"),
    )
    try:
        secret = workspace.get_secrets([name]).get(name)
        value = secret.get_value() if secret else None
    finally:
        workspace.reset_client()
    if not value:
        raise ValueError(f"The GitHub credential {name} is unavailable")
    return value


def github_request(
    token: str,
    method: str,
    path: str,
    params: dict | None = None,
    body: dict | None = None,
    accept: str = "application/vnd.github+json",
) -> tuple:
    url = f"https://api.github.com{path}"
    if params:
        url = f"{url}?{urlencode(params)}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    data = json.dumps(body).encode() if body is not None else None
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req, timeout=90) as r:
        raw = r.read()
        return (json.loads(raw) if raw.strip() else {}), dict(r.headers)


def github_paginate(token: str, path: str, params: dict | None = None) -> list:
    results = []
    base_params = dict(params or {})
    base_params.setdefault("per_page", 100)
    for page in range(1, 101):
        base_params["page"] = page
        data, _ = github_request(token, "GET", path, params=base_params)
        if not isinstance(data, list):
            raise TypeError("Expected a paginated GitHub list")
        results.extend(data)
        if len(data) < int(base_params["per_page"]):
            return results
    raise RuntimeError("GitHub pagination exceeded limit")


class GitHubRepository:
    name = "GitHub automation"

    def __init__(
        self,
        config_path=Path("config.json"),
        *,
        github_token_secret,
        repository=None,
        conversation=None,
        dispatcher=None,
    ):
        self.config = json.loads(Path(config_path).read_text())
        self.repository = repository or self.config["repository"]
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repository):
            raise ValueError("repository must be owner/repo")
        if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", github_token_secret):
            raise ValueError(
                "Expected the environment variable containing the GitHub token"
            )
        self.token_name = github_token_secret
        self.token = _load_secret(github_token_secret)
        self.conversation = conversation
        self.conversation_id = str(conversation.id) if conversation else None
        self.dispatcher = dispatcher
        self.workspace = Path(os.environ["WORKSPACE_BASE"])
        self.project = self.workspace
        self.evidence = self.workspace / "evidence"
        self.evidence.mkdir(exist_ok=True)
        self._completed_dependencies = {}

    @cached_property
    def base_branch(self):
        return self.config.get("base_branch") or self.gh("GET", "")["default_branch"]

    @property
    def github_instructions(self):
        return (
            f"Use `GH_TOKEN=${self.token_name} gh api` for GitHub requests. "
            "Never print the credential value. "
            f"Only {self.repository} is in scope. Work in {self.project}. "
            "Do not modify the automation bundle or its configuration."
        )

    def gh(self, method, path, body=None):
        return github_request(
            self.token, method, f"/repos/{self.repository}" + path, body=body
        )[0]

    def api(self, method, path, params=None, body=None):
        """Call a GitHub endpoint that is not scoped to one repository."""
        return github_request(self.token, method, path, params=params, body=body)[0]

    def shell(self, args, cwd=None, timeout=300):
        result = subprocess.run(
            args,
            cwd=cwd or self.project,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
        if result.returncode:
            raise RuntimeError(
                f"{args[0]} failed: {result.stdout[-4000:].replace(self.token, '[REDACTED]')}"
            )
        return result.stdout.strip()

    def comment(self, number, text):
        return self.gh(
            "POST",
            f"/issues/{number}/comments",
            {
                "body": text
                + f"\n\nFactory role: `{self.name}`; conversation: `{self.conversation_id}`."
                + "\n\n_This comment was posted by an AI agent (OpenHands)._"
            },
        )

    def open_issues(self):
        return [
            i for i in self.gh_pages("/issues?state=open") if "pull_request" not in i
        ]

    def statuses(self, sha):
        result = {}
        for item in self.gh_pages(f"/commits/{sha}/statuses"):
            result.setdefault(item["context"], item["state"])
        return result

    def check_runs(self, sha):
        """Return every check run GitHub reported for one commit SHA.

        Reading check runs needs no branch-protection or ruleset access, so this
        is the head-eligibility signal the automation's own token can always
        see. The endpoint answers with an object rather than a list, so it
        paginates through ``gh`` instead of ``gh_pages``.
        """
        runs = []
        for page in range(1, 101):
            data = self.gh(
                "GET", f"/commits/{sha}/check-runs?per_page=100&page={page}"
            )
            batch = data.get("check_runs") or []
            runs.extend(batch)
            if len(runs) >= int(data.get("total_count") or 0) or not batch:
                return runs
        raise RuntimeError("GitHub check-run pagination exceeded limit")

    def completed_dependency(self, number):
        if number in self._completed_dependencies:
            return self._completed_dependencies[number]
        try:
            dependency = self.gh("GET", f"/issues/{number}")
        except HTTPError as exc:
            if exc.code == 404:
                return False
            raise
        completed = (
            dependency["state"] == "closed"
            and dependency.get("state_reason") == "completed"
        )
        self._completed_dependencies[number] = completed
        return completed

    def dependencies_complete(self, issue):
        """Honor explicit Depends on lines; unknown/incomplete issues remain blocked."""
        for line in re.findall(
            "^Depends on:\\s*(.+)$",
            issue.get("body") or "",
            re.MULTILINE | re.IGNORECASE,
        ):
            for number in re.findall("#(\\d+)", line):
                if not self.completed_dependency(number):
                    return False
        return True

    def gh_pages(self, endpoint):
        split = urlsplit(endpoint)
        return github_paginate(
            self.token,
            f"/repos/{self.repository}" + split.path,
            params=dict(parse_qsl(split.query)),
        )


def run_repositories(automation_type, conversation=None, dispatcher=None):
    parser = argparse.ArgumentParser(description=automation_type.__doc__)
    parser.add_argument("--github-token-secret")
    args = parser.parse_args()
    config = json.loads(Path("config.json").read_text())
    token_name = args.github_token_secret or config.get(
        "github_token_secret", "GITHUB_PERSONAL_ACCESS_TOKEN"
    )
    repositories = config.get("repos") or [config["repository"]]
    failures = []
    for repository in repositories:
        options = dict(
            github_token_secret=token_name,
            repository=repository,
            conversation=conversation,
        )
        if dispatcher is not None:
            options["dispatcher"] = dispatcher
        automation = automation_type(**options)
        try:
            automation.run()
        except Exception as exc:  # noqa: BLE001 - one repository must not block others
            failures.append(repository)
            print(
                json.dumps({"repository": repository, "error": type(exc).__name__}),
                flush=True,
            )
    if failures:
        raise RuntimeError("Automation failed for: " + ", ".join(failures))
    return str(conversation.id) if conversation else None
