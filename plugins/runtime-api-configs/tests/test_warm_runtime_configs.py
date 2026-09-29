"""End-to-end tests for warm_runtime_configs against an in-process HTTP server.

Uses only the standard library. Boots a threading HTTP server, points
RUNTIME_API_URL at it, and runs each CLI subcommand as if it were a real
runtime-api install.
"""

from __future__ import annotations

import binascii
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


PLUGIN_DIR = Path(__file__).resolve().parents[1]
SCRIPT_PATH = PLUGIN_DIR / "scripts" / "warm_runtime_configs.py"

spec = importlib.util.spec_from_file_location("wrc", SCRIPT_PATH)
assert spec and spec.loader
wrc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wrc)


ADMIN_PASSWORD = "hunter2"
API_KEY = "test-api-key"
SALT = "salt-value"
CHALLENGE = "challenge-value"
ITERATIONS = 1000

EXPECTED_HASH = binascii.hexlify(
    hashlib.pbkdf2_hmac(
        "sha256",
        ADMIN_PASSWORD.encode(),
        (SALT + CHALLENGE).encode(),
        ITERATIONS,
        dklen=32,
    )
).decode()

ADMIN_JWT = "test-jwt"


class FakeRuntimeAPI(BaseHTTPRequestHandler):
    """In-process stand-in for the runtime-api admin endpoints."""

    configs: dict[str, dict] = {}
    calls: list[tuple[str, str, dict, dict]] = []
    initial_configs: list[dict] = []

    def log_message(self, format, *args):  # silence stdout noise
        pass

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode() if length else ""
        return json.loads(raw) if raw else {}

    def _respond(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/admin/challenge":
            self._respond(200, {"salt": SALT, "challenge": CHALLENGE, "iterations": ITERATIONS})
            return
        if self.path == "/api/admin/api-keys":
            if self.headers.get("Authorization") != f"Bearer {ADMIN_JWT}":
                self._respond(401, {"error": "bad token"})
                return
            self.calls.append(("GET", self.path, dict(self.headers), {}))
            # Real runtime-api returns a top-level JSON array of ApiKeyResponse.
            self._respond_raw(200, json.dumps([
                {"id": 1, "name": "default", "key_value": API_KEY},
                {"id": 2, "name": "other",   "key_value": "other-key"},
            ]).encode())
            return
        if self.path == "/api/warm-runtime-configs":
            if self.headers.get("X-API-Key") != API_KEY:
                self._respond(401, {"error": "bad api key"})
                return
            merged = list(self.initial_configs) + [
                dict(name=n, source="db", **c) for n, c in self.configs.items()
            ]
            self._respond(200, {"configs": merged})
            return
        self._respond(404, {"error": "not found"})

    def _respond_raw(self, status: int, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path == "/api/admin/login":
            body = self._read_body()
            if body.get("challenge") == CHALLENGE and body.get("hash") == EXPECTED_HASH:
                self._respond(200, {"token": ADMIN_JWT})
            else:
                self._respond(401, {"error": "bad password"})
            return
        self._respond(404, {"error": "not found"})

    def do_PUT(self):
        prefix = "/api/admin/warm-runtime-configs/"
        if not self.path.startswith(prefix):
            self._respond(404, {"error": "not found"})
            return
        if self.headers.get("Authorization") != f"Bearer {ADMIN_JWT}":
            self._respond(401, {"error": "bad token"})
            return
        name = self.path[len(prefix):]
        body = self._read_body()
        self.configs[name] = body
        self.calls.append(("PUT", name, dict(self.headers), body))
        self._respond(200, {"name": name, **body})

    def do_DELETE(self):
        prefix = "/api/admin/warm-runtime-configs/"
        if not self.path.startswith(prefix):
            self._respond(404, {"error": "not found"})
            return
        if self.headers.get("Authorization") != f"Bearer {ADMIN_JWT}":
            self._respond(401, {"error": "bad token"})
            return
        name = self.path[len(prefix):]
        removed = self.configs.pop(name, None)
        self.calls.append(("DELETE", name, dict(self.headers), {}))
        if removed is None:
            self._respond(404, {"error": f"no such config {name}"})
        else:
            self._respond(200, {"message": f"deleted {name}"})


class CliIntegrationTests(unittest.TestCase):
    server: HTTPServer
    thread: threading.Thread

    @classmethod
    def setUpClass(cls) -> None:
        cls.server = HTTPServer(("127.0.0.1", 0), FakeRuntimeAPI)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        host, port = cls.server.server_address
        os.environ["RUNTIME_API_URL"] = f"http://{host}:{port}"
        os.environ["API_KEY"] = API_KEY
        os.environ["ADMIN_PASSWORD"] = ADMIN_PASSWORD

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.thread.join(timeout=2)

    def setUp(self) -> None:
        FakeRuntimeAPI.configs.clear()
        FakeRuntimeAPI.calls.clear()
        FakeRuntimeAPI.initial_configs = [
            {
                "name": "v1_current",
                "source": "file",
                "image": "ghcr.io/openhands/agent-server:1.46.0-python",
                "count": 1,
                "command": ["/usr/local/bin/openhands-agent-server", "--port", "60000"],
                "working_dir": "/workspace/project",
                "environment": {"BASE": "1"},
            }
        ]
        os.environ.pop("ADMIN_TOKEN", None)

    @contextlib.contextmanager
    def _capture_stdout(self):
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            yield buf
        finally:
            sys.stdout = old

    def test_list_returns_configs(self) -> None:
        with self._capture_stdout() as out:
            wrc.main(["list"])
        configs = json.loads(out.getvalue())
        self.assertEqual([c["name"] for c in configs], ["v1_current"])

    def test_template_strips_identity_and_applies_overrides(self) -> None:
        with self._capture_stdout() as out:
            wrc.main(
                [
                    "template", "v1_current",
                    "--image", "ghcr.io/your-org/openhands-php:8.4-v1",
                    "--count", "2",
                ]
            )
        derived = json.loads(out.getvalue())
        self.assertNotIn("name", derived)
        self.assertNotIn("source", derived)
        self.assertEqual(derived["image"], "ghcr.io/your-org/openhands-php:8.4-v1")
        self.assertEqual(derived["count"], 2)
        self.assertEqual(derived["environment"], {"BASE": "1"})

    def test_save_upserts_via_admin_auth(self) -> None:
        body = {
            "image": "ghcr.io/your-org/openhands-php:8.4-v1",
            "count": 1,
            "command": ["x"],
            "working_dir": "/w",
            "environment": {},
        }
        sys.stdin = io.StringIO(json.dumps(body))
        try:
            with self._capture_stdout():
                wrc.main(["save", "php-web"])
        finally:
            sys.stdin = sys.__stdin__

        self.assertIn("php-web", FakeRuntimeAPI.configs)
        method, name, headers, sent = FakeRuntimeAPI.calls[-1]
        self.assertEqual(method, "PUT")
        self.assertEqual(name, "php-web")
        self.assertEqual(headers.get("Authorization"), f"Bearer {ADMIN_JWT}")
        self.assertEqual(sent["image"], body["image"])

    def test_save_from_file(self) -> None:
        path = Path(self.id().split(".")[-1] + ".json")
        path.write_text(json.dumps({"image": "x", "command": [], "working_dir": "/", "environment": {}, "count": 1}))
        try:
            with self._capture_stdout():
                wrc.main(["save", "from-file", "--file", str(path)])
        finally:
            path.unlink()
        self.assertIn("from-file", FakeRuntimeAPI.configs)

    def test_delete_removes_config(self) -> None:
        FakeRuntimeAPI.configs["php-web"] = {"image": "x"}
        with self._capture_stdout():
            wrc.main(["delete", "php-web"])
        self.assertNotIn("php-web", FakeRuntimeAPI.configs)

    def test_admin_token_env_skips_login(self) -> None:
        FakeRuntimeAPI.configs["php-web"] = {"image": "x"}
        os.environ["ADMIN_TOKEN"] = ADMIN_JWT
        os.environ.pop("ADMIN_PASSWORD", None)  # would fail if handshake ran
        try:
            with self._capture_stdout():
                wrc.main(["delete", "php-web"])
            # Handshake would have called /api/admin/challenge; verify it didn't.
            self.assertNotIn("php-web", FakeRuntimeAPI.configs)
            self.assertEqual(FakeRuntimeAPI.calls[-1][0], "DELETE")
        finally:
            os.environ["ADMIN_PASSWORD"] = ADMIN_PASSWORD

    def test_missing_env_fails_fast(self) -> None:
        os.environ.pop("RUNTIME_API_URL", None)
        try:
            with self.assertRaises(SystemExit) as cm:
                wrc.main(["list"])
            self.assertEqual(cm.exception.code, 1)
        finally:
            host, port = self.server.server_address
            os.environ["RUNTIME_API_URL"] = f"http://{host}:{port}"

    def test_list_falls_back_to_admin_when_api_key_missing(self) -> None:
        """Without API_KEY set, list must log in as admin and fetch it."""
        os.environ.pop("API_KEY", None)
        try:
            with self._capture_stdout() as out:
                wrc.main(["list"])
            self.assertEqual(
                [c["name"] for c in json.loads(out.getvalue())], ["v1_current"]
            )
            # Fallback path hit /api/admin/api-keys with the admin JWT.
            paths = [c[1] for c in FakeRuntimeAPI.calls]
            self.assertIn("/api/admin/api-keys", paths)
        finally:
            os.environ["API_KEY"] = API_KEY

    def test_list_fails_when_no_api_key_and_no_admin_creds(self) -> None:
        """No fallback possible: neither API_KEY nor admin creds set."""
        os.environ.pop("API_KEY", None)
        os.environ.pop("ADMIN_PASSWORD", None)
        os.environ.pop("ADMIN_TOKEN", None)
        try:
            with self.assertRaises(SystemExit) as cm:
                wrc.main(["list"])
            self.assertEqual(cm.exception.code, 1)
        finally:
            os.environ["API_KEY"] = API_KEY
            os.environ["ADMIN_PASSWORD"] = ADMIN_PASSWORD


if __name__ == "__main__":
    unittest.main()
