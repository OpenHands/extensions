#!/usr/bin/env python3
"""Test that workflow files in .github/workflows/ match any copies elsewhere in the repo."""

import os
from pathlib import Path


def test_workflow_files_are_in_sync():
    """Ensure workflow files in .github/workflows/ are identical to copies elsewhere."""
    repo_root = Path(__file__).parent.parent
    workflows_dir = repo_root / ".github" / "workflows"

    if not workflows_dir.exists():
        return  # No workflows directory

    # Find all workflow files in .github/workflows/
    canonical_workflows = {f.name: f for f in workflows_dir.glob("*.yml")}
    canonical_workflows.update({f.name: f for f in workflows_dir.glob("*.yaml")})

    # Find all other yml/yaml files in the repo that might be workflow copies
    mismatches = []
    for root, dirs, files in os.walk(repo_root):
        # Skip .github/workflows itself and hidden directories
        if ".github/workflows" in root or "/.git" in root:
            continue

        for filename in files:
            if filename in canonical_workflows:
                other_path = Path(root) / filename
                canonical_path = canonical_workflows[filename]

                canonical_content = canonical_path.read_text()
                other_content = other_path.read_text()

                if canonical_content != other_content:
                    rel_path = other_path.relative_to(repo_root)
                    mismatches.append(
                        f"{rel_path} differs from .github/workflows/{filename}"
                    )

    if mismatches:
        raise AssertionError(
            "Workflow files are out of sync:\n" + "\n".join(f"  - {m}" for m in mismatches)
            + "\n\nRun: cp .github/workflows/<file> <destination> to sync"
        )


if __name__ == "__main__":
    test_workflow_files_are_in_sync()
    print("All workflow files are in sync!")
