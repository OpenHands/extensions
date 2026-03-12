#!/usr/bin/env python3
"""Test that workflow files in .github/workflows/ match copies in plugins/*/workflows/."""

from pathlib import Path


def test_workflow_files_are_in_sync():
    """Ensure workflow files in .github/workflows/ are identical to copies in plugin dirs."""
    repo_root = Path(__file__).parent.parent
    workflows_dir = repo_root / ".github" / "workflows"

    if not workflows_dir.exists():
        return  # No workflows directory

    mismatches = []
    # Check all plugins/*/workflows/ directories
    for copy_path in repo_root.glob("plugins/*/workflows"):
        if not copy_path.is_dir():
            continue

        for copy_file in copy_path.glob("*.yml"):
            canonical_file = workflows_dir / copy_file.name
            if not canonical_file.exists():
                continue

            canonical_content = canonical_file.read_text()
            copy_content = copy_file.read_text()

            if canonical_content != copy_content:
                rel_path = copy_path.relative_to(repo_root)
                mismatches.append(
                    f"{rel_path}/{copy_file.name} differs from "
                    f".github/workflows/{copy_file.name}"
                )

    if mismatches:
        raise AssertionError(
            "Workflow files are out of sync:\n"
            + "\n".join(f"  - {m}" for m in mismatches)
            + "\n\nRun: cp .github/workflows/<file> <destination> to sync"
        )


if __name__ == "__main__":
    test_workflow_files_are_in_sync()
    print("All workflow files are in sync!")
