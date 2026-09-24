"""Warn and close abandoned pull requests with persistently failing required CI."""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from github_client import GitHubRepository, run_repositories

WARN_AFTER_SECONDS = 7 * 24 * 60 * 60
CLOSE_AFTER_SECONDS = 7 * 24 * 60 * 60
WARNING_MARKER = "<!-- openhands-stale-ci-warning -->"
CLOSE_MARKER = "<!-- openhands-stale-ci-close -->"
PASSING_CONCLUSIONS = {"success", "neutral", "skipped"}
PULL_REQUESTS_QUERY = """
query($owner: String!, $name: String!, $cursor: String) {
  repository(owner: $owner, name: $name) {
    pullRequests(first: 40, after: $cursor, states: OPEN) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number isDraft baseRefName headRefOid
        author { login }
        commits(last: 1) {
          nodes {
            commit {
              statusCheckRollup {
                contexts(first: 100) {
                  totalCount
                  nodes {
                    __typename
                    ... on CheckRun {
                      databaseId name status conclusion startedAt completedAt
                      checkSuite { app { databaseId } }
                    }
                    ... on StatusContext { context state createdAt }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""
KV_TOKEN = os.environ.get("AUTOMATION_KV_TOKEN", "")
KV_BASE = os.environ.get("AUTOMATION_API_URL", "").rstrip("/")


def _timestamp(value):
    return datetime.fromisoformat(value).timestamp()


def _state_key(repo):
    payload = json.loads(os.environ.get("AUTOMATION_EVENT_PAYLOAD", "{}"))
    automation_id = payload.get("automation_id", "default")
    return f"github-stale-ci-pr-closer:{automation_id}:{repo.replace('/', '__')}"


def _state_path(repo):
    workspace = Path(
        os.environ.get("WORKSPACE_BASE", Path.home() / ".openhands/workspaces")
    )
    root = (
        workspace.resolve().parent.parent
        if os.environ.get("WORKSPACE_BASE")
        else workspace
    )
    directory = root / "automation-state"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / (_state_key(repo) + ".json")


def _kv_request(key, method, value=None):
    if not KV_TOKEN or not KV_BASE:
        return None
    data = json.dumps({"value": value}).encode() if value is not None else None
    request = Request(
        f"{KV_BASE}/v1/kv/{quote(key, safe='')}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {KV_TOKEN}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request) as response:
            payload = json.loads(response.read() or b"{}")
            return payload.get("value")
    except HTTPError as exc:
        if method == "GET" and exc.code == 404:
            return None
        raise


def load_state(repo):
    if KV_TOKEN and KV_BASE:
        return _kv_request(_state_key(repo), "GET") or {"version": 1, "prs": {}}
    path = _state_path(repo)
    if not path.exists():
        return {"version": 1, "prs": {}}
    return json.loads(path.read_text())


def save_state(repo, state):
    state["version"] = 1
    if KV_TOKEN and KV_BASE:
        _kv_request(_state_key(repo), "PUT", state)
        return
    path = _state_path(repo)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def complete_run(status="COMPLETED", error=None):
    """Report this detached entrypoint's terminal state to Automations."""
    url = os.environ.get("AUTOMATION_CALLBACK_URL")
    if not url:
        return
    body = {"status": status, "run_id": os.environ.get("AUTOMATION_RUN_ID", "")}
    if error:
        body["error"] = error
    request = Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": "Bearer "
            + os.environ.get("AUTOMATION_CALLBACK_API_KEY", ""),
            "Content-Type": "application/json",
        },
    )
    with urlopen(request):
        pass


