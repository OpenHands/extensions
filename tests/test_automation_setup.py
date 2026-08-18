"""Contract tests for the `setup` block in automations/catalog/*/manifest.json.

Three things are checked here that nothing else can catch:

1. Every catalog entry validates against automations/catalog.schema.json, the way
   integration catalog entries validate against integrations/catalog.schema.json.
2. Running a fixture's form values through an entry's declared mapping reproduces
   the fixture's request body, byte for byte.
3. The parts of that request an entry no longer declares - the preflight body and
   the payload-path-to-field mapping - still come out right when derived. An entry
   states only what varies between automations; everything else is the same code
   for every automation, and these tests are where that code is pinned.

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
BUNDLE_INDEX = ROOT / "automations" / "bundle-index.js"
BUILD_SCRIPT = ROOT / "scripts" / "build-automation-catalog.mjs"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "automations"
CAPABILITIES_PATH = FIXTURE_DIR / "capabilities.json"

# The standardized parts of a direct setup, identical for every automation and
# therefore not declared in any entry. Which create endpoint is used follows
# from what the entry produces: a prompt is a preset, a bundle is a tarball the
# host uploads and then creates from, which is the raw endpoint.
CREATE_PATH = "/v1/preset/prompt"
BUNDLE_CREATE_PATH = "/v1"
BUNDLE_UPLOAD_PATH = "/v1/uploads"
PREFLIGHT_PATH = "/v1/validate"

# Preflight runs while the form is being filled in and the upload happens once,
# at submit, so a bundle draft has no tarball path to send yet. The service
# checks that field's scheme at preflight and its ownership only at creation,
# so a well-formed stand-in validates what preflight is for - the rest of the
# body - without uploading an archive per keystroke.
PREFLIGHT_TARBALL_PATH = "oh-internal://uploads/00000000-0000-0000-0000-000000000000"

# The trigger properties the service accepts, per kind. A form field named
# after one of them fills it; the rest are inputs to the declared filter.
TRIGGER_PROPERTIES = {"cron": ("schedule", "timezone"), "event": ("on",)}

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


def _inlined_bundles() -> dict:
    """The generated bundle index, read as data rather than executed."""
    body = BUNDLE_INDEX.read_text()
    marker = "export const AUTOMATION_BUNDLE_FILES = "
    return json.loads(body[body.index(marker) + len(marker) :].rstrip().rstrip(";"))


def _entry_for(bundle: dict) -> dict:
    return _load(CATALOG_DIR / bundle["automationId"] / "manifest.json")


def _uploaded_path(scenario: dict) -> str:
    """Where a bundle scenario's tarball landed, as the upload step reported it.

    A preset scenario has no upload step and never reads this.
    """
    return (
        scenario.get("upload", {})
        .get("response", {})
        .get("body", {})
        .get("tarball_path", "")
    )


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
    """Apply placeholder substitution to a setup fragment."""
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


def _repo_picker(setup: dict) -> tuple[str | None, dict | None]:
    for name, field in _fields(setup).items():
        if field["type"] == "repo-picker":
            return name, field
    return None, None


def _is_bundle(entry: dict) -> bool:
    """Whether this entry ships a script tarball instead of a prompt."""
    return "bundle" in entry.get("setup", {})


def _create_path(entry: dict) -> str:
    return BUNDLE_CREATE_PATH if _is_bundle(entry) else CREATE_PATH


def _repo_values(setup: dict, form_values: dict) -> list[str]:
    """Every repository the form collected, whether it collects one or many.

    A `multiple` picker holds a list; a single one holds a string. Reading both
    as a list is what keeps the rest of the derivation from branching.
    """
    name, field = _repo_picker(setup)
    if not name:
        return []
    value = form_values.get(name)
    if value is None or value == "":
        return []
    if field and field.get("multiple"):
        return list(value)
    return [value]


def _derive_name(entry: dict, form_values: dict) -> str:
    """The created automation's name. One repository is worth naming; several
    are not, so the count stands in rather than a list that never fits."""
    repos = _repo_values(entry["setup"], form_values)
    if not repos:
        return entry["name"]
    if len(repos) == 1:
        return f"{entry['name']} - {repos[0]}"
    return f"{entry['name']} - {len(repos)} repositories"


def _derive_trigger(entry: dict, form_values: dict) -> dict:
    """The `trigger` object, read off the key and fields under form.triggers."""
    setup = entry["setup"]
    kind, trigger_fields = next(iter(setup["form"]["triggers"].items()))
    trigger = {"type": kind}
    # A field under a trigger kind fills the trigger property of the same name.
    # Anything else there, such as a phrase to match, is an input to `filter`.
    for name in trigger_fields:
        if name in TRIGGER_PROPERTIES[kind]:
            trigger[name] = form_values[name]
    if kind == "event":
        _, repo_field = _repo_picker(setup)
        trigger["source"] = repo_field["provider"]
        trigger["filter"] = _interpolate(setup["filter"], _context(entry, form_values))
    return trigger


def _render_bundle_payload(entry: dict, form_values: dict, tarball_path: str) -> dict:
    """The raw create body a bundle entry produces.

    `tarball_path` is the one value that is neither declared nor derived: the
    host uploads the packed bundle first and creates from what came back. The
    rest follows the same rule as the preset path - only `config` is declared,
    because only the entry knows which key of its own script each field fills.
    """
    bundle = entry["setup"]["bundle"]
    body: dict = {
        "name": _derive_name(entry, form_values),
        "trigger": _derive_trigger(entry, form_values),
        "tarball_path": tarball_path,
        "entrypoint": bundle["entrypoint"],
    }
    if "setupScript" in bundle:
        body["setup_script_path"] = bundle["setupScript"]
    if "timeout" in bundle:
        body["timeout"] = bundle["timeout"]
    body["template"] = {
        "id": entry["id"],
        "version": bundle["version"],
        "config": _interpolate(bundle["config"], _context(entry, form_values)),
    }
    return body


def _render_payload(entry: dict, form_values: dict, tarball_path: str = "") -> dict:
    """The create request body these form values produce.

    No entry declares this. `name` comes from the entry, `repos` from the
    repo-picker field and its provider, and `trigger` from the key and fields
    under `form.triggers`. Only `prompt` (or, for a bundle, `config`) and an
    event `filter` are declared, because only they cannot be read off the form.
    """
    if _is_bundle(entry):
        return _render_bundle_payload(entry, form_values, tarball_path)

    setup = entry["setup"]
    context = _context(entry, form_values)
    _, repo_field = _repo_picker(setup)
    repos = _repo_values(setup, form_values)

    body: dict = {
        "name": _derive_name(entry, form_values),
        "prompt": _interpolate(setup["prompt"], context),
    }

    if repos:
        body["repos"] = [
            {
                "url": repo,
                "provider": repo_field["provider"],
                **({"ref": form_values["ref"]} if "ref" in form_values else {}),
            }
            for repo in repos
        ]

    body["trigger"] = _derive_trigger(entry, form_values)

    return body


def _derive_preflight_body(entry: dict, form_values: dict) -> dict:
    """The preflight body the host sends. The same shape for every automation,
    so no entry declares it."""
    return {
        "automationId": entry["id"],
        "endpoint": _create_path(entry),
        "draft": _render_payload(entry, form_values, PREFLIGHT_TARBALL_PATH),
    }


def _derive_error_map(entry: dict) -> dict[str, list[str]]:
    """Which form fields built each payload path.

    Preflight and the create endpoint reject a draft by payload path, and the
    host has to turn that back into a highlighted input. Building the body with
    each field standing in for its own value recovers the mapping exactly, so
    an entry does not declare it.
    """
    mapping: dict[str, list[str]] = {}
    if "prompt" not in entry["setup"] and not _is_bundle(entry):
        return mapping

    stand_ins = {name: f"{{{{form.{name}}}}}" for name in _field_names(entry["setup"])}
    template = _render_payload(entry, stand_ins)

    def walk(node, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{path}.{key}" if path else key)
        elif isinstance(node, list):
            for index, item in enumerate(node):
                walk(item, f"{path}[{index}]")
        elif isinstance(node, str):
            names = [
                key
                for namespace, key in PLACEHOLDER_RE.findall(node)
                if namespace == "form"
            ]
            if names:
                mapping[path] = list(dict.fromkeys(names))

    walk(template, "")
    return mapping


def _payload_path_exists(payload, path: str) -> bool:
    """Whether an error path such as `repos[0].ref` addresses the payload."""
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


def _fields(setup: dict) -> dict[str, dict]:
    """Every input the form declares, keyed by name, whichever half it is in."""
    fields = {}
    for group in setup["form"].get("triggers", {}).values():
        fields.update(group)
    fields.update(setup["form"]["args"])
    return fields


def _field_names(setup: dict) -> set[str]:
    return set(_fields(setup))


def _join_loc(parts: list[str]) -> str:
    path = ""
    for part in parts:
        if part.isdigit():
            path += f"[{part}]"
        else:
            path += f".{part}" if path else part
    return path


def _loc_to_payload_path(loc: list, payload) -> str:
    """Turn a 422 `loc` into the payload path an error is keyed by.

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
    """Apply the derived error map to whatever rejected this scenario."""
    setup = entry["setup"]
    error_map = _derive_error_map(entry)
    payload = (
        _render_payload(entry, scenario["formValues"], _uploaded_path(scenario))
        if ("prompt" in setup or _is_bundle(entry)) and "formValues" in scenario
        else {}
    )

    reported: dict[str, str] = {}

    for error in scenario.get("localValidation", {}).get("errors", []):
        reported[error["field"]] = error["message"]

    for error in scenario.get("preflight", {}).get("response", {}).get("body", {}).get(
        "errors", []
    ):
        for name in error_map.get(error["field"], [error["field"]]):
            reported[name] = error["message"]

    response = scenario.get("create", {}).get("response", {})
    if response.get("status") == 422:
        for detail in response["body"]["detail"]:
            path = _loc_to_payload_path(detail["loc"], payload)
            for name in error_map.get(path, [path]):
                reported[name] = detail["msg"]

    return reported


