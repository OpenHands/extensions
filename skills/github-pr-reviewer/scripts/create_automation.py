import argparse
import json
import os
import urllib.request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create an OpenHands automation from a packaged tarball."
    )
    parser.add_argument("--openhands-host", required=True, help="Automation backend base URL")
    parser.add_argument("--name", required=True, help="Automation display name")
    parser.add_argument("--schedule", required=True, help="Cron schedule")
    parser.add_argument("--tarball-path", required=True, help="Uploaded tarball_path value")
    parser.add_argument("--entrypoint", required=True, help="Automation entrypoint command")
    parser.add_argument("--timeout", type=int, required=True, help="Automation timeout in seconds")
    parser.add_argument(
        "--api-key-env",
        default="OPENHANDS_AUTOMATION_API_KEY",
        help="Environment variable that stores the automation API key",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    api_key = os.environ.get(args.api_key_env, "")
    if not api_key:
        raise SystemExit(f"Environment variable {args.api_key_env} is not set")

    payload = {
        "name": args.name,
        "trigger": {"type": "cron", "schedule": args.schedule},
        "tarball_path": args.tarball_path,
        "entrypoint": args.entrypoint,
        "timeout": args.timeout,
    }
    request = urllib.request.Request(
        f"{args.openhands_host.rstrip('/')}/api/automation/v1",
        data=json.dumps(payload).encode(),
        headers={
            "X-Session-API-Key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        automation = json.load(response)

    print(json.dumps(automation, indent=2))


if __name__ == "__main__":
    main()