class StaleCIPullRequestCloser(GitHubRepository):
    name = "github-stale-ci-pr-closer"

    def required_checks(self, branch):
        cached = getattr(self, "_required_checks", {})
        if branch in cached:
            return cached[branch]
        try:
            rules = self.gh("GET", f"/rules/branches/{quote(branch, safe='')}")
        except HTTPError as exc:
            if exc.code == 404:
                return []
            raise
        required = []
        for rule in rules:
            if rule.get("type") != "required_status_checks":
                continue
            required.extend(
                rule.get("parameters", {}).get("required_status_checks", [])
            )
        cached[branch] = required
        self._required_checks = cached
        return required

    @staticmethod
    def _required_ci_result(runs, statuses, required):
        if not required:
            return "unconfigured", None
        latest_runs = {}
        for run in sorted(runs, key=lambda item: item.get("id", 0), reverse=True):
            latest_runs.setdefault(
                (run.get("name"), (run.get("app") or {}).get("id")), run
            )
        latest_statuses = {}
        for status in sorted(
            statuses,
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        ):
            latest_statuses.setdefault(status.get("context"), status)

        states = []
        failures = []
        for item in required:
            context = item["context"]
            integration = item.get("integration_id") or None
            run = latest_runs.get((context, integration))
            if run is None and integration is None:
                matches = [
                    value for (name, _), value in latest_runs.items() if name == context
                ]
                run = max(matches, key=lambda value: value.get("id", 0), default=None)
            if run is not None:
                if run.get("status") != "completed" or run.get("conclusion") is None:
                    states.append("pending")
                elif run.get("conclusion") in PASSING_CONCLUSIONS:
                    states.append("passing")
                else:
                    states.append("failing")
                    completed = run.get("completed_at") or run.get("started_at")
                    if completed:
                        failures.append(_timestamp(completed))
                continue
            status = latest_statuses.get(context) if integration is None else None
            if status is None or status.get("state") in {"pending", "expected"}:
                states.append("pending")
            elif status.get("state") == "success":
                states.append("passing")
            else:
                states.append("failing")
                completed = status.get("updated_at") or status.get("created_at")
                if completed:
                    failures.append(_timestamp(completed))
        if "pending" in states:
            return "pending", None
        if "failing" in states:
            return "failing", max(failures) if failures else None
        return "passing", None

    def required_ci_result(self, sha, required):
        if not required:
            return "unconfigured", None
        runs = []
        for page in range(1, 11):
            batch = self.gh(
                "GET", f"/commits/{sha}/check-runs?per_page=100&page={page}"
            )
            page_runs = batch.get("check_runs", [])
            runs.extend(page_runs)
            if len(page_runs) < 100:
                break
        else:
            raise RuntimeError(f"More than 1,000 check runs found for {sha}")
        statuses = self.gh_pages(f"/commits/{sha}/statuses")
        return self._required_ci_result(runs, statuses, required)

    def required_ci_state(self, sha, required):
        return self.required_ci_result(sha, required)[0]

    @staticmethod
    def _graphql_ci_result(contexts, required):
        runs = []
        statuses = []
        for context in contexts:
            if context.get("__typename") == "CheckRun":
                app = ((context.get("checkSuite") or {}).get("app") or {}).get(
                    "databaseId"
                )
                runs.append(
                    {
                        "id": context.get("databaseId"),
                        "name": context.get("name"),
                        "app": {"id": app},
                        "status": (context.get("status") or "").lower(),
                        "conclusion": (context.get("conclusion") or "").lower() or None,
                        "started_at": context.get("startedAt"),
                        "completed_at": context.get("completedAt"),
                    }
                )
            elif context.get("__typename") == "StatusContext":
                statuses.append(
                    {
                        "context": context.get("context"),
                        "state": (context.get("state") or "").lower(),
                        "created_at": context.get("createdAt"),
                    }
                )
        return StaleCIPullRequestCloser._required_ci_result(runs, statuses, required)

    def open_pull_requests(self):
        """Read every open PR and its latest check rollup with explicit pagination."""
        owner, name = self.repository.split("/", 1)
        cursor = None
        seen_cursors = set()
        pull_requests = []
        while True:
            result = self.api(
                "POST",
                "/graphql",
                body={
                    "query": PULL_REQUESTS_QUERY,
                    "variables": {"owner": owner, "name": name, "cursor": cursor},
                },
            )
            if result.get("errors"):
                raise RuntimeError("GitHub GraphQL pull request query failed")
            connection = result["data"]["repository"]["pullRequests"]
            for node in connection["nodes"]:
                commits = node.get("commits", {}).get("nodes", [])
                rollup = (
                    ((commits[-1].get("commit") or {}).get("statusCheckRollup") or {})
                    if commits
                    else {}
                )
                contexts = rollup.get("contexts") or {"nodes": [], "totalCount": 0}
                required = self.required_checks(node["baseRefName"])
                if contexts.get("totalCount", 0) > len(contexts.get("nodes", [])):
                    state, failed_at = self.required_ci_result(
                        node["headRefOid"], required
                    )
                else:
                    state, failed_at = self._graphql_ci_result(
                        contexts.get("nodes", []), required
                    )
                pull_requests.append(
                    {
                        "number": node["number"],
                        "draft": node["isDraft"],
                        "head": {"sha": node["headRefOid"]},
                        "base": {"ref": node["baseRefName"]},
                        "user": {"login": (node.get("author") or {}).get("login", "")},
                        "_ci_state": state,
                        "_failed_at": failed_at,
                    }
                )
            page = connection["pageInfo"]
            if not page["hasNextPage"]:
                return pull_requests
            cursor = page["endCursor"]
            if not cursor or cursor in seen_cursors:
                raise RuntimeError("GitHub returned an invalid pull request cursor")
            seen_cursors.add(cursor)

    def comments(self, number):
        return self.gh_pages(f"/issues/{number}/comments")

    def post_comment(self, number, body):
        return self.gh("POST", f"/issues/{number}/comments", {"body": body})

    @staticmethod
    def author_followed_up(pr, comments, after):
        author = (pr.get("user") or {}).get("login", "").lower()
        return any(
            (comment.get("user") or {}).get("login", "").lower() == author
            and _timestamp(comment["created_at"]) > after
            for comment in comments
        )

    def reconcile(self, pr, records, now):
        number = pr["number"]
        key = str(number)
        if pr.get("draft"):
            records.pop(key, None)
            return "draft"
        head = pr["head"]["sha"]
        ci_state = pr.get("_ci_state")
        if ci_state is None:
            required = self.required_checks(pr["base"]["ref"])
            ci_state = self.required_ci_state(head, required)
        if ci_state != "failing":
            records.pop(key, None)
            return ci_state

        record = records.get(key)
        if not record or record.get("head_sha") != head:
            failed_at = pr.get("_failed_at")
            record = {
                "head_sha": head,
                "first_failed_at": now if failed_at is None else failed_at,
            }
            records[key] = record
        elif (
            not record.get("warning")
            and not record.get("reset_at")
            and pr.get("_failed_at") is not None
        ):
            # Backfill records created by versions that used first observation time.
            record["first_failed_at"] = min(record["first_failed_at"], pr["_failed_at"])
        warning = record.get("warning")
        if not warning:
            if now - record["first_failed_at"] < WARN_AFTER_SECONDS:
                return "observing"
            comments = self.comments(number)
            head_marker = f"<!-- openhands-stale-ci-warning head={head} -->"
            existing = [
                comment
                for comment in comments
                if head_marker in (comment.get("body") or "")
            ]
            existing.sort(
                key=lambda comment: comment.get("created_at", ""), reverse=True
            )
            if existing:
                warning_at = _timestamp(existing[0]["created_at"])
                if warning_at >= record[
                    "first_failed_at"
                ] and not self.author_followed_up(pr, comments, warning_at):
                    warning = {
                        "at": warning_at,
                        "head_sha": head,
                        "comment_id": existing[0].get("id"),
                    }
                    record["warning"] = warning
            if not warning:
                comment = self.post_comment(
                    number,
                    f"{WARNING_MARKER}\n{head_marker}\nRequired CI has remained failing for "
                    "seven days. Please repair it or comment with an update. If the author "
                    "does not push or comment and required CI remains failing for another "
                    "seven days, this pull request will be closed automatically.",
                )
                record["warning"] = {
                    "at": now,
                    "head_sha": head,
                    "comment_id": comment.get("id"),
                }
                return "warned"

        comments = self.comments(number)
        if self.author_followed_up(pr, comments, warning["at"]):
            records[key] = {
                "head_sha": head,
                "first_failed_at": now,
                "reset_at": now,
            }
            return "followed-up"
        if now - warning["at"] < CLOSE_AFTER_SECONDS:
            return "waiting"

        if not any(CLOSE_MARKER in (comment.get("body") or "") for comment in comments):
            self.post_comment(
                number,
                f"{CLOSE_MARKER}\nClosing because required CI is still failing seven days "
                "after the automated warning and the author has not pushed or commented. "
                "The pull request can be reopened when work resumes.",
            )
        self.gh("PATCH", f"/pulls/{number}", {"state": "closed"})
        records.pop(key, None)
        return "closed"

    def run(self):
        state = load_state(self.repository)
        records = state.setdefault("prs", {})
        open_prs = self.open_pull_requests()
        open_by_number = {pr["number"]: pr for pr in open_prs}
        open_numbers = {str(number) for number in open_by_number}
        for key in set(records) - open_numbers:
            records.pop(key, None)
        now = time.time()
        candidates = {
            pr["number"]
            for pr in open_prs
            if not pr["draft"]
            and pr["_ci_state"] == "failing"
            and pr["_failed_at"] is not None
            and now - pr["_failed_at"] >= WARN_AFTER_SECONDS
        }
        candidates.update(int(number) for number in records)
        for number in sorted(candidates, reverse=True):
            pr = open_by_number.get(number)
            if pr is None:
                continue
            outcome = self.reconcile(pr, records, now)
            print(
                json.dumps(
                    {
                        "repository": self.repository,
                        "pr": pr["number"],
                        "outcome": outcome,
                    }
                )
            )
        save_state(self.repository, state)


if __name__ == "__main__":
    try:
        run_repositories(StaleCIPullRequestCloser)
    except Exception as exc:
        complete_run("FAILED", str(exc))
        raise
    else:
        complete_run()
