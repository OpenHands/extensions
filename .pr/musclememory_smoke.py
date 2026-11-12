"""Temporary live catalog proof using released packages and an isolated database.

Run from the repository root:
    uv run --group test python .pr/musclememory_smoke.py

Requires uv/uvx on PATH and network for the pinned package and default search
model on a cold cache. No model agent or paid LLM is used. The separate operator
process below simulates approval only inside this script's temporary database.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "thewariend-musclememory==0.1.7"
TOOLS = {
    f"musclememory_{name}"
    for name in ("recall", "observe", "learn", "evaluate", "inspect")
}
PROFILE = {
    "agent_name": "catalog-connection-proof",
    "bindings": {"repository.inspect": "read_file", "task.verify": "host_verify"},
}
INTENT = "Inspect local repository manifest"


def run(command, env):
    result = subprocess.run(
        command, env=env, text=True, capture_output=True, timeout=300
    )
    if result.returncode:
        raise RuntimeError(f"Command failed ({command[0]}): {result.stderr[-2000:]}")
    return result.stdout


def workflow(call, operator, manifest):
    common = {"runtime_profile": PROFILE, "visibility_scope": "default"}

    def recall():
        return call("musclememory_recall", {**common, "intent_text": INTENT})

    def observe(token, *, expected_name="catalog-fixture"):
        start = time.monotonic()
        payload = json.loads(manifest.read_text())
        elapsed = (time.monotonic() - start) * 1000
        passed = payload["name"] == expected_name
        events = [
            {
                "event_id": "intent",
                "sequence": 0,
                "kind": "intent",
                "intent_text": INTENT,
            },
            {
                "event_id": "read",
                "sequence": 1,
                "kind": "tool",
                "tool_name": "read_file",
                "capability": "repository.inspect",
                "arguments": {"path": str(manifest)},
                "status": "success",
                "outcome_verified": True,
                "duration_ms": elapsed,
            },
            {
                "event_id": "verify",
                "sequence": 2,
                "kind": "tool",
                "tool_name": "host_verify",
                "capability": "task.verify",
                "response": {"passed": passed},
                "status": "success" if passed else "failure",
                "outcome_verified": True,
            },
            {
                "event_id": "done",
                "sequence": 3,
                "kind": "completion",
                "status": "success" if passed else "failure",
            },
        ]
        result = call(
            "musclememory_observe",
            {**common, "run_token": token, "event_batch": events},
        )
        assert result["accepted_event_count"] == 4
        return elapsed

    assert recall()["no_match"]
    observe("training")
    learned = call(
        "musclememory_learn",
        {
            "run_token": "training",
            "completion_proof": {
                "succeeded": True,
                "evidence_event_ids": ["verify"],
                "summary": "Manifest independently verified",
            },
            "learning_policy": {},
        },
    )
    token, version = learned["procedure_token"], learned["procedure_version"]
    assert recall()["no_match"]
    for index in range(2):
        run_token = f"check-{index}"
        elapsed = observe(run_token)
        checked = call(
            "musclememory_evaluate",
            {
                "procedure_token": token,
                "run_token": run_token,
                "outcome_report": {
                    "succeeded": True,
                    "procedure_version": version,
                    "evidence_event_ids": ["verify"],
                },
                "performance_metrics": {
                    "observed": {"tool_calls": 2, "duration_ms": elapsed}
                },
            },
        )
    assert checked["validation_status"] == "validated"
    assert recall()["no_match"]  # Validation alone does not grant operator approval.
    operator(token)
    assert not recall()["no_match"]
    detail = call("musclememory_inspect", {"procedure_token": token})
    assert detail["successes"] == 2 and not detail["needs_review"]
    assert detail["definition"]["steps"]
    elapsed = observe("failed-check", expected_name="deliberately-wrong")
    failed = call(
        "musclememory_evaluate",
        {
            "procedure_token": token,
            "run_token": "failed-check",
            "outcome_report": {
                "succeeded": False,
                "procedure_version": version,
                "evidence_event_ids": ["verify"],
            },
            "performance_metrics": {
                "observed": {"tool_calls": 2, "duration_ms": elapsed}
            },
        },
    )
    assert failed["validation_status"] == "flagged"
    assert recall()["no_match"]
    return {
        "tools": sorted(TOOLS),
        "independent_file_reads": 4,
        "checks": 2,
        "operator_approval": True,
        "failure_withholds_recall": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--client", choices=["openhands", "cline"], default="openhands")
    parser.add_argument("--entry", type=Path)
    options = parser.parse_args()
    entry_path = options.entry or ROOT / "integrations/catalog/musclememory.json"
    entry = json.loads(entry_path.read_text())
    if options.client == "cline":
        argv = entry["install"]["args"]
        assert argv[:2] == ["musclememory", "--"]
        command, args = argv[2], argv[3:]
    else:
        transport = entry["connectionOptions"][0]["transport"]
        assert transport["kind"] == "stdio"
        command, args = transport["command"], transport["args"]
    assert args == ["--python", "3.12", "--from", PACKAGE, "musclememory", "stdio"]
    assert shutil.which(command) and shutil.which("uv"), (
        "Install uv/uvx and put them on PATH"
    )
    with tempfile.TemporaryDirectory(prefix="musclememory-catalog-proof-") as folder:
        home = Path(folder)
        env = {
            key: os.environ[key]
            for key in (
                "HOME",
                "PATH",
                "TMPDIR",
                "UV_CACHE_DIR",
                "UV_PYTHON_INSTALL_DIR",
            )
            if key in os.environ
        }
        env["MM_HOME"] = str(home / "memory")
        cache = (
            Path(os.environ.get("UV_CACHE_DIR", home / "cache")) / "musclememory-models"
        )
        env["MM_EMBEDDING_CACHE_DIR"] = str(cache)
        prefix = [command, *args[:-1]]
        run([*prefix, "init"], env)
        agent = json.loads(
            run(
                [
                    *prefix,
                    "key",
                    "--label",
                    options.client,
                    "--permissions",
                    "read,write",
                ],
                env,
            )
        )
        admin = json.loads(
            run(
                [
                    *prefix,
                    "key",
                    "--label",
                    "test-operator",
                    "--permissions",
                    "read,write,delete,admin",
                ],
                env,
            )
        )
        manifest = home / "manifest.json"
        manifest.write_text(json.dumps({"name": "catalog-fixture"}))

        def operator(token):
            code = """import os