def _capabilities_satisfied(entry: dict, deployment: dict) -> bool:
    """A deployment can run this automation when it offers every feature the
    entry requires and every trigger kind the form configures."""
    needed_features = set(entry["requires"].get("features", []))
    if not needed_features.issubset(set(deployment.get("features", []))):
        return False
    needed_kinds = set(entry.get("setup", {}).get("form", {}).get("triggers", {}))
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
        pytest.fail(f"{entry_path.parent.name} failed schema validation:\n{rendered}")


def test_schema_file_is_valid_draft_2020_12() -> None:
    Draft202012Validator.check_schema(_SCHEMA)


def test_schema_rejects_content_a_setup_block_must_never_carry() -> None:
    """The format constraints are the trust boundary, so they are asserted here.

    A setup block is data that tells the host what to render and what request to
    build. These are the mutations that would turn it into code, an arbitrary
    request, or a credential leak.
    """
    entry = _load(CATALOG_DIR / "github-pr-reviewer" / "manifest.json")

    rejected: list[tuple[str, dict]] = []

    with_markup = deepcopy(entry)
    with_markup["setup"]["form"]["args"]["repositories"]["label"] = (
        "Repository <script>steal()</script>"
    )
    rejected.append(("<script>steal()</script>", with_markup))

    with_unknown_placeholder = deepcopy(entry)
    with_unknown_placeholder["setup"]["prompt"] = "Use {{env.GITHUB_TOKEN}}"
    rejected.append(("{{env.GITHUB_TOKEN}}", with_unknown_placeholder))

    with_secret_value = deepcopy(entry)
    with_secret_value["requires"]["integrations"]["github"]["value"] = (
        "ghp_notarealtokenvalue00"
    )
    rejected.append(("value", with_secret_value))

    with_repeated_identity = deepcopy(entry)
    with_repeated_identity["setup"]["description"] = "a second description"
    rejected.append(("description", with_repeated_identity))

    for expected_fragment, invalid in rejected:
        errors = list(VALIDATOR.iter_errors(invalid))
        assert any(expected_fragment in error.message for error in errors), (
            f"schema accepted an entry it must reject ({expected_fragment}): {errors}"
        )


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
        name
        for name, field in _fields(setup).items()
        if field["type"] == "select" and "options" not in field
    ]

    assert unusable == []


