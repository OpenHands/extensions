"""Build the same factory bundle for any supported execution workspace."""

import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path

from extension_workflows import SOURCES, source_root


def build(config_path, output):
    scripts = Path(__file__).parent
    root = source_root()
    files = {
        name: (scripts / name).read_bytes()
        for name in (
            "main.py",
            "extension_workflows.py",
            "scoped_gh.py",
        )
    }
    files["config.json"] = Path(config_path).read_bytes()
    provenance = {}
    for name in SOURCES:
        content = (root / name).read_bytes()
        files["extensions/" + name] = content
        provenance[name] = hashlib.sha256(content).hexdigest()
    files["workflow-sources.json"] = json.dumps(provenance, indent=2).encode()
    with tarfile.open(output, "w:gz") as archive:
        for name, content in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(content)
            info.mode = 0o600
            archive.addfile(info, io.BytesIO(content))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config")
    parser.add_argument("output")
    args = parser.parse_args()
    build(args.config, args.output)
