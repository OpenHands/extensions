"""Contract tests for the `setup` block in automations/catalog/*/manifest.json.

Two things are checked here that nothing else can catch:

1. Every catalog entry validates against automations/catalog.schema.json, the way
   integration catalog entries validate against integrations/catalog.schema.json.
2. Running a fixture's form values through an entry's declared mapping reproduces
   the fixture's request body, byte for byte.

(2) is the point of the fixtures. Form shape and API shape genuinely differ, the
create endpoint is declared extra="forbid", and a mapping mistake is a 422 that
only shows up at creation time. Pinning the mapping to a worked example is what
keeps OpenHands/agent-canvas and OpenHands/automation building against the same
contract.
"""

import json
import re
import subprocess
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "automations" / "catalog.schema.json"
CATALOG_DIR = ROOT / "automations" / "catalog"
CATALOG_INDEX = ROOT / "automations" / "catalog-index.js"
BUILD_SCRIPT = ROOT / "scripts" / "build-automation-catalog.mjs"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "automations"
CAPABILITIES_PATH = FIXTURE_DIR / "capabilities.json"

_SCHEMA = json.loads(SCHEMA_PATH.read_text())
VALIDATOR = Draft202012Validator(_SCHEMA)

PLACEHOLDER_RE = re.compile(r"\{\{([a-z]+)\.([A-Za-z0-9_.]+)\}\}")

# Anything that looks like a real credential rather than a credential's name.
CREDENTIAL_VALUE_RE = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{16,}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{20,})"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _manifests():
    return sorted(CATALOG_DIR.glob("*/manifest.json"))


def _catalog_paths():
    for path in _manifests():
        yield pytest.param(path, id=path.parent.name)


def _setup_paths():
    """Only the entries that ship a setup block. It is optional by design."""
    for path in _manifests():
        if "setup" in _load(path):
            yield pytest.param(path, id=path.parent.name)


def _fixture_bundles():
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        if path == CAPABILITIES_PATH:
            continue
        yield pytest.param(path, id=path.stem)


def _entry_for(bundle: dict) -> dict:
    return _load(CATALOG_DIR / bundle["automationId"] / "manifest.json")


def _integration_catalog_ids() -> set[str]:
    return {path.stem for path in (ROOT / "integrations" / "catalog").glob("*.json")}


def _resolve(namespace: str, key: str, context: dict):
    """Resolve one {{namespace.key}} placeholder against the render context."""
    if namespace not in context:
        raise KeyError(f"unknown placeholder namespace: {namespace}")
    value = context[namespace]
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(f"unresolved placeholder: {{{{{namespace}.{key}}}}}")
        value = value[part]
    return value


def _interpolate(node, context: dict):
    """Apply placeholder substitution to a setup fragment.

    A string that is exactly one placeholder resolves to the referenced value
    with its type intact, so {{submit.payload}} yields the payload object rather
    than its string repr. Placeholders embedded in longer strings are stringified.
    """
    if isinstance(node, dict):
        return {key: _interpolate(value, context) for key, value in node.items()}
    if isinstance(node, list):
        return [_interpolate(item, context) for item in node]
    if not isinstance(node, str):
        return node

    whole = PLACEHOLDER_RE.fullmatch(node)
    if whole:
        return _resolve(whole.group(1), whole.group(2), context)
    return PLACEHOLDER_RE.sub(
        lambda match: str(_resolve(match.group(1), match.group(2), context)), node
    )


def _context(entry: dict, form_values: dict) -> dict:
    """`automation` resolves against the catalog entry the setup block sits in."""
    return {"form": form_values, "automation": entry}


def _render_payload(entry: dict, form_values: dict):
    """The request body this entry's setup produces for these form values."""
    return _interpolate(
        entry["setup"]["submit"]["payload"], _context(entry, form_values)
    )


def _render_preflight_body(entry: dict, form_values: dict):
    payload = _render_payload(entry, form_values)
    context = _context(entry, form_values) | {"submit": {"payload": payload}}
    return _interpolate(entry["setup"]["validation"]["preflight"]["body"], context)