@pytest.mark.parametrize(("bundle", "scenario"), list(_scenarios("create")))
def test_derived_body_reproduces_the_create_request(
    bundle: dict, scenario: dict
) -> None:
    """An entry declares the prompt and, for an event trigger, the filter. The
    name, the repository and the trigger come out of the form, and this is
    where that reconstruction is pinned to a body the service accepts."""
    entry = _entry_for(bundle)

    derived = _render_payload(entry, scenario["formValues"], _uploaded_path(scenario))

    assert derived == scenario["create"]["request"]["body"]
    assert scenario["create"]["request"]["path"] == _create_path(entry)


@pytest.mark.parametrize(("bundle", "scenario"), list(_scenarios("preflight")))
def test_derived_preflight_body_reproduces_the_preflight_request(
    bundle: dict, scenario: dict
) -> None:
    """No entry declares the preflight call any more. It has to come out of the
    entry id and the payload, and this is where that is pinned."""
    entry = _entry_for(bundle)

    derived = _derive_preflight_body(entry, scenario["formValues"])

    assert derived == scenario["preflight"]["request"]["body"]
    assert scenario["preflight"]["request"]["path"] == PREFLIGHT_PATH


@pytest.mark.parametrize(("bundle", "scenario"), list(_scenarios("conversation")))
def test_seed_message_reproduces_the_conversation_request(
    bundle: dict, scenario: dict
) -> None:
    entry = _entry_for(bundle)

    rendered = _interpolate(
        entry["setup"]["message"], _context(entry, scenario["formValues"])
    )

    assert rendered == scenario["conversation"]["request"]["message"]


