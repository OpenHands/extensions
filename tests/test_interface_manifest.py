"""The production Automation interface manifest and its schema.

`interface.json` states the domain-level facts of the Automation interface;
`interface.schema.json` is its authoritative contract. These tests hold the
manifest to its schema, the schema to the same trust rules as the catalog's,
and the manifest's cross-file references to the catalog.
"""

import copy
import json
import subprocess
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
AUTOMATIONS = ROOT / "automations"
SCHEMA = json.loads((AUTOMATIONS / "interface.schema.json").read_text())
MANIFEST = json.loads((AUTOMATIONS / "interface.json").read_text())


def _validate(document):
    jsonschema.Draft202012Validator(SCHEMA).validate(document)


def _with(mutation):
    document = copy.deepcopy(MANIFEST)
    mutation(document)
    return document


def test_schema_is_a_valid_draft_2020_12_schema():
    jsonschema.Draft202012Validator.check_schema(SCHEMA)


def test_manifest_validates_against_its_schema():
    _validate(MANIFEST)


def test_featured_automations_resolve_to_catalog_entries():
    for automation_id in MANIFEST["featuredAutomationIds"]:
        manifest = AUTOMATIONS / "catalog" / automation_id / "manifest.json"
        assert manifest.is_file(), automation_id


@pytest.mark.parametrize(
    ("case", "mutation"),
    [
        ("an unknown version", lambda doc: doc.update(version="2.0")),
        (
            "markup in copy",
            lambda doc: doc["navigation"]["sidebar"].update(
                label="<b>Automate</b>"
            ),
        ),
        (
            "a docs link outside the product documentation",
            lambda doc: doc.update(docsUrl="https://evil.example/"),
        ),
        (
            "an endpoint naming a host",
            lambda doc: doc["endpoints"].update(list="https://evil.example/v1"),
        ),
        (
            "an id endpoint without its {id} substitution",
            lambda doc: doc["endpoints"].update(detail="/v1/latest"),
        ),
        (
            "a key the contract does not define",
            lambda doc: doc.update(dashboards=[]),
        ),
        (
            "constraints on a non-number attribute",
            lambda doc: doc["attributes"]["name"].update(
                constraints={"max": 50}
            ),
        ),
    ],
)
def test_schema_rejects(case, mutation):
    with pytest.raises(jsonschema.ValidationError):
        _validate(_with(mutation))


def test_direct_entries_carry_a_fallback_message():
    """Both direct entries seed the conversation the host offers when the
    deployment cannot run the direct path, within the assisted-message cap."""
    for entry_id in ("github-pr-reviewer", "github-repo-monitor"):
        manifest = json.loads(
            (AUTOMATIONS / "catalog" / entry_id / "manifest.json").read_text()
        )
        message = manifest["setup"].get("message", "")
        assert message, entry_id
        assert len(message) <= 2000, entry_id


def test_node_package_exports_the_interface():
    script = """
      import { AUTOMATION_INTERFACE } from './index.js';
      if (AUTOMATION_INTERFACE?.version !== '1.0') process.exit(1);
      if (AUTOMATION_INTERFACE.endpoints.createPrompt !== '/v1/preset/prompt') process.exit(1);
      if (AUTOMATION_INTERFACE.routes.setup !== '/automations/new/:automationId') process.exit(1);
    """
    subprocess.run(
        ["node", "--input-type=module", "-e", script], cwd=ROOT, check=True
    )