def _payload_path_exists(payload, path: str) -> bool:
    """Whether an errorMap key such as `repos[0].ref` addresses the payload."""
    node = payload
    for segment in path.split("."):
        name, _, indexes = segment.partition("[")
        if not isinstance(node, dict) or name not in node:
            return False
        node = node[name]
        for index in re.findall(r"\d+", indexes):
            if not isinstance(node, list) or int(index) >= len(node):
                return False
            node = node[int(index)]
    return True


def _fields(setup: dict) -> list[dict]:
    """Every input the form declares, whichever half of it they belong to."""
    triggers = setup["form"].get("triggers", {})
    return [
        field for group in triggers.values() for field in group
    ] + setup["form"]["args"]


def _field_names(setup: dict) -> set[str]:
    return {field["name"] for field in _fields(setup)}


def _join_loc(parts: list[str]) -> str:
    path = ""
    for part in parts:
        if part.isdigit():
            path += f"[{part}]"
        else:
            path += f".{part}" if path else part
    return path


def _loc_to_payload_path(loc: list, payload) -> str:
    """Turn a 422 `loc` into the payload path an errorMap is keyed by.

    FastAPI prefixes `body`, and Pydantic inserts the discriminated-union tag,
    so an invalid cron arrives as ["body", "trigger", "cron", "schedule"] while
    the payload path is `trigger.schedule`. Dropping the segment that does not
    address the payload is what makes the error field-addressable.
    """
    parts = [str(part) for part in loc]
    if parts and parts[0] == "body":
        parts = parts[1:]

    candidates = [parts] + [parts[:i] + parts[i + 1 :] for i in range(len(parts))]
    for candidate in candidates:
        path = _join_loc(candidate)
        if _payload_path_exists(payload, path):
            return path
    return _join_loc(parts)


def _reported_fields(entry: dict, scenario: dict) -> dict[str, str]:
    """Apply errorMap to whatever rejected this scenario, whoever rejected it."""
    setup = entry["setup"]
    error_map = setup.get("validation", {}).get("onInvalid", {}).get("errorMap", {})
    payload = (
        _render_payload(entry, scenario["formValues"])
        if "payload" in setup["submit"] and "formValues" in scenario
        else {}
    )

    reported: dict[str, str] = {}

    for error in scenario.get("localValidation", {}).get("errors", []):
        reported[error["field"]] = error["message"]

    for error in scenario.get("preflight", {}).get("response", {}).get("body", {}).get(
        "errors", []
    ):
        target = error_map.get(error["field"], error["field"])
        for name in [target] if isinstance(target, str) else target:
            reported[name] = error["message"]

    response = scenario.get("create", {}).get("response", {})
    if response.get("status") == 422:
        for detail in response["body"]["detail"]:
            path = _loc_to_payload_path(detail["loc"], payload)
            target = error_map.get(path, path)
            for name in [target] if isinstance(target, str) else target:
                reported[name] = detail["msg"]

    return reported


def _capabilities_satisfied(setup: dict, deployment: dict) -> bool:
    """A deployment can run this automation when it offers every feature the
    setup requires and every trigger kind the form configures."""
    needed_features = set(setup.get("requires", {}).get("features", []))
    if not needed_features.issubset(set(deployment.get("features", []))):
        return False
    needed_kinds = set(setup["form"].get("triggers", {}))
    return needed_kinds.issubset(set(deployment.get("triggerKinds", [])))


