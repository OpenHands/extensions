"""The automation service's KV API, served over HTTP for monitor templates."""

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer


class KVHandler(BaseHTTPRequestHandler):
    """One value per key, each limited to `limit` bytes of UTF-8 JSON and
    refused with the service's 413 body (see the automation repository's
    `kv_router._check_value_size`)."""

    store: dict
    puts: list
    limit: int
    base: str

    def log_message(self, *args):
        pass

    def _reply(self, code: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        key = self.path.rsplit("/", 1)[1]
        if key not in self.store:
            return self._reply(404, {"detail": "Key not found"})
        self._reply(200, {"key": key, "value": self.store[key]})

    def do_PUT(self):
        key = self.path.rsplit("/", 1)[1]
        value = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        size = len(json.dumps(value, ensure_ascii=False).encode())
        self.puts.append(size)
        if size > self.limit:
            return self._reply(413, {"detail": {
                "error": "value_too_large",
                "message": f"Value for key '{key}' is {size} bytes, "
                           f"exceeding the {self.limit} byte per-value limit",
                "key": key, "size": size, "limit": self.limit,
            }})
        self.store[key] = value
        self._reply(200, {"key": key, "value": value})


@contextmanager
def serve_kv(limit: int = 64 * 1024):
    """Yield a handler class whose `store`, `puts`, `limit` and `base` (the
    AUTOMATION_API_URL to use) describe a running KV server."""
    handler = type("Handler", (KVHandler,), {"store": {}, "puts": [], "limit": limit})
    server = HTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    handler.base = f"http://127.0.0.1:{server.server_port}/api/automation"
    try:
        yield handler
    finally:
        server.shutdown()