from musclememory.config import Settings
from musclememory.service import MemoryService
service = MemoryService(Settings.from_env())
principal = service.authenticate(os.environ['MM_API_KEY'], rate_limit=False)
service.approve(principal, os.environ['MM_PROOF_PROCEDURE'])
service.db.engine.dispose()
"""
            run(
                [
                    "uv",
                    "run",
                    "--no-project",
                    "--python",
                    "3.12",
                    "--with",
                    PACKAGE,
                    "python",
                    "-c",
                    code,
                ],
                {**env, "MM_API_KEY": admin["api_key"], "MM_PROOF_PROCEDURE": token},
            )

        server_env = {**env, "MM_API_KEY": agent["api_key"]}
        if options.client == "openhands":
            import mcp.types
            from openhands.sdk.mcp import MCPServer, create_mcp_tools

            server = MCPServer.model_validate(
                {
                    "transport": "stdio",
                    "command": command,
                    "args": args,
                    "env": server_env,
                }
            )
            with create_mcp_tools({"musclememory": server}, timeout=180) as client:
                assert {tool.name for tool in client.tools} == TOOLS

                def call(name, arguments):
                    result = client.call_async_from_sync(
                        client.call_tool_mcp,
                        name=name,
                        arguments=arguments,
                        timeout=180,
                    )
                    assert not result.isError, result.content
                    return result.structuredContent or json.loads(
                        "\n".join(
                            block.text
                            for block in result.content
                            if isinstance(block, mcp.types.TextContent)
                        )
                    )

                evidence = workflow(call, operator, manifest)
        else:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client

            async def probe():
                from concurrent.futures import ThreadPoolExecutor

                loop = asyncio.get_running_loop()
                params = StdioServerParameters(
                    command=command, args=args, env=server_env
                )
                async with stdio_client(params) as streams:
                    async with ClientSession(*streams) as client:
                        initialized = await client.initialize()
                        assert initialized.serverInfo.version == "0.1.7"
                        assert {
                            tool.name for tool in (await client.list_tools()).tools
                        } == TOOLS

                        def call(name, arguments):
                            result = asyncio.run_coroutine_threadsafe(
                                client.call_tool(name, arguments), loop
                            ).result(timeout=180)
                            assert not result.isError, result.content
                            return result.structuredContent or json.loads(
                                "\n".join(
                                    block.text
                                    for block in result.content
                                    if block.type == "text"
                                )
                            )

                        with ThreadPoolExecutor(max_workers=1) as pool:
                            return await loop.run_in_executor(
                                pool, workflow, call, operator, manifest
                            )

            evidence = asyncio.run(probe())
        print(
            json.dumps(
                {"client": options.client, "release": "0.1.7", **evidence},
                sort_keys=True,
            )
        )
        print(
            "PASS: released stdio command -> five tools -> real file reads -> learned -> two checks -> operator approval -> recall/inspect -> failed check withholds recall"
        )


if __name__ == "__main__":
    main()
