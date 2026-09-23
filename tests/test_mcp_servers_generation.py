"""Assert MCP server.json artifacts generated from the integration catalog.

The integration catalog (``integrations/catalog/*.json``) is the only hand-authored
source of truth; ``integrations/mcp-servers/<id>.json`` and its static import
index are one-way generated build output from ``scripts/build-mcp-servers.mjs``.
These tests pin the mapping contract (remote transports, npm/pypi/oci stdio
packages, namespaced ``_meta`` preservation) and enforce that checked-in
artifacts stay in sync with the catalog.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import openhands_extensions
import pytest
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
CATALOG_DIR = ROOT / "integrations" / "catalog"
SERVERS_DIR = ROOT / "integrations" / "mcp-servers"
SCHEMA_PATH = ROOT / "tests" / "fixtures" / "mcp-server.schema.json"
GENERATOR = ROOT / "scripts" / "build-mcp-servers.mjs"
NAMESPACE = "dev.openhands"

_SCHEMA = json.loads(SCHEMA_PATH.read_text())
VALIDATOR = Draft7Validator(_SCHEMA)


def _catalog_files() -> dict[str: , dict]:
    return {p.stem: json.loads(p.read_text()) for p in sorted(CATALOG_DIR.glob("*.json"))}


def _artifact_files() -> dict[str, dict]:
    """Generated server.json artifacts keyed by catalog id (excluding index.js)."""
    return {
        path.stem: json.loads(path.read_text())
        for path in sorted(SERVERS_DIR.glob("*.json"))
    }


def _supports_mcp(entry: dict) -> bool:
    return any(o.get("provider") == "mcp" for o in entry["connectionOptions"])


def _expect_generated(entry: dict) -> bool:
    """An entry is generated when at least one MCP option maps cleanly."""
    options = [o for o in entry["connectionOptions"] if o.get("provider") == "mcp"]
    for option in options:
        t = option["transport"]
        if t["kind"] in ("shttp", "sse"):
            return True
        if t["kind"] == "stdio":
            if _stdio_maps_to_package(option):
                return True
    return False


def _stdio_maps_to_package(option: dict) -> bool:
    t = option["transport"]
    args = t.get("args", [])
    if t.get("command") == "npx":
        spec = args[1] if len(args) > 1 else ""
        return args[:1] == ["-y"] and not spec.startswith("github:")
    if t.get("command") == "uvx":
        spec = args[1] if args[:1] == ["--from"] else (args[0] if args else "")
        return bool(spec)
    if t.get("command") == "docker":
        return args[:1] == ["run"]and bool(args)
    return False


def _mcp_options(entry: dict) -> list[dict]:
    return [o for o in entry["connectionOptions"] if o.get("provider") == "mcp"]


@pytest.mark.parametrize("id", [p.stem for p in sorted(SERVERS_DIR.glob("*.json"))])
def test_every_generated_artifact_validates_against_mcp_schema(id: str) -> None:
    doc = json.loads((SERVERS_DIR / f"{id}.json").read_text())
    errors = sorted(VALIDATOR.iter_errors(doc), key=lambda e: list(e.path))
    assert not errors, f"{id}.json failed MCP schema validation:\n" + "\n".join(
        f"  - at {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors
    )


def test_artifacts_match_catalog_set() -> None:
    catalog = _catalog_files()
    generated = _artifact_files()
    expected = {
        cid
        for cid, entry in catalog.items()
        if _supports_mcp(entry) and _expect_generated(entry)
    }
    assert set(generated) == expected


def test_http_only_entries_are_not_generated() -> None:
    catalog = _catalog_files()
    generated = _artifact_files()
    http_only = {
        cid for cid, entry in catalog.items() if not _supports_mcp(entry)
    }
    assert http_only.isdisjoint(generated)

    # Unmapped stdio entries (e.g. npx github shorthand) are also skipped.
    quickbooks = catalog["quickbooks"]
    assert _supports_mcp(quickbooks)
    assert "quickbooks" not in generated


def test_remote_transport_mapping() -> None:
    generated = _artifact_files()

    deepwiki = generated["deepwiki"]
    assert deepwiki["remotes"] == [
        {"type": "streamable-http", "url": "https://mcp.deepwiki.com/mcp"}
    ]

    slack = generated["slack"]
    assert {"type": "streamable-http", "url": "https://mcp.slack.com/mcp"
    } in slack["remotes"]


def test_stdio_npm_mapping() -> None:
    filesystem = _artifact_files()["filesystem"]

    (package,) = filesystem["packages"]
    assert package["registryType"] == "npm"
    assert package["identifier"] == "@modelcontextprotocol/server-filesystem"
    assert package["runtimeHint"] == "npx"
    assert package["transport"] == {"type": "stdio"}
    (paths_arg,) = package["packageArguments"]
    assert paths_arg["type"] == "positional"
    assert paths_arg["valueHint"] == "paths"
    assert paths_arg["isRepeated"] is True


def test_stdio_pypi_mapping() -> None:
    atlassian = _artifact_files()["atlassian"]
    packages = atlassian["packages"]
    assert any(
        p["registryType"] == "pypi" and p["identifier"] == "mcp-atlassian"
        for p in packages
    )


def test_stdio_oci_mapping() -> None:
    reportportal = _artifact_files()["reportportal"]
    (package,) = reportportal["packages"]
    assert package["registryType"] == "oci"
    assert package["identifier"] == "docker.io/reportportal/mcp-server:latest"
    assert package["runtimeHint"] == "docker"
    assert package["transport"] == {"type": "stdio"}


def test_supabase_latest_pin_is_stripped() -> None:
    supabase = _artifact_files()["supabase"]
    (package,) = supabase["packages"]
    assert package["identifier"] == "@supabase/mcp-server-supabase"
    assert "version" not in package


def test_meta_preserves_openhands_metadata() -> None:
    slack = _artifact_files()["slack"]
    meta = slack["_meta"][NAMESPACE]

    assert meta["catalogId"] == "slack"
    assert meta["defaultMcpConnectionOptionId"] == "oauth"
    assert meta["installHint"]
    assert meta["keywords"]
    assert meta["categories"]
    assert meta["notes"]
    connection_options = meta["connectionOptions"]
    assert isinstance(connection_options, list)
    assert all("provider" in o for o in connection_options)


def test_description_truncation_preserves_original() -> None:
    atlassian_rovo = _artifact_files()["atlassian-rovo"]
    assert len(atlassian_rovo["description"]) <= 100
    assert (
        atlassian_rovo["_meta"][NAMESPACE]["originalDescription"]
        == _catalog_files()["atlassian-rovo"]["description"]
    )


def test_js_accessors_read_generated_artifacts() -> None:
    script = f"""
        import {{ listMcpServerArtifacts, getMcpServerArtifact }} from './integrations/index.js';
        const list = listMcpServerArtifacts();
        const first = list[0];
        first.__mutated = true;
        const entry = getMcpServerArtifact('dev.openhands/filesystem');
        entry.__mutated = true;
        process.stdout.write(JSON.stringify({{
          count: listMcpServerArtifacts().length,
          hasName: getMcpServerArtifact('dev.openhands/filesystem')?.name === 'dev.openhands/filesystem',

          independent:
            !('__mutated' in listMcpServerArtifacts()[0]) &&
            !('__mutated' in getMcpServerArtifact('dev.openhands/filesystem')),
        }}));
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    payload = json.loads(result.stdout)
    assert payload["count"] == len(_artifact_files())
    assert payload["hasName"] is True
    assert payload["independent"] is True


