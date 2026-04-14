"""Verify that every slash trigger has a matching Claude Code command file."""

import subprocess
import sys
from pathlib import Path


def test_claude_commands_in_sync():
    """Run sync_claude_commands.py --check and fail if out of sync."""
    script = Path(__file__).parent.parent / "scripts" / "sync_claude_commands.py"
    result = subprocess.run(
        [sys.executable, str(script), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Claude Code command files out of sync:\n{result.stdout}\n{result.stderr}\n"
        f"Run `python scripts/sync_claude_commands.py` to fix."
    )
