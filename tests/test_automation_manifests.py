"""Contract tests for automations/manifests/*.json and automations/fixtures/*.json.

Two things are checked here that nothing else can catch:

1. Every manifest validates against automations/manifest.schema.json, the way
   integration catalog entries validate against integrations/catalog.schema.json.
2. Running a fixture's form values through its manifest's declared mapping
   reproduces the fixture's request body, byte for byte.

(2) is the point of the fixtures. Form shape and API shape genuinely differ, the
create endpoint is declared extra="forbid", and a mapping mistake is a 422 that
only shows up at creation time. Pinning the mapping to a worked example is what
keeps OpenHands/agent-canvas and OpenHands/automation building against the same
contract.
"""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "automations" / "manifest.schema.json"
MANIFEST_DIR = ROOT / "automations" / "manifests"
FIXTURE_DIR = ROOT / "automations" / "fixtures"
CAPABILITIES_PATH = FIXTURE_DIR / "capabilities.json"
AUTOMATION_INDEX = ROOT / "automations" / "index.js"

_SCHEMA = json.loads(SCHEMA_PATH.read_text())
VALIDATOR = Draft202012Validator(_SCHEMA)

PLACEHOLDER_RE = re.compile(r"\{\{([a-z]+)\.([A-Za-z0-9_.]+)\}\}")

# Anything that looks like a real credential rather than a credential's name.
CREDENTIAL_VALUE_RE = re.compile(
    r"(gh[pousr]_[A-Za-z0-9]{16,}|xox[baprs]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9]{20,})"
)


def _manifests():
    for path in sorted(MANIFEST_DIR.glob("*.json")):
        yield pytest.param(path, id=path.stem)


def _fixture_bundles():
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        if path == CAPABILITIES_PATH:
            continue
        yield pytest.param(path, id=path.stem)


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _manifest_for(bundle: dict) -> dict:
    return _load(MANIFEST_DIR / f"{bundle['manifestId']}.json")


