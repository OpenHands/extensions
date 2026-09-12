"""Factory authorization and merge gates, without credentials or network access."""

import importlib.util
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).parents[1]
    / "skills/openhands-automation/scripts/github_factory_gateway.py"
)


@pytest.fixture
def broker():
    spec = importlib.util.spec_from_file_location("factory_broker", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("role", ["triage", "developer", "reviewer", "watchdog"])
def test_no_role_can_write_main_or_administer_repository(broker, role):
    for method, path, body in [
        ("PATCH", "/git/refs/heads/main", {"sha": "a" * 40}),
        ("POST", "/git/refs", {"ref": "refs/heads/main", "sha": "a" * 40}),
        ("PUT", "/contents/application.js", {"content": "AAAA"}),
        ("DELETE", "", {}),
        ("PUT", "/pulls/1/merge", {"sha": "a" * 40}),
        ("PATCH", "/issues/1", {"state": "closed"}),
    ]:
        assert not broker.permitted(role, method, path, body)


def test_writer_cannot_accept_and_reviewer_cannot_publish(broker):
    assert broker.permitted(
        "developer", "POST", "/git/refs", {"ref": "refs/heads/factory/issue-1"}
    )
    assert not broker.permitted(
        "developer",
        "POST",
        "/statuses/" + "a" * 40,
        {"context": "software-factory/review"},
    )
    assert not broker.permitted("reviewer", "POST", "/git/blobs", {})
    assert not broker.permitted(
        "reviewer",
        "POST",
        "/pulls/1/reviews",
        {"event": "APPROVE", "commit_id": "a" * 40},
    )
    assert not broker.permitted(
        "developer", "PATCH", "/git/refs/heads/factory/issue-1", {"force": True}
    )
    assert broker.permitted(
        "reviewer",
        "POST",
        "/statuses/" + "a" * 40,
        {"context": "software-factory/tests"},
    )


def install_merge_fixture(monkeypatch, broker):
    sha = "a" * 40
    pr = {
        "number": 1,
        "state": "open",
        "draft": False,
        "mergeable": True,
        "head": {"sha": sha, "ref": "factory/issue-1"},
        "base": {"sha": "b" * 40, "ref": "main"},
    }
    data = {
        "pr": pr,
        "statuses": [
            {"context": "software-factory/tests", "state": "success"},
            {"context": "software-factory/review", "state": "success"},
        ],
        "checks": {"total_count": 0, "check_runs": []},
        "comparison": {"status": "ahead"},
    }
    writes = []

    def github(role, method, path, body=None):
        assert role == "watchdog"
        if method == "PUT":
            writes.append((path, body))
            return {"merged": True}
        if path == "/pulls/1":
            return data["pr"]
        if "/statuses?" in path:
            return data["statuses"]
        if "/check-runs?" in path:
            return data["checks"]
        if path.startswith("/compare/"):
            return data["comparison"]
        raise AssertionError(path)

    monkeypatch.setattr(broker, "github", github)
    return sha, data, writes


def test_merge_requires_exact_reviewed_head(monkeypatch, broker):
    sha, data, writes = install_merge_fixture(monkeypatch, broker)
    assert broker.merge(1, sha)["merged"]
    assert writes == [("/pulls/1/merge", {"sha": sha, "merge_method": "squash"})]


@pytest.mark.parametrize(
    "failure",
    [
        "new_head",
        "missing_review",
        "new_failure",
        "pending_ci",
        "stale_base",
        "incomplete_checks",
        "draft",
        "conflict",
    ],
)
def test_merge_fails_closed(monkeypatch, broker, failure):
    sha, data, writes = install_merge_fixture(monkeypatch, broker)
    if failure == "new_head":
        data["pr"]["head"]["sha"] = "c" * 40
    elif failure == "missing_review":
        data["statuses"].pop()
    elif failure == "new_failure":
        data["statuses"].insert(
            0, {"context": "software-factory/tests", "state": "failure"}
        )
    elif failure == "pending_ci":
        data["checks"] = {"total_count": 1, "check_runs": [{"conclusion": None}]}
    elif failure == "stale_base":
        data["comparison"]["status"] = "diverged"
    elif failure == "incomplete_checks":
        data["checks"]["total_count"] = 101
    elif failure == "draft":
        data["pr"]["draft"] = True
    elif failure == "conflict":
        data["pr"]["mergeable"] = False
    with pytest.raises(ValueError):
        broker.merge(1, sha)
    assert not writes


def test_merge_rejects_invalid_identity_before_network(broker, monkeypatch):
    def unexpected(*args):
        raise AssertionError("Invalid identity reached GitHub")

    monkeypatch.setattr(broker, "github", unexpected)
    for number, sha in [(0, "a" * 40), (1, "../other-repo"), (1, "main")]:
        with pytest.raises(ValueError):
            broker.merge(number, sha)


def test_reads_are_limited_to_role_inputs(broker):
    assert broker.permitted("triage", "GET", "/issues?state=open", {})
    assert not broker.permitted("triage", "GET", "/git/ref/heads/main", {})
    assert not broker.permitted("triage", "GET", "/pulls", {})
    assert broker.permitted("watchdog", "GET", "/commits/" + "a" * 40 + "/statuses", {})
    assert not broker.permitted("watchdog", "GET", "/git/blobs/" + "a" * 40, {})
    assert not broker.permitted("watchdog", "GET", "/issues", {})
    assert broker.permitted("reviewer", "GET", "/git/ref/heads/factory/issue-1", {})
    assert not broker.permitted("reviewer", "GET", "/git/ref/heads/private-work", {})


def test_watchdog_cannot_post_comments(broker):
    for role in ("triage", "developer", "reviewer"):
        assert broker.permitted(role, "POST", "/issues/1/comments", {"body": "report"})
    assert not broker.permitted(
        "watchdog", "POST", "/issues/1/comments", {"body": "report"}
    )


def configure_fixture(broker, monkeypatch, tmp_path):
    import json

    grants = {role: f"grant-{role}" for role in broker.ROLES}
    control = tmp_path / "grants.json"
    control.write_text(json.dumps(grants))
    control.chmod(0o600)
    monkeypatch.setenv("FACTORY_REPOSITORY", "owner/repository")
    monkeypatch.setenv("FACTORY_CONTROL_FILE", str(control))
    monkeypatch.delenv("FACTORY_GITHUB_WATCHDOG_TOKEN_ENV", raising=False)
    for role in broker.ROLES:
        monkeypatch.setenv(f"FACTORY_GITHUB_{role.upper()}_TOKEN", f"github-{role}")
    return grants


@pytest.mark.parametrize("failure", ["missing", "empty", "shared", "exposed"])
def test_configuration_rejects_missing_or_shared_credentials(
    broker, monkeypatch, tmp_path, failure
):
    configure_fixture(broker, monkeypatch, tmp_path)
    name = "FACTORY_GITHUB_REVIEWER_TOKEN"
    if failure == "missing":
        monkeypatch.delenv(name)
    else:
        monkeypatch.setenv(
            name,
            {"empty": " ", "shared": "github-developer", "exposed": "grant-reviewer"}[
                failure
            ],
        )
    with pytest.raises(ValueError) as error:
        broker.configure()
    assert "github-developer" not in str(error.value)
    assert "grant-reviewer" not in str(error.value)
    assert broker.TOKENS == {}


@pytest.mark.parametrize("shared_watchdog", [False, True])
def test_concurrent_requests_keep_role_credentials(
    broker, monkeypatch, tmp_path, shared_watchdog
):
    import io
    import json
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier, Thread
    from urllib.request import Request, urlopen

    grants = configure_fixture(broker, monkeypatch, tmp_path)
    if shared_watchdog:
        monkeypatch.setenv(
            "FACTORY_GITHUB_WATCHDOG_TOKEN_ENV", "FACTORY_GITHUB_DEVELOPER_TOKEN"
        )
        monkeypatch.delenv("FACTORY_GITHUB_WATCHDOG_TOKEN")
    broker.configure()
    # Sharing an upstream credential must not share worker authorization.
    assert not broker.permitted("watchdog", "POST", "/git/blobs", {})
    assert not broker.permitted("watchdog", "POST", "/issues/1/comments", {"body": "x"})
    barrier = Barrier(4)
    seen = []

    def upstream(request, timeout):
        barrier.wait(timeout=5)
        seen.append((request.full_url, request.get_header("Authorization")))
        return io.BytesIO(b"{}")

    monkeypatch.setattr(broker, "urlopen", upstream)
    server = broker.ThreadingHTTPServer(("127.0.0.1", 0), broker.Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    paths = {
        "triage": "/labels",
        "developer": "/git/commits/" + "a" * 40,
        "reviewer": "/git/ref/heads/main",
        "watchdog": "/pulls/1",
    }

    def send(role):
        request = Request(
            f"http://127.0.0.1:{server.server_port}",
            data=json.dumps({"method": "GET", "path": paths[role]}).encode(),
            headers={"Authorization": "Bearer " + grants[role]},
        )
        with urlopen(request, timeout=10) as response:
            assert response.status == 200

    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(send, broker.ROLES))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert sorted(seen) == sorted(
        (
            broker.ROOT + paths[role],
            "Bearer github-developer"
            if shared_watchdog and role == "watchdog"
            else f"Bearer github-{role}",
        )
        for role in broker.ROLES
    )


@pytest.mark.parametrize("selected", [None, "FACTORY_GITHUB_REVIEWER_TOKEN", ""])
def test_watchdog_sharing_requires_explicit_developer_selection(
    broker, monkeypatch, tmp_path, selected
):
    configure_fixture(broker, monkeypatch, tmp_path)
    monkeypatch.delenv("FACTORY_GITHUB_WATCHDOG_TOKEN")
    if selected is not None:
        monkeypatch.setenv("FACTORY_GITHUB_WATCHDOG_TOKEN_ENV", selected)
    with pytest.raises(ValueError):
        broker.configure()


def test_shared_watchdog_still_requires_separate_reviewer(broker, monkeypatch, tmp_path):
    configure_fixture(broker, monkeypatch, tmp_path)
    monkeypatch.setenv(
        "FACTORY_GITHUB_WATCHDOG_TOKEN_ENV", "FACTORY_GITHUB_DEVELOPER_TOKEN"
    )
    monkeypatch.setenv("FACTORY_GITHUB_REVIEWER_TOKEN", "github-developer")
    with pytest.raises(ValueError):
        broker.configure()


@pytest.mark.parametrize("role", ["developer", "reviewer"])
def test_archive_uses_calling_role_credential(broker, monkeypatch, tmp_path, role):
    import io

    configure_fixture(broker, monkeypatch, tmp_path)
    broker.configure()

    def upstream(request, timeout):
        assert request.get_header("Authorization") == f"Bearer github-{role}"
        return io.BytesIO(b"archive")

    monkeypatch.setattr(broker, "urlopen", upstream)
    assert broker.archive(role, "a" * 40)["tarball"] == "YXJjaGl2ZQ=="


@pytest.mark.parametrize("force", [True, 1, "true", "false", None])
def test_force_push_flag_must_be_boolean_false(broker, force):
    assert not broker.permitted(
        "developer",
        "PATCH",
        "/git/refs/heads/factory/issue-1",
        {"sha": "a" * 40, "force": force},
    )


def test_status_pagination_keeps_latest_and_detects_later_failure(broker, monkeypatch):
    calls = []

    def github(role, method, path, body=None):
        assert role == "watchdog"
        calls.append(path)
        if path.endswith("page=1"):
            return [{"context": "newest", "state": "success"}] * 100
        return [
            {"context": "newest", "state": "failure"},
            {"context": "other-ci", "state": "failure"},
        ]

    monkeypatch.setattr(broker, "github", github)
    statuses = broker.latest_statuses("watchdog", "a" * 40)
    assert len(calls) == 2
    assert statuses["newest"]["state"] == "success"
    assert statuses["other-ci"]["state"] == "failure"


def test_incomplete_status_pagination_rejects_merge(broker, monkeypatch):
    monkeypatch.setattr(
        broker,
        "github",
        lambda *args: [{"context": "ci", "state": "success"}] * 100,
    )
    with pytest.raises(ValueError, match="pagination"):
        broker.latest_statuses("watchdog", "a" * 40)


def test_network_failure_returns_structured_gateway_error(
    broker, monkeypatch, tmp_path
):
    import io
    import json
    from urllib.error import URLError

    grants = configure_fixture(broker, monkeypatch, tmp_path)
    broker.configure()
    payload = json.dumps({"method": "GET", "path": "/pulls"}).encode()
    handler = object.__new__(broker.Handler)
    handler.headers = {
        "Authorization": "Bearer " + grants["reviewer"],
        "Content-Length": str(len(payload)),
    }
    handler.rfile = io.BytesIO(payload)
    replies = []
    handler.reply = lambda status, body: replies.append((status, body))

    def unavailable(*args):
        raise URLError("private diagnostic")

    monkeypatch.setattr(broker, "github", unavailable)
    handler.do_POST()
    assert replies == [
        (502, {"error": "GitHub upstream request failed; outcome may be unknown"})
    ]
