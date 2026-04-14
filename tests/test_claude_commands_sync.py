"""Verify that extensions are in sync (commands, catalog, coverage)."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "sync_extensions.py"


def test_extensions_in_sync():
    """Run sync_extensions.py --check and fail if commands or catalog are stale."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Extensions out of sync:\n{result.stdout}\n{result.stderr}\n"
        f"Run `python scripts/sync_extensions.py` to fix."
    )
