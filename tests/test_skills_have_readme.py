"""Test that all skills have a README.md file in their directory."""

import os
from pathlib import Path


def get_skills_directory():
    """Get the path to the skills directory."""
    # Get the directory containing this test file
    test_dir = Path(__file__).parent
    # Go up one level to the repo root, then into skills/
    return test_dir.parent / "skills"


def test_all_skills_have_readme():
    """Verify that every skill directory contains a README.md file."""
    skills_dir = get_skills_directory()
    
    # Get all subdirectories in the skills directory (excluding files)
    skill_dirs = [
        d for d in skills_dir.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    ]
    
    assert len(skill_dirs) > 0, "No skill directories found"
    
    missing_readmes = []
    for skill_dir in skill_dirs:
        readme_path = skill_dir / "README.md"
        if not readme_path.exists():
            missing_readmes.append(skill_dir.name)
    
    assert len(missing_readmes) == 0, (
        f"The following skills are missing README.md: {', '.join(missing_readmes)}"
    )


def test_readme_is_readable():
    """Verify that README.md files are readable (symlinks resolve correctly)."""
    skills_dir = get_skills_directory()
    
    skill_dirs = [
        d for d in skills_dir.iterdir()
        if d.is_dir() and not d.name.startswith('.')
    ]
    
    unreadable_readmes = []
    for skill_dir in skill_dirs:
        readme_path = skill_dir / "README.md"
        if readme_path.exists():
            try:
                content = readme_path.read_text()
                if len(content) == 0:
                    unreadable_readmes.append(f"{skill_dir.name} (empty)")
            except Exception as e:
                unreadable_readmes.append(f"{skill_dir.name} ({e})")
    
    assert len(unreadable_readmes) == 0, (
        f"The following README.md files are unreadable: {', '.join(unreadable_readmes)}"
    )


if __name__ == "__main__":
    test_all_skills_have_readme()
    test_readme_is_readable()
    print("All tests passed!")