def test_python_accessors_read_generated_artifacts() -> None:
    artifacts = openhands_extensions.list_mcp_server_artifacts()
    assert len(artifacts) == len(_artifact_files())
    assert all(
        "name" in a and a["name"].startswith(f"{NAMESPACE}/") for a in artifacts
    )
    assert (
        openhands_extensions.get_mcp_server_artifact("dev.openhands/filesystem")[
            "name"
        ]
        == "dev.openhands/filesystem"
    )
    assert openhands_extensions.get_mcp_server_artifact("nope") is None

    # Independent copies.

    artifacts[0]["__mutated"] = True
    assert "__mutated" not in openhands_extensions.list_mcp_server_artifacts()[0]


def test_generated_artifacts_are_in_sync_with_catalog() -> None:
    result = subprocess.run(
        ["node", "scripts/build-mcp-servers.mjs", "--check"],
        capture_output=True,
        text=True,
        cwd=ROOT,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_generator_is_deterministic_on_synthetic_entries() -> None:
    """Pin the mapping contract with synthetic entries, including sse transports."""
    script = f"""
        import {{ buildArtifacts }} from './scripts/build-mcp-servers.mjs';
        const entries = [
          {{
            id: 'sse-demo',
            name: 'SSE Demo',
            description: 'Demo SSE server',
            docsUrl: 'https://example.com/docs',
            connectionOptions: [
              {{
                id: 'none',
                provider: 'mcp',
                transport: {{ kind: 'sse', url: 'https://example.com/mcp' }},
                auth: {{ strategy: 'none' }},
              }},
            ],
          }},
          {{
            id: 'npx-demo',
            name: 'Npx Demo',
            description: 'Demo npx server',

            docsUrl: 'https://github.com/example/npx-demo/tree/main/src/server',
            connectionOptions: [
              {{
                id: 'api',
                provider: 'mcp',
                transport: {{
                  kind: 'stdio',
                  serverName: 'demo',
                  command: 'npx',
                  args: ['-y', '@scope/demo-pkg@1.2.3', '--flag'],
                  envFields: [
                    {{ key: 'DEMO_KEY', label: 'Demo key', type: 'password', required: true }},
                  ],
                  argFields: [
                    {{ key: 'target', label: 'Target path', type: 'text', required: true }},
                  ],
                }},
                auth: {{ strategy: 'api_key' }},
              }},
            ],
          }},
        ];
        const artifacts = buildArtifacts(entries);
        const out = [...artifacts.entries()].map(([id, a]) => ({{ id: id, name: a.name, repo: a.repository, remotes: a.remotes, packages: a.packages, meta: a._meta }}));
        process.stdout.write(JSON.stringify(out));
    """
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    payload = json.loads(result.stdout)
    by_id = {entry["id"]: entry for entry in payload}

    sse = by_id["sse-demo"]
    assert sse["name"] == f"{NAMESPACE}/sse-demo"
    assert sse["remotes"] == [{"type": "sse", "url": "https://example.com/mcp"}]

    npx = by_id["npx-demo"]
    assert npx["repo"] == {
        "url": "https://github.com/example/npx-demo",
        "source": "github",
        "subfolder": "src/server",
    }
    (package,) = npx["packages"]
    assert package["registryType"] == "npm"
    assert package["identifier"] == "@scope/demo-pkg"
    assert package["version"] == "1.2.3"
    assert package["runtimeHint"] == "npx"
    assert package["environmentVariables"] == [
        {
            "name": "DEMO_KEY",
            "description": "Demo key",
            "isRequired": True,
            "isSecret": True,
        }
    ]
    assert package["packageArguments"] == [
        {"type": "named", "name": "--flag"},
        {
            "type": "positional",
            "valueHint": "target",
            "description": "Target path",
            "isRequired": True,
            "isSecret": False,
            "isRepeated": False,
        },
    ]
    assert npx["meta"]["dev.openhands"]["catalogId"] == "npx-demo"