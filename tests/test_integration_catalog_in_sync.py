"""Assert the checked-in ``oauth-provider-catalog.json`` asset stays in sync
with the JavaScript authoring source, and that the Python package reads the
same data.

The JSON asset is the single source of truth shared by the JS and Python
packages. It is generated from the JS source by
``scripts/build-integration-catalog.mjs``. This test regenerates it and
asserts the checked-in copy matches, so a catalog edit that forgets to
re-run the build fails CI.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import openhands_extensions

ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "integrations" / "oauth-provider-catalog.json"
BUILD_SCRIPT = ROOT / "scripts" / "build-integration-catalog.mjs"


def _run_node_dump() -> dict:
    """Regenerate the catalog via the JS build script and return it parsed."""
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "-e",
            (
                "import { buildCatalog } from "
                f"{BUILD_SCRIPT.as_posix()!r};\n"
                "process.stdout.write(JSON.stringify(buildCatalog()));"
            ),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_checked_in_asset_matches_js_source() -> None:
    """The committed JSON must equal a fresh build from the JS source."""
    regenerated = _run_node_dump()
    checked_in = json.loads(ASSET.read_text())
    assert checked_in == regenerated, (
        "integrations/oauth-provider-catalog.json is out of sync with the JS "
        "source. Run `npm run build:integration-catalog` and commit the result."
    )


def test_python_reads_the_same_asset() -> None:
    """The Python package must load the checked-in JSON asset verbatim."""
    checked_in = json.loads(ASSET.read_text())
    assert openhands_extensions.INTEGRATION_CATALOG_SNAPSHOT == checked_in


def test_python_list_oauth_provider_catalog_matches_asset() -> None:
    checked_in = json.loads(ASSET.read_text())
    assert openhands_extensions.list_oauth_provider_catalog() == checked_in["providers"]


def test_python_default_managed_connectors_match_asset() -> None:
    checked_in = json.loads(ASSET.read_text())
    assert (
        openhands_extensions.default_managed_connectors()
        == checked_in["defaultManagedConnectors"]
    )


def test_get_oauth_provider_registration_defaults_round_trip() -> None:
    for provider in openhands_extensions.list_oauth_provider_catalog():
        slug = provider["slug"]
        defaults = openhands_extensions.get_oauth_provider_registration_defaults(slug)
        assert defaults == provider["registrationDefaults"]


def test_get_oauth_provider_registration_defaults_unknown_slug() -> None:
    assert openhands_extensions.get_oauth_provider_registration_defaults("nope") is None


def test_python_asset_is_byte_identical_to_root_asset() -> None:
    """The Python package's bundled asset must be byte-identical to the root
    generated asset. The build script writes both from a single generation
    pass; this guards against a maintainer updating one copy without the other
    (which would ship a stale catalog in the wheel)."""
    root_asset = (ROOT / "integrations" / "oauth-provider-catalog.json").read_bytes()
    py_asset = (
        ROOT / "python" / "openhands_extensions" / "oauth-provider-catalog.json"
    ).read_bytes()
    assert root_asset == py_asset, (
        "Python package asset drifts from the root asset. Re-run "
        "`npm run build:integration-catalog` (it writes both copies)."
    )


def test_accessors_return_independent_copies() -> None:
    """The cached accessors must return independent objects so a caller mutating
    a returned value cannot corrupt the shared cache for other callers."""
    catalog_a = openhands_extensions.list_oauth_provider_catalog()
    catalog_b = openhands_extensions.list_oauth_provider_catalog()
    assert catalog_a == catalog_b
    assert catalog_a is not catalog_b
    catalog_a[0]["__mutated"] = True
    assert "__mutated" not in openhands_extensions.list_oauth_provider_catalog()[0]

    defaults_a = openhands_extensions.get_oauth_provider_registration_defaults("github")
    assert defaults_a is not None
    defaults_a["__mutated"] = True
    defaults_b = openhands_extensions.get_oauth_provider_registration_defaults("github")
    assert defaults_b is not None
    assert "__mutated" not in defaults_b

    connectors_a = openhands_extensions.default_managed_connectors()
    connectors_b = openhands_extensions.default_managed_connectors()
    assert connectors_a is not connectors_b
