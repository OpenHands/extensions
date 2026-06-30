import argparse
import json
import os
import tarfile
import tempfile
import urllib.request
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package a build directory and upload it to the OpenHands automation service."
    )
    parser.add_argument("--build-dir", required=True, help="Directory to package")
    parser.add_argument(
        "--openhands-host",
        required=True,
        help="Automation backend base URL, for example https://app.all-hands.dev",
    )
    parser.add_argument(
        "--upload-name",
        default="github-pr-reviewer",
        help="Upload name to send to the automation service",
    )
    parser.add_argument(
        "--api-key-env",
        default="OPENHANDS_AUTOMATION_API_KEY",
        help="Environment variable that stores the automation API key",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_dir = Path(args.build_dir).expanduser().resolve()
    if not build_dir.is_dir():
        raise SystemExit(f"Build directory not found: {build_dir}")

    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise SystemExit(f"Environment variable {args.api_key_env} is not set")

    temp_file = tempfile.NamedTemporaryFile(
        prefix=f"{args.upload_name}-",
        suffix=".tar.gz",
        delete=False,
    )
    temp_file.close()
    tarball_path = Path(temp_file.name)

    with tarfile.open(tarball_path, "w:gz") as tar:
        tar.add(build_dir, arcname=".")

    request = urllib.request.Request(
        f"{args.openhands_host.rstrip('/')}/api/automation/v1/uploads?name={args.upload_name}",
        data=tarball_path.read_bytes(),
        headers={
            "X-Session-API-Key": api_key,
            "Content-Type": "application/gzip",
        },
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        upload_data = json.load(response)

    print(
        json.dumps(
            {
                "tarball_path": upload_data["tarball_path"],
                "local_tarball_path": str(tarball_path),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
