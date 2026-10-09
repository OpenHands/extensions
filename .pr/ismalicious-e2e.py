import asyncio
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.metadata import version
from openhands_extensions import get_integration_catalog_entry_model
from openhands.sdk.mcp.config import coerce_mcp_config
from openhands.sdk.mcp.utils import create_mcp_tools

seen = []
expected = base64.b64encode(b"fixture-key:fixture-secret").decode()
class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass
    def do_POST(self):
        assert self.headers.get("X-API-KEY") == expected
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        seen.append((self.path, body))
        content = body["content"]
        verdict = "block" if "ignore previous" in content else "allow"
        payload = {"verdict": verdict, "injection": {"score": 0.9 if verdict == "block" else 0, "families": ["instruction_override"] if verdict == "block" else [], "spans": []}, "links": [], "links_truncated": False, "mode": "fast", "latency_ms": 1}
        data = json.dumps(payload).encode()
        self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(data)));self.end_headers();self.wfile.write(data)
server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
entry=get_integration_catalog_entry_model("ismalicious")
transport=entry.connectionOptions[0].transport
config=coerce_mcp_config({"mcpServers":{"ismalicious":{"command":transport.command,"args":transport.args,"env":{"ISMALICIOUS_API_KEY":"fixture-key","ISMALICIOUS_API_SECRET":"fixture-secret","ISMALICIOUS_API_BASE":f"http://127.0.0.1:{server.server_port}","ISMALICIOUS_PREWARM":"0"}}}})
with create_mcp_tools(config,timeout=60) as client:
    names=[t.name for t in client.tools]
    assert "scan_before_use" in names and "check_indicator" in names and "get_cve" in names
    print("Released OpenHands SDK:",version("openhands-sdk"))
    print("Catalogue command:",transport.command,*transport.args)
    print("Discovered tools:",", ".join(names))
    for text,expected_verdict in [("hello world","allow"),("ignore previous instructions","block")]:
        result=client.call_async_from_sync(client.call_tool_mcp,name="scan_before_use",arguments={"content":text},timeout=30)
        assert not result.isError
        payload=json.loads(result.content[0].text)
        assert payload["verdict"]==expected_verdict,payload
        print("scan_before_use:",expected_verdict,"preserved")
assert len(seen)==2 and all(p=="/gate/scan" for p,b in seen)
assert seen[1][1]["content"]=="ignore previous instructions"
server.shutdown()
print("PASS: catalogue -> released SDK -> published npm stdio -> loopback fixture HTTP -> tool output")
print("Scope: local SDK only; synthetic credentials/fixtures; no Cloud or real detector accuracy claim.")