@pytest.mark.parametrize(("bundle", "scenario"), list(_scenarios("expectedFieldErrors")))
def test_derived_error_map_turns_rejections_into_highlighted_inputs(
    bundle: dict, scenario: dict
) -> None:
    """The whole two-tier validation design rests on this translation: whoever
    rejects the draft, the user must end up looking at the input at fault. The
    mapping is derived from the payload, so it cannot drift from it."""
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
    entry = _entry_for(bundle)
    responses = _load(CAPABILITIES_PATH)["responses"]

    unsatisfiable = {
        name
        for name, response in responses.items()
        if not _capabilities_satisfied(entry, response["body"])
    }

    assert unsatisfiable == set(bundle["blockedBy"])
    assert _capabilities_satisfied(entry, responses[bundle["capabilities"]]["body"])


def test_generated_catalog_index_is_up_to_date() -> None:
    """Re-running the codegen script should produce identical output."""
    before = CATALOG_INDEX.read_text()
    bundles_before = BUNDLE_INDEX.read_text()
    subprocess.run(
        ["node", str(BUILD_SCRIPT)], cwd=str(ROOT), check=True, capture_output=True
    )
    assert CATALOG_INDEX.read_text() == before, (
        "automations/catalog-index.js is out of date - run: npm run build:automations"
    )
    assert BUNDLE_INDEX.read_text() == bundles_before, (
        "automations/bundle-index.js is out of date - run: npm run build:automations"
    )


