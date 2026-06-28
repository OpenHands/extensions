"""Strict JSON-Schema validation for integrations/catalog/*.json.

Every catalog entry must validate against integrations/catalog.schema.json.
The schema encodes the catalog contract from integrations/index.d.ts plus the
cross-field connectability rules (e.g. an oauth2 HTTP option must carry an
authorizationUrl + tokenUrl; an HTTP option must ship an openApiUrl) so the
class of "entry looks shaped but cannot actually be connected" regressions the
AI reviewer kept catching is now caught in CI.
"""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "integrations" / "catalog.schema.json"
CATALOG_DIR = ROOT / "integrations" / "catalog"

_SCHEMA = json.loads(SCHEMA_PATH.read_text())
VALIDATOR = Draft202012Validator(_SCHEMA)


def _catalog_entries():
    for entry_path in sorted(CATALOG_DIR.glob("*.json")):
        yield pytest.param(
            entry_path,
            id=entry_path.stem,
        )


@pytest.mark.parametrize("entry_path", list(_catalog_entries()))
def test_catalog_entry_validates_against_schema(entry_path: Path) -> None:
    entry = json.loads(entry_path.read_text())
    errors = sorted(VALIDATOR.iter_errors(entry), key=lambda e: list(e.path))
    if errors:
        rendered = "\n".join(
            f"  - at {'/'.join(map(str, e.path)) or '<root>'}: {e.message}"
            for e in errors
        )
        pytest.fail(f"{entry_path.stem} failed schema validation:\n{rendered}")


def test_schema_file_is_valid_draft_2020_12() -> None:
    """The schema itself must be a valid Draft 2020-12 document."""
    Draft202012Validator.check_schema(_SCHEMA)
