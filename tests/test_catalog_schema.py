"""Strict JSON-Schema validation for integrations/catalog/*.json.

Every catalog entry must validate against integrations/catalog.schema.json.
The schema encodes the catalog contract from integrations/index.d.ts plus the
cross-field connectability rules (e.g. an oauth2 HTTP option must carry an
authorizationUrl + tokenUrl; an HTTP option must ship an openApiUrl) so the
class of "entry looks shaped but cannot actually be connected" regressions the
AI reviewer kept catching is now caught in CI.
"""

import json
from copy import deepcopy
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


def test_schema_requires_catalog_and_install_metadata() -> None:
    entry = json.loads((CATALOG_DIR / "slack.json").read_text())

    invalid_entries: list[tuple[str, dict]] = []

    missing_docs = deepcopy(entry)
    missing_docs.pop("docsUrl")
    invalid_entries.append(("docsUrl", missing_docs))

    missing_field_type = deepcopy(entry)
    missing_field_type["connectionOptions"][1]["transport"]["envFields"][0].pop("type")
    invalid_entries.append(("type", missing_field_type))

    missing_required_marker = deepcopy(entry)
    missing_required_marker["connectionOptions"][1]["transport"]["envFields"][0].pop(
        "required"
    )
    invalid_entries.append(("required", missing_required_marker))

    missing_principal_mapping = deepcopy(entry)
    missing_principal_mapping["connectionOptions"][0]["connectionModel"][
        "identityMapping"
    ].pop("externalPrincipalIdPath")
    invalid_entries.append(("externalPrincipalIdPath", missing_principal_mapping))

    for field, invalid in invalid_entries:
        errors = list(VALIDATOR.iter_errors(invalid))
        assert any(field in error.message for error in errors), errors


@pytest.mark.parametrize(
    ("entry_id", "resource_type", "cardinality", "selection_mode"),
    [
        ("slack", "workspace", "one", "automatic"),
        ("notion", "workspace", "one", "automatic"),
        ("microsoft-teams", "tenant", "one", "automatic"),
        ("atlassian", "site", "many", "post_auth"),
        ("github", "organization", "many", "post_auth"),
    ],
)
def test_oauth_connection_model_examples(
    entry_id: str,
    resource_type: str,
    cardinality: str,
    selection_mode: str,
) -> None:
    entry = json.loads((CATALOG_DIR / f"{entry_id}.json").read_text())
    oauth_option = next(
        option for option in entry["connectionOptions"] if option["id"] == "oauth"
    )
    model = oauth_option["connectionModel"]

    assert model["resourceType"] == resource_type
    assert model["resourceCardinality"] == cardinality
    assert model["selectionMode"] == selection_mode
