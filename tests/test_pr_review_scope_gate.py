"""Guard the repository review guide's leading ownership/scope gate."""

from pathlib import Path

GUIDE_PATH = (
    Path(__file__).parent.parent / ".agents/skills/custom-codereview-guide.md"
)

DOWNSTREAM_CHECKPOINTS = [
    "### Executable instructions and runtime parity",
    "### Untrusted triggers and credentials",
    "### Sources of truth and generated artifacts",
    "### Documentation claims",
    "### Dependencies and supply chain",
    "## Evidence and comment discipline",
]


def get_guide() -> str:
    return GUIDE_PATH.read_text()


def test_scope_gate_precedes_the_technical_checkpoints():
    content = get_guide()
    gate = content.index("## Ownership and scope gate")

    for checkpoint in DOWNSTREAM_CHECKPOINTS:
        assert gate < content.index(checkpoint), checkpoint


def test_gate_names_extensions_owned_work():
    content = get_guide()

    for phrase in [
        "reusable skills and plugins",
        "automation bundles",
        "integration catalogs",
        "public host and runtime capabilities",
    ]:
        assert phrase in content, phrase


def test_gate_names_out_of_scope_owners():
    content = get_guide()

    assert "Runtime, agent-server, and client contracts" in content
    assert "`OpenHands/software-agent-sdk`" in content
    assert (
        "Generic automation scheduling, state, dispatch, and profile selection"
        in content
    )
    assert "`OpenHands/automation`" in content
    assert "Canvas product UI and app integration" in content
    assert "`OpenHands/OpenHands`" in content


def test_gate_keeps_coordinated_stacks_in_scope():
    content = get_guide()

    assert "coordinated cross-repository stack is legitimate" in content
    assert "Judge this PR's own diff" in content
    assert "only reusable extension content" in content


def test_gate_defines_four_maintainer_decision_outcomes():
    content = get_guide()

    for outcome in [
        "Wrong repository",
        "Unresolved product or architecture decision",
        "Obsolete or duplicate",
        "Contrary to current direction",
    ]:
        assert outcome in content, outcome

    assert "Stop before exhaustive code review" in content
    assert "do not approve the PR" in content
    assert "auto-merge" in content


def test_gate_instructs_naming_the_owning_repository():
    content = get_guide()

    assert "name the likely owning repository" in content
    assert "omit the name when the evidence does not" in content


def test_gate_defers_to_existing_downstream_criteria():
    content = get_guide()

    assert "proceeds unchanged through the existing packaging, installation" in content
    assert "permissions, prompt-quality, and test checkpoints below" in content


def test_gate_uses_stable_categories_without_case_history():
    content = get_guide()

    assert "PR #" not in content
    assert "#640" not in content
    assert "#641" not in content


def test_guide_uses_plain_hyphens():
    content = get_guide()

    assert "\u2014" not in content
    assert "\u2013" not in content