@pytest.mark.parametrize("entry_path", list(_setup_paths()))
def test_bundle_files_exist_and_are_inlined(entry_path: Path) -> None:
    """A bundle names repository paths; the package ships their contents.

    The host packing the tarball has the published package but not this
    repository, so a path that resolves here and nowhere else would produce an
    entry that installs in CI and fails for every user.
    """
    entry = _load(entry_path)
    if not _is_bundle(entry):
        pytest.skip("not a bundle entry")

    bundle = entry["setup"]["bundle"]
    inlined = _inlined_bundles()

    assert set(inlined) >= {entry["id"]}
    for packed_path, source in bundle["files"].items():
        assert (ROOT / source).is_file(), f"{source} does not exist"
        assert inlined[entry["id"]][packed_path] == (ROOT / source).read_text()

    # The entrypoint has to name something the tarball actually contains.
    packed = set(bundle["files"]) | {"config.json"}
    assert any(word in packed for word in bundle["entrypoint"].split()), (
        f"entrypoint {bundle['entrypoint']!r} names no packed file"
    )
    if "setupScript" in bundle:
        assert bundle["setupScript"] in packed


# A bundle is the one part of a manifest naming files and a command the host
# acts on, so the schema is what stands between an entry and the host doing it.
BUNDLE_REJECTIONS = [
    ("a packed path that climbs out of the archive", {"files": {"../main.py": "skills/github-pr-reviewer/scripts/main.py"}}),
    ("a packed path that is a bare dot segment", {"files": {"./main.py": "skills/github-pr-reviewer/scripts/main.py"}}),
    ("a source that traverses out of the repository", {"files": {"main.py": "skills/../../etc/passwd"}}),
    ("a source outside skills/ and automations/", {"files": {"main.py": "python/main.py"}}),
    ("an entrypoint carrying a shell metacharacter", {"entrypoint": "python3 main.py && curl evil.sh"}),
    ("a setup script that climbs out of the archive", {"setupScript": "../setup.sh"}),
    ("a version that is not a semantic version", {"version": "latest"}),
    ("no files at all", {"files": {}}),
]


@pytest.mark.parametrize(
    ("case", "override"),
    [pytest.param(case, override, id=case) for case, override in BUNDLE_REJECTIONS],
)
def test_schema_refuses_an_unsafe_bundle(case: str, override: dict) -> None:
    entry = deepcopy(_load(CATALOG_DIR / "github-pr-reviewer" / "manifest.json"))
    entry["setup"]["bundle"].update(override)

    assert list(VALIDATOR.iter_errors(entry)), f"schema admitted {case}"


def test_a_direct_entry_declares_a_prompt_or_a_bundle_but_not_both() -> None:
    entry = deepcopy(_load(CATALOG_DIR / "github-pr-reviewer" / "manifest.json"))
    entry["setup"]["prompt"] = "Review pull requests."

    assert list(VALIDATOR.iter_errors(entry))

    del entry["setup"]["prompt"]
    del entry["setup"]["bundle"]

    assert list(VALIDATOR.iter_errors(entry))


@pytest.mark.parametrize("entry_path", list(_setup_paths()))
def test_bundle_config_only_reads_declared_form_fields(entry_path: Path) -> None:
    """config.json is the bundle's analogue of the prompt, and the same rule
    applies: a placeholder must name an input the form actually collects."""
    entry = _load(entry_path)
    if not _is_bundle(entry):
        pytest.skip("not a bundle entry")

    names = _field_names(entry["setup"])
    for value in _iter_strings(entry["setup"]["bundle"]["config"]):
        for namespace, key in PLACEHOLDER_RE.findall(value):
            if namespace == "form":
                assert key in names, f"config references unknown field: {key}"


def test_no_catalog_entry_or_fixture_carries_a_credential_value() -> None:
    """Credentials come from a connected integration, so no entry or fixture
    has any reason to carry one."""
    offenders = []
    for path in _manifests() + sorted(FIXTURE_DIR.glob("*.json")):
        for value in _iter_strings(_load(path)):
            if CREDENTIAL_VALUE_RE.search(value):
                offenders.append(f"{path.name}: {value[:40]}")

    assert offenders == []
