"""Run an automation script with plugin-spec configuration compatibility."""

from __future__ import annotations

import os
import runpy
import shutil
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: plugin_runner.py <script.py> [args...]")

    here = Path(__file__).resolve().parent
    config_path = os.environ.get("AUTOMATION_CONFIG_PATH")
    if config_path and Path(config_path).is_file():
        shutil.copyfile(config_path, here / "config.json")

    target = here / sys.argv[1]
    sys.argv = [str(target), *sys.argv[2:]]
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