def _catalog_ids(relative_path: str) -> set[str]:
    return {path.stem for path in (ROOT / relative_path).glob("*.json")}


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
    """Apply placeholder substitution to a manifest fragment.

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


def _render_payload(manifest: dict, form_values: dict):
    """The request body the manifest produces for these form values."""
    context = {"form": form_values, "manifest": manifest}
    return _interpolate(manifest["submit"]["payload"], context)


def _render_preflight_body(manifest: dict, form_values: dict):
    payload = _render_payload(manifest, form_values)
    context = {
        "form": form_values,
        "manifest": manifest,
        "submit": {"payload": payload},
    }
    return _interpolate(manifest["validation"]["preflight"]["body"], context)


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


def _field_names(manifest: dict) -> set[str]:
    return {field["name"] for field in manifest["form"]["fields"]}


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


def _reported_fields(manifest: dict, scenario: dict) -> dict[str, str]:
    """Apply errorMap to whatever rejected this scenario, whoever rejected it."""
    error_map = manifest.get("validation", {}).get("onInvalid", {}).get("errorMap", {})
    payload = (
        _render_payload(manifest, scenario["formValues"])
        if "payload" in manifest["submit"] and "formValues" in scenario
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


def _capabilities_satisfied(requires: dict, deployment: dict) -> bool:
    if requires.get("ready") and not deployment.get("ready"):
        return False
    for key in ("triggerKinds", "eventSources", "eventTypes", "features"):
        needed = set(requires.get(key, []))
        if needed and not needed.issubset(set(deployment.get(key, []))):
            return False
    return True


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
            if kind in scenario and scenario.get("matchesManifestPayload", True):
                yield pytest.param(
                    bundle, scenario, id=f"{path.stem}-{scenario['id']}"
                )


@pytest.mark.parametrize("manifest_path", list(_manifests()))
def test_manifest_validates_against_schema(manifest_path: Path) -> None:
    manifest = _load(manifest_path)

    errors = sorted(VALIDATOR.iter_errors(manifest), key=lambda e: list(e.path))

    if errors:
        rendered = "\n".join(
            f"  - at {'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
            for error in errors
        )
        pytest.fail(f"{manifest_path.stem} failed schema validation:\n{rendered}")


def test_schema_file_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(_SCHEMA)


def test_schema_rejects_content_a_manifest_must_never_carry() -> None:
    """The format constraints are the trust boundary, so they are asserted here.

    A manifest is data authored in another repo that tells the host to make HTTP
    calls and render copy. These are the mutations that would turn it into code,
    an arbitrary request, or a credential leak.
    """
    manifest = _load(MANIFEST_DIR / "github-pr-reviewer.json")

    rejected: list[tuple[str, dict]] = []

    with_secret_value = deepcopy(manifest)
    with_secret_value["requires"]["secrets"][0]["value"] = "ghp_notarealtokenvalue00"
    rejected.append(("value", with_secret_value))

    with_markup = deepcopy(manifest)
    with_markup["review"]["title"] = "Review <script>steal()</script>"
    rejected.append(("<script>steal()</script>", with_markup))

    with_absolute_url = deepcopy(manifest)
    with_absolute_url["submit"]["endpoint"]["path"] = "https://elsewhere.example/v1/x"
    rejected.append(("https://elsewhere.example/v1/x", with_absolute_url))

    with_external_redirect = deepcopy(manifest)
    with_external_redirect["submit"]["onSuccess"]["to"] = "https://elsewhere.example"
    rejected.append(("https://elsewhere.example", with_external_redirect))

    with_unknown_action = deepcopy(manifest)
    with_unknown_action["submit"]["action"] = "shell.exec"
    rejected.append(("automation.create", with_unknown_action))

    with_unknown_placeholder = deepcopy(manifest)
    with_unknown_placeholder["submit"]["payload"]["name"] = "{{env.GITHUB_TOKEN}}"
    rejected.append(("{{env.GITHUB_TOKEN}}", with_unknown_placeholder))

    for expected_fragment, invalid in rejected:
        errors = list(VALIDATOR.iter_errors(invalid))
        assert any(expected_fragment in error.message for error in errors), (
            f"schema accepted a manifest it must reject ({expected_fragment}): {errors}"
        )


@pytest.mark.parametrize("manifest_path", list(_manifests()))
def test_manifest_id_matches_filename_and_a_catalog_entry(manifest_path: Path) -> None:
    manifest = _load(manifest_path)

    assert manifest["id"] == manifest_path.stem
    assert manifest["id"] in _catalog_ids("automations/catalog")


@pytest.mark.parametrize("manifest_path", list(_manifests()))
def test_required_integrations_exist_in_the_integration_catalog(
    manifest_path: Path,
) -> None:
    manifest = _load(manifest_path)
    known = _catalog_ids("integrations/catalog")

    required = {
        entry["id"] for entry in manifest.get("requires", {}).get("integrations", [])
    }

    assert required - known == set()


@pytest.mark.parametrize("manifest_path", list(_manifests()))
def test_form_placeholders_reference_declared_fields(manifest_path: Path) -> None:
    """A {{form.x}} that names no field renders as an empty value at runtime."""
    manifest = _load(manifest_path)
    fields = _field_names(manifest)

    referenced = {
        key
        for value in _iter_strings(manifest)
        for namespace, key in PLACEHOLDER_RE.findall(value)
        if namespace == "form"
    }

    assert referenced - fields == set()


@pytest.mark.parametrize("manifest_path", list(_manifests()))
def test_select_fields_offer_options_inline_or_from_a_capability(
    manifest_path: Path,
) -> None:
    """A select with neither is an empty dropdown the user cannot get past."""
    manifest = _load(manifest_path)
    bound = {
        binding["field"]
        for binding in manifest.get("capabilities", {}).get("bindings", [])
        if binding["constraint"] == "options"
    }

    unusable = [
        field["name"]
        for field in manifest["form"]["fields"]
        if field["type"] == "select"
        and "options" not in field
        and field["name"] not in bound
    ]

    assert unusable == []


@pytest.mark.parametrize("manifest_path", list(_manifests()))
def test_capability_bindings_target_declared_fields(manifest_path: Path) -> None:
    manifest = _load(manifest_path)
    fields = _field_names(manifest)

    bound = {
        binding["field"]
        for binding in manifest.get("capabilities", {}).get("bindings", [])
    }

    assert bound - fields == set()


@pytest.mark.parametrize("manifest_path", list(_manifests()))
def test_error_map_connects_real_payload_paths_to_real_fields(
    manifest_path: Path,
) -> None:
    """Preflight validates the mapped payload, so errors come back keyed by
    payload path. errorMap is what turns those back into highlighted inputs."""
    manifest = _load(manifest_path)
    error_map = manifest.get("validation", {}).get("onInvalid", {}).get("errorMap")
    if not error_map:
        pytest.skip("manifest declares no errorMap")

    fields = _field_names(manifest)
    defaults = {
        field["name"]: field.get("default", "x")
        for field in manifest["form"]["fields"]
    }
    payload = _render_payload(manifest, defaults)

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
    manifest = _manifest_for(bundle)

    rendered = _render_payload(manifest, scenario["formValues"])

    assert rendered == scenario["create"]["request"]["body"]
    assert scenario["create"]["request"]["path"] == manifest["submit"]["endpoint"]["path"]


@pytest.mark.parametrize(("bundle", "scenario"), list(_scenarios("preflight")))
def test_preflight_body_reproduces_the_preflight_request(
    bundle: dict, scenario: dict
) -> None:
    manifest = _manifest_for(bundle)

    rendered = _render_preflight_body(manifest, scenario["formValues"])

    assert rendered == scenario["preflight"]["request"]["body"]
    assert (
        scenario["preflight"]["request"]["path"]
        == manifest["validation"]["preflight"]["path"]
    )


@pytest.mark.parametrize(("bundle", "scenario"), list(_scenarios("conversation")))
def test_seed_message_reproduces_the_conversation_request(
    bundle: dict, scenario: dict
) -> None:
    manifest = _manifest_for(bundle)

    rendered = _interpolate(
        manifest["submit"]["message"],
        {"form": scenario["formValues"], "manifest": manifest},
    )

    assert rendered == scenario["conversation"]["request"]["message"]


@pytest.mark.parametrize(("bundle", "scenario"), list(_scenarios("expectedReviewSummary")))
def test_review_summary_substitutes_empty_values(bundle: dict, scenario: dict) -> None:
    """Optional fields left blank must read as the declared emptyValueText,
    not as a blank row the user cannot interpret."""
    manifest = _manifest_for(bundle)
    empty_text = manifest["review"].get("emptyValueText")
    context = {"form": scenario["formValues"], "manifest": manifest}

    rendered = []
    for row in manifest["review"]["summary"]:
        value = _interpolate(row["value"], context)
        rendered.append(
            {"label": row["label"], "value": value.strip() or empty_text}
        )

    assert rendered == scenario["expectedReviewSummary"]


@pytest.mark.parametrize(("bundle", "scenario"), list(_scenarios("expectedFieldErrors")))
def test_error_map_turns_rejections_into_highlighted_inputs(
    bundle: dict, scenario: dict
) -> None:
    """The whole two-tier validation design rests on this translation: whoever
    rejects the draft, the user must end up looking at the input at fault."""
    manifest = _manifest_for(bundle)

    reported = _reported_fields(manifest, scenario)

    assert set(reported) <= _field_names(manifest)
    assert reported == scenario["expectedFieldErrors"]


@pytest.mark.parametrize("fixture_path", list(_fixture_bundles()))
def test_blocked_by_lists_exactly_the_unsatisfiable_deployments(
    fixture_path: Path,
) -> None:
    """Keeps capabilities.requires honest: a manifest that claims to work
    everywhere would silently offer a card the deployment cannot run."""
    bundle = _load(fixture_path)
    manifest = _manifest_for(bundle)
    requires = manifest.get("capabilities", {}).get("requires", {})
    responses = _load(CAPABILITIES_PATH)["responses"]

    unsatisfiable = {
        name
        for name, response in responses.items()
        if not _capabilities_satisfied(requires, response["body"])
    }

    assert unsatisfiable == set(bundle["blockedBy"])
    assert _capabilities_satisfied(requires, responses[bundle["capabilities"]]["body"])


def test_every_manifest_has_fixtures_and_both_are_exported() -> None:
    """automations/index.js is hand-maintained, so a new file can otherwise
    ship to npm missing from the package export and no test would notice."""
    manifest_ids = {path.stem for path in MANIFEST_DIR.glob("*.json")}
    fixture_ids = {
        path.stem for path in FIXTURE_DIR.glob("*.json") if path != CAPABILITIES_PATH
    }
    index_source = AUTOMATION_INDEX.read_text()

    assert manifest_ids == fixture_ids
    for manifest_id in sorted(manifest_ids):
        assert f'"./manifests/{manifest_id}.json"' in index_source
        assert f'"./fixtures/{manifest_id}.json"' in index_source
    assert '"./fixtures/capabilities.json"' in index_source


def test_no_manifest_or_fixture_carries_a_credential_value() -> None:
    """Manifests name the secrets an automation needs; they never contain one."""
    offenders = []
    for path in sorted(MANIFEST_DIR.glob("*.json")) + sorted(FIXTURE_DIR.glob("*.json")):
        for value in _iter_strings(_load(path)):
            if CREDENTIAL_VALUE_RE.search(value):
                offenders.append(f"{path.name}: {value[:40]}")

    assert offenders == []
