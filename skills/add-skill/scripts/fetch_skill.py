#!/usr/bin/env python3
"""
Fetch a skill from a GitHub repository and install it locally.

This script downloads OpenHands skills from GitHub repositories and installs them
into the workspace's .openhands/skills/ directory. It uses git sparse checkout to
efficiently download only the skill directory without cloning the entire repository.

Usage:
    python fetch_skill.py <github-url> <workspace-path> [--force]

Examples:
    # Full GitHub URL with branch
    python fetch_skill.py "https://github.com/OpenHands/skills/tree/main/skills/docker" /workspace
    
    # Simplified URL (assumes 'main' branch)
    python fetch_skill.py "https://github.com/OpenHands/skills/skills/npm" /workspace
    
    # Shorthand format
    python fetch_skill.py "OpenHands/skills/skills/codereview" /workspace

The script will:
1. Parse the GitHub URL to extract owner, repo, branch, and skill path
2. Use git sparse checkout to download only the specified skill directory
3. Validate the skill has a SKILL.md file
4. Copy the skill to <workspace>/.openhands/skills/<skill-name>/
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def parse_github_url(url: str) -> tuple[str, str, str, str]:
    """
    Parse a GitHub URL into its component parts.
    
    Handles multiple URL formats:
    - Full URL: https://github.com/owner/repo/tree/branch/path/to/skill
    - Simple URL: https://github.com/owner/repo/path/to/skill
    - With github.com: github.com/owner/repo/skill-name
    - Shorthand: owner/repo/skill-name
    
    Args:
        url: GitHub URL in any of the supported formats
        
    Returns:
        Tuple of (owner, repo, branch, skill_path)
        - owner: GitHub username or organization
        - repo: Repository name
        - branch: Git branch (defaults to 'main' if not specified)
        - skill_path: Path to the skill directory within the repo
        
    Raises:
        ValueError: If the URL cannot be parsed
    """
    # Step 1: Normalize the URL by removing protocol prefix (https://, http://)
    url = re.sub(r'^https?://', '', url)
    url = url.rstrip('/')
    
    # Step 2: Remove github.com prefix if present
    url = re.sub(r'^github\.com/', '', url)
    
    # Step 3: Try to match full URL pattern with explicit branch
    # Pattern: owner/repo/tree/branch/path/to/skill
    # Example: "OpenHands/skills/tree/main/skills/docker"
    tree_match = re.match(r'^([^/]+)/([^/]+)/tree/([^/]+)/(.+)$', url)
    if tree_match:
        return tree_match.group(1), tree_match.group(2), tree_match.group(3), tree_match.group(4)
    
    # Step 4: Fall back to simple pattern (assumes 'main' branch)
    # Pattern: owner/repo/path/to/skill
    # Example: "OpenHands/skills/skills/docker"
    parts = url.split('/')
    if len(parts) >= 3:
        owner = parts[0]
        repo = parts[1]
        skill_path = '/'.join(parts[2:])
        return owner, repo, 'main', skill_path
    
    raise ValueError(f"Unable to parse GitHub URL: {url}")


def fetch_skill(github_url: str, workspace_path: str, force: bool = False) -> str:
    """
    Fetch a skill from GitHub and install it to the workspace.
    
    This function performs the following steps:
    1. Parses the GitHub URL to extract repository information
    2. Creates a temporary directory for the git operation
    3. Uses git sparse checkout to download only the skill directory (efficient!)
    4. Validates the downloaded content is a valid skill (has SKILL.md)
    5. Copies the skill to the workspace's .openhands/skills/ directory
    
    Args:
        github_url: URL to the skill on GitHub (various formats supported)
        workspace_path: Path to the workspace root directory
        force: If True, overwrite existing skill with same name
        
    Returns:
        Path to the installed skill directory
        
    Raises:
        SystemExit: If skill already exists (without --force), path not found,
                    or skill is invalid (no SKILL.md)
    """
    # Parse the URL to get repository details
    owner, repo, branch, skill_path = parse_github_url(github_url)
    
    # Extract skill name from the path (last component)
    # e.g., "skills/docker" -> "docker"
    skill_name = skill_path.rstrip('/').split('/')[-1]
    
    # Determine the destination directory
    # Skills are installed to: <workspace>/.openhands/skills/<skill-name>/
    dest_dir = Path(workspace_path) / '.openhands' / 'skills' / skill_name
    
    # Check if skill already exists - prevent accidental overwrites
    if dest_dir.exists():
        if not force:
            print(f"⚠️  Skill '{skill_name}' already exists at {dest_dir}")
            print("   Use --force to overwrite")
            sys.exit(1)
        print(f"Removing existing skill at {dest_dir}")
        shutil.rmtree(dest_dir)
    
    # Ensure the parent directory exists (.openhands/skills/)
    dest_dir.parent.mkdir(parents=True, exist_ok=True)
    
    # Use a temporary directory for the git clone operation
    # This keeps the workspace clean and handles cleanup automatically
    with tempfile.TemporaryDirectory() as tmpdir:
        # Build the repository URL
        repo_url = f"https://github.com/{owner}/{repo}.git"
        
        # If GITHUB_TOKEN is available, use it for authentication
        # This enables access to private repositories
        github_token = os.environ.get('GITHUB_TOKEN')
        if github_token:
            repo_url = f"https://{github_token}@github.com/{owner}/{repo}.git"
        
        print(f"Fetching skill '{skill_name}' from {owner}/{repo}...")
        
        # ============================================================
        # Git Sparse Checkout Process
        # ============================================================
        # Sparse checkout allows us to download only specific directories
        # from a repository, rather than the entire repo. This is much
        # faster and uses less bandwidth/disk space.
        #
        # The process:
        # 1. Clone with --filter=blob:none (don't download file contents yet)
        # 2. Clone with --no-checkout (don't populate working directory)
        # 3. Clone with --depth=1 (only get latest commit, no history)
        # 4. Initialize sparse-checkout in cone mode
        # 5. Set the specific path we want
        # 6. Checkout to actually download just those files
        # ============================================================
        
        # Step 1: Clone the repo skeleton (metadata only, no file contents)
        subprocess.run(
            ['git', 'clone', '--filter=blob:none', '--no-checkout', '--depth=1',
             '--branch', branch, repo_url, tmpdir],
            check=True, capture_output=True, text=True
        )
        
        # Step 2: Initialize sparse checkout in "cone" mode
        # Cone mode is more efficient and works with directory patterns
        subprocess.run(
            ['git', '-C', tmpdir, 'sparse-checkout', 'init', '--cone'],
            check=True, capture_output=True, text=True
        )
        
        # Step 3: Specify which directory we want to download
        subprocess.run(
            ['git', '-C', tmpdir, 'sparse-checkout', 'set', skill_path],
            check=True, capture_output=True, text=True
        )
        
        # Step 4: Checkout - this actually downloads the files we specified
        subprocess.run(
            ['git', '-C', tmpdir, 'checkout'],
            check=True, capture_output=True, text=True
        )
        
        # ============================================================
        # Validation and Installation
        # ============================================================
        
        # Verify the skill path exists in the downloaded content
        src_skill_dir = Path(tmpdir) / skill_path
        if not src_skill_dir.exists():
            print(f"❌ Skill path '{skill_path}' not found in repository")
            sys.exit(1)
        
        # Verify this is a valid skill by checking for SKILL.md
        # Every valid OpenHands skill must have a SKILL.md file
        if not (src_skill_dir / 'SKILL.md').exists():
            print(f"❌ No SKILL.md found in '{skill_path}' - not a valid skill")
            sys.exit(1)
        
        # Copy the skill directory to the final destination
        shutil.copytree(src_skill_dir, dest_dir)
    
    print(f"✅ Successfully installed '{skill_name}' to {dest_dir}")
    return str(dest_dir)


def main():
    """
    Command-line entry point for the fetch_skill script.
    
    Parses command-line arguments and invokes fetch_skill() with appropriate
    error handling. Exits with code 1 on any error.
    """
    parser = argparse.ArgumentParser(
        description='Fetch a skill from a GitHub repository and install it locally.',
        epilog='''
Examples:
  %(prog)s "https://github.com/OpenHands/skills/tree/main/skills/docker" /workspace
  %(prog)s "OpenHands/skills/skills/npm" /workspace
  %(prog)s "owner/repo/my-skill" /workspace --force
        '''
    )
    parser.add_argument(
        'url',
        help='GitHub URL to the skill directory (supports full URLs, github.com URLs, or owner/repo/path shorthand)'
    )
    parser.add_argument(
        'workspace',
        help='Path to the workspace root where the skill will be installed (to .openhands/skills/)'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Overwrite existing skill if it already exists'
    )
    
    args = parser.parse_args()
    
    try:
        fetch_skill(args.url, args.workspace, args.force)
    except subprocess.CalledProcessError as e:
        # Git command failed - show the error message from git
        print(f"❌ Git error: {e.stderr if e.stderr else e}")
        sys.exit(1)
    except Exception as e:
        # Any other unexpected error
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
