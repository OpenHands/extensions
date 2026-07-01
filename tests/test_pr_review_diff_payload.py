"""Tests for the per-file diff payload introduced to replace the global byte-
slice truncation in agent_script.py.

The legacy `truncate_text()` cut the raw diff at byte 100,000, which silently
dropped files whose patches lived past that point (issue #233). These tests
exercise the replacement: a manifest that lists every file plus per-file
budgeted patches that mark abbreviation/omission explicitly.
"""

from __future__ import annotations

# Re-use the module loader from the review-context test file so we don't
# duplicate ~130 lines of openhands-SDK stubbing.
from test_pr_review_review_context import _load_agent_script_module


def _file(
    filename: str,
    *,
    status: str = "modified",
    additions: int = 0,
    deletions: int = 0,
    patch: str | None = "",
    previous_filename: str | None = None,
) -> dict:
    return {
        "filename": filename,
        "status": status,
        "additions": additions,
        "deletions": deletions,
        "patch": patch,
        "previous_filename": previous_filename,
    }


# --- manifest -----------------------------------------------------------


def test_manifest_lists_every_file():
    module = _load_agent_script_module()
    files = [
        _file("a.py", status="added", additions=10),
        _file("b.py", status="modified", additions=2, deletions=3),
        _file("c.py", status="removed", deletions=15),
    ]
    manifest = module.format_files_manifest(files)
    assert "`a.py`" in manifest
    assert "`b.py`" in manifest
    assert "`c.py`" in manifest
    assert "[added]" in manifest
    assert "[modified]" in manifest
    assert "[removed]" in manifest
    assert "+10" in manifest
    assert "+2/-3" in manifest
    assert "-15" in manifest


def test_manifest_includes_totals_in_header():
    module = _load_agent_script_module()
    files = [
        _file("a.py", additions=10, deletions=2),
        _file("b.py", additions=5, deletions=1),
    ]
    manifest = module.format_files_manifest(files)
    assert "2 files" in manifest
    assert "+15" in manifest
    assert "-3" in manifest


def test_manifest_handles_renames():
    module = _load_agent_script_module()
    files = [
        _file(
            "new.py",
            status="renamed",
            additions=1,
            deletions=1,
            previous_filename="old.py",
        ),
    ]
    manifest = module.format_files_manifest(files)
    assert "`new.py`" in manifest
    assert "renamed from old.py" in manifest


def test_manifest_flags_binary_files():
    module = _load_agent_script_module()
    files = [
        _file("logo.png", status="modified", additions=1, deletions=1, patch=""),
    ]
    manifest = module.format_files_manifest(files)
    assert "`logo.png`" in manifest
    assert "binary or unavailable" in manifest


# --- patch formatting ---------------------------------------------------


def test_patches_include_header_for_every_file():
    """Every file gets a diff header even when only a stub fits."""
    module = _load_agent_script_module()
    files = [
        _file("a.py", status="added", additions=1, patch="@@ -0,0 +1 @@\n+x\n"),
        _file("b.py", status="added", additions=1, patch="@@ -0,0 +1 @@\n+y\n"),
    ]
    out = module.format_patches(files)
    assert "diff --git a/a.py b/a.py" in out
    assert "diff --git a/b.py b/b.py" in out


def test_patches_below_budget_passthrough():
    module = _load_agent_script_module()
    patch = "@@ -1,2 +1,2 @@\n-foo\n+bar\n"
    files = [_file("a.py", patch=patch)]
    out = module.format_patches(files, max_total=10000, max_per_file=10000)
    assert patch in out
    assert "[patch abbreviated" not in out


def test_per_file_cap_abbreviates_huge_single_file():
    """A single large patch is abbreviated, not dropped."""
    module = _load_agent_script_module()
    big_patch = "@@ -0,0 +1,1000 @@\n" + "".join(
        f"+line {i}\n" for i in range(1000)
    )
    files = [_file("big.py", status="added", patch=big_patch)]
    out = module.format_patches(files, max_total=100000, max_per_file=500)
    assert "diff --git a/big.py b/big.py" in out
    # The marker is the contract — the agent knows the patch was cut.
    assert "[patch abbreviated" in out
    # Should reference the actual file path so the agent knows where to look.
    assert "`big.py`" in out
    # Must not contain the full patch text.
    assert len(out) < len(big_patch)


def test_total_budget_omits_late_files_with_marker_not_silence():
    """When total budget is exhausted, later files become header-only stubs
    with an explicit `[patch omitted]` marker — never silently dropped."""
    module = _load_agent_script_module()
    fat_patch = "@@ -0,0 +1,100 @@\n" + "".join(f"+x{i}\n" for i in range(100))
    files = [
        _file("first.py", status="added", patch=fat_patch),
        _file("second.py", status="added", patch=fat_patch),
        _file("third.py", status="added", patch=fat_patch),
    ]
    # Budget that comfortably fits one full patch but not three.
    out = module.format_patches(files, max_total=800, max_per_file=10000)

    # All three files appear in the patch block — at minimum as headers.
    assert "diff --git a/first.py b/first.py" in out
    assert "diff --git a/second.py b/second.py" in out
    assert "diff --git a/third.py b/third.py" in out
    # At least one of the later files is marked omitted.
    assert "[patch omitted" in out


def test_no_patch_field_is_annotated_not_silent():
    """A file with no patch text (binary, rename, etc) gets a clear note."""
    module = _load_agent_script_module()
    files = [_file("logo.png", additions=1, deletions=1, patch="")]
    out = module.format_patches(files)
    assert "diff --git a/logo.png b/logo.png" in out
    assert "no patch available" in out


def test_smoking_gun_pr_14401_shape():
    """Regression for issue #233 — the specific failure mode that triggered
    the redesign. Earlier files have huge patches; the implementation file
    of interest sits past the byte-100K mark of the original raw diff. With
    a per-file budget the late file's *patch* may still be abbreviated, but
    its *presence* must always be visible in both manifest and patch block."""
    module = _load_agent_script_module()

    # Two heavy files dominate the byte budget.
    bulk_patch = "@@ -1 +1,2000 @@\n" + "".join(
        f"+filler {i}\n" for i in range(2000)
    )
    # The implementation file the bot kept missing.
    target = (
        "@@ -0,0 +1,55 @@\n"
        + "".join(f"+line {i}\n" for i in range(55))
    )
    files = [
        _file("enterprise/poetry.lock", patch=bulk_patch),
        _file("openhands/long_module.py", patch=bulk_patch),
        _file(
            "frontend/src/utils/shell-tokenize.ts",
            status="added",
            additions=55,
            patch=target,
        ),
    ]

    manifest = module.format_files_manifest(files)
    patches = module.format_patches(files, max_total=2000, max_per_file=600)

    # Manifest always names the target file — this is the property that
    # prevents the bot from claiming the file is missing.
    assert "`frontend/src/utils/shell-tokenize.ts`" in manifest
    # Patch block lists it too, even when its content is abbreviated/omitted.
    assert "diff --git a/frontend/src/utils/shell-tokenize.ts" in patches