def _iter_strings(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _iter_strings(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_strings(item)
    elif isinstance(node, str):
        yield node


def _scenarios(kind: str):
    """Every fixture scenario carrying the given block, as test params."""
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        if path == CAPABILITIES_PATH:
            continue
        bundle = _load(path)
        for scenario in bundle["scenarios"]:
            if kind in scenario and scenario.get("matchesSetupPayload", True):
                yield pytest.param(bundle, scenario, id=f"{path.stem}-{scenario['id']}")


@pytest.mark.parametrize("entry_path", list(_catalog_paths()))
def test_catalog_entry_validates_against_schema(entry_path: Path) -> None:
    entry = _load(entry_path)

    errors = sorted(VALIDATOR.iter_errors(entry), key=lambda e: list(e.path))

    if errors:
        rendered = "\n".join(
            f"  - at {'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        pytest.fail(f"{entry_path.stem} failed schema validation:\n{rendered}")


def test_schema_file_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(_SCHEMA)


def test_schema_rejects_content_a_setup_block_must_never_carry() -> None:
    """The format constraints are the trust boundary, so they are asserted here.

    A setup block is data that tells the host to make HTTP calls and render copy.
    These are the mutations that would turn it into code, an arbitrary request,
    or a credential leak.
    """
    entry = _load(CATALOG_DIR / "github-pr-reviewer" / "manifest.json")

    rejected: list[tuple[str, dict]] = []

    with_markup = deepcopy(entry)
    with_markup["setup"]["review"]["title"] = "Review <script>steal()</script>"
    rejected.append(("<script>steal()</script>", with_markup))

    with_absolute_url = deepcopy(entry)
    with_absolute_url["setup"]["submit"]["endpoint"]["path"] = (
        "https://elsewhere.example/v1/x"
    )
    rejected.append(("https://elsewhere.example/v1/x", with_absolute_url))

    with_external_redirect = deepcopy(entry)
    with_external_redirect["setup"]["submit"]["onSuccess"]["to"] = (
        "https://elsewhere.example"
    )
    rejected.append(("https://elsewhere.example", with_external_redirect))

    with_unknown_action = deepcopy(entry)
    with_unknown_action["setup"]["submit"]["action"] = "shell.exec"
    rejected.append(("automation.create", with_unknown_action))

    with_unknown_placeholder = deepcopy(entry)
    with_unknown_placeholder["setup"]["submit"]["payload"]["name"] = (
        "{{env.GITHUB_TOKEN}}"
    )
    rejected.append(("{{env.GITHUB_TOKEN}}", with_unknown_placeholder))

    for expected_fragment, invalid in rejected:
        errors = list(VALIDATOR.iter_errors(invalid))
        assert any(expected_fragment in error.message for error in errors), (
            f"schema accepted an entry it must reject ({expected_fragment}): {errors}"
        )


@pytest.mark.parametrize("entry_path", list(_setup_paths()))
def test_required_integrations_exist_in_the_integration_catalog(
    entry_path: Path,
) -> None:
    setup = _load(entry_path)["setup"]
    known = _integration_catalog_ids()

    required = {
        entry["id"] for entry in setup.get("requires", {}).get("integrations", [])
    }

    assert required - known == set()


@pytest.mark.parametrize("entry_path", list(_setup_paths()))
def test_form_placeholders_reference_declared_fields(entry_path: Path) -> None:
    """A {{form.x}} that names no field renders as an empty value at runtime."""
    setup = _load(entry_path)["setup"]
    fields = _field_names(setup)

    referenced = {
        key
        for value in _iter_strings(setup)
        for namespace, key in PLACEHOLDER_RE.findall(value)
        if namespace == "form"
    }

    assert referenced - fields == set()


@pytest.mark.parametrize("entry_path", list(_setup_paths()))
def test_select_fields_offer_options(entry_path: Path) -> None:
    """A select without options is an empty dropdown the user cannot get past.
    A field whose options come from the deployment declares a semantic type
    instead, so the host knows to fill it."""
    setup = _load(entry_path)["setup"]

    unusable = [
        field["name"]
        for field in _fields(setup)
        if field["type"] == "select" and "options" not in field
    ]

    assert unusable == []


@pytest.mark.parametrize("entry_path", list(_setup_paths()))
def test_error_map_connects_real_payload_paths_to_real_fields(entry_path: Path) -> None:
    """Preflight validates the mapped payload, so errors come back keyed by
    payload path. errorMap is what turns those back into highlighted inputs."""
    entry = _load(entry_path)
    setup = entry["setup"]
    error_map = setup.get("validation", {}).get("onInvalid", {}).get("errorMap")
    if not error_map:
        pytest.skip("entry declares no errorMap")

    fields = _field_names(setup)
    defaults = {field["name"]: field.get("default", "x") for field in _fields(setup)}
    payload = _render_payload(entry, defaults)

    for path, target in error_map.items():
        assert _payload_path_exists(payload, path), (
            f"errorMap key '{path}' addresses nothing in submit.payload"
        )
        targets = [target] if isinstance(target, str) else target
        assert set(targets) <= fields, f"errorMap '{path}' names unknown fields"


@pytest.mark.parametrize(("bundle", "scenario"), list(_scenarios("create")))
def test_submit_payload_reproduces_the_create_request(
    bundle: dict, scenario: dict
) -> None:
    entry = _entry_for(bundle)

    rendered = _render_payload(entry, scenario["formValues"])

    assert rendered == scenario["create"]["request"]["body"]
    assert (
        scenario["create"]["request"]["path"]
        == entry["setup"]["submit"]["endpoint"]["path"]
    )


@pytest.mark.parametrize(("bundle", "scenario"), list(_scenarios("preflight")))
def test_preflight_body_reproduces_the_preflight_request(
    bundle: dict, scenario: dict
) -> None:
    entry = _entry_for(bundle)

    rendered = _render_preflight_body(entry, scenario["formValues"])

    assert rendered == scenario["preflight"]["request"]["body"]
    assert (
        scenario["preflight"]["request"]["path"]
        == entry["setup"]["validation"]["preflight"]["path"]
    )


@pytest.mark.parametrize(("bundle", "scenario"), list(_scenarios("conversation")))
def test_seed_message_reproduces_the_conversation_request(
    bundle: dict, scenario: dict
) -> None:
    entry = _entry_for(bundle)

    rendered = _interpolate(
        entry["setup"]["submit"]["message"], _context(entry, scenario["formValues"])
    )

    assert rendered == scenario["conversation"]["request"]["message"]


@pytest.mark.parametrize(
    ("bundle", "scenario"), list(_scenarios("expectedReviewSummary"))
)
def test_review_summary_substitutes_empty_values(bundle: dict, scenario: dict) -> None:
    """Optional fields left blank must read as the declared emptyValueText,
    not as a blank row the user cannot interpret."""
    entry = _entry_for(bundle)
    review = entry["setup"]["review"]
    empty_text = review.get("emptyValueText")
    context = _context(entry, scenario["formValues"])

    rendered = []
    for row in review["summary"]:
        value = _interpolate(row["value"], context)
        rendered.append({"label": row["label"], "value": value.strip() or empty_text})

    assert rendered == scenario["expectedReviewSummary"]


@pytest.mark.parametrize(("bundle", "scenario"), list(_scenarios("expectedFieldErrors")))
def test_error_map_turns_rejections_into_highlighted_inputs(
    bundle: dict, scenario: dict
) -> None:
    """The whole two-tier validation design rests on this translation: whoever
    rejects the draft, the user must end up looking at the input at fault."""
    entry = _entry_for(bundle)

    reported = _reported_fields(entry, scenario)

    assert set(reported) <= _field_names(entry["setup"])
    assert reported == scenario["expectedFieldErrors"]


@pytest.mark.parametrize("fixture_path", list(_fixture_bundles()))
def test_blocked_by_lists_exactly_the_unsatisfiable_deployments(
    fixture_path: Path,
) -> None:
    """Keeps requires honest: an entry that claims to work everywhere would
    silently offer a card the deployment cannot run."""
    bundle = _load(fixture_path)
    setup = _entry_for(bundle)["setup"]
    responses = _load(CAPABILITIES_PATH)["responses"]

    unsatisfiable = {
        name
        for name, response in responses.items()
        if not _capabilities_satisfied(setup, response["body"])
    }

    assert unsatisfiable == set(bundle["blockedBy"])
    assert _capabilities_satisfied(setup, responses[bundle["capabilities"]]["body"])


def test_generated_catalog_index_is_up_to_date() -> None:
    """Re-running the codegen script should produce identical output."""
    before = CATALOG_INDEX.read_text()
    subprocess.run(
        ["node", str(BUILD_SCRIPT)], cwd=str(ROOT), check=True, capture_output=True
    )
    assert CATALOG_INDEX.read_text() == before, (
        "automations/catalog-index.js is out of date - run: npm run build:automations"
    )


def test_no_catalog_entry_or_fixture_carries_a_credential_value() -> None:
    """Credentials come from a connected integration, so no entry or fixture
    has any reason to carry one."""
    offenders = []
    for path in _manifests() + sorted(FIXTURE_DIR.glob("*.json")):
        for value in _iter_strings(_load(path)):
            if CREDENTIAL_VALUE_RE.search(value):
                offenders.append(f"{path.name}: {value[:40]}")

    assert offenders == []
