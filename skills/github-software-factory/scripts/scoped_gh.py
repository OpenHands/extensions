#!/usr/bin/env python3
"""Small gh api transport for an explicitly scoped repository gateway.

The same executable and configuration work in any workspace. This is not a
general replacement for gh; unsupported operations fail rather than bypassing
the gateway. Credentials are never sent to a caller-selected URL.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urlsplit
from urllib.request import Request, urlopen


def gateway_token(config, config_path):
    name = config.get("token_env", "")
    if not re.fullmatch(r"[A-Z_][A-Z0-9_]*", name):
        raise ValueError("Gateway configuration requires a token_env secret reference")
    token = os.environ.get(name)
    path = Path(config_path).parent / ".factory-gateway-token"
    if token:
        # Materialize the one profile-selected grant for later agent tool calls.
        # The artifact stays in this run's workspace, never in an uploaded bundle.
        descriptor = os.open(
            path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(descriptor, "w") as output:
            os.fchmod(output.fileno(), 0o600)
            output.write(token)
        return token
    if path.is_symlink():
        raise ValueError("Gateway credential must not be a symlink")
    token = path.read_text().strip() if path.is_file() else ""
    if not token:
        raise ValueError("Selected gateway credential was not supplied by the profile")
    return token


def repository_path(endpoint, repository):
    prefix = f"repos/{repository}/"
    endpoint = endpoint.lstrip("/")
    if not endpoint.startswith(prefix):
        raise ValueError("Endpoint must be inside the configured repository")
    path = "/" + endpoint[len(prefix) :]
    if any(c in path for c in ("%", "#", "\\")) or any(
        part in (".", "..") for part in urlsplit(path).path.split("/")
    ):
        raise ValueError("Invalid endpoint")
    return path


def main(argv=None, config_path=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["api"])
    parser.add_argument("endpoint")
    parser.add_argument("-X", "--method", default=None)
    parser.add_argument("--input")
    parser.add_argument("--paginate", action="store_true")
    parser.add_argument("--jq", "-q")
    parser.add_argument("-H", "--header", action="append", default=[])
    args = parser.parse_args(argv)
    config_path = config_path or Path(__file__).resolve().parents[1] / "config.json"
    config = json.loads(Path(config_path).read_text())
    path = repository_path(args.endpoint, config["repository"])
    body = None
    if args.input:
        body = json.loads(
            sys.stdin.read() if args.input == "-" else Path(args.input).read_text()
        )
    method = args.method or ("POST" if body is not None else "GET")
    if args.paginate and method != "GET":
        raise ValueError("Pagination is read-only")
    # The gateway intentionally returns JSON, never arbitrary media or URLs.
    if any("diff" in header or "patch" in header for header in args.header):
        raise ValueError("Use GET pulls/NUMBER/files for JSON patches")
    results = []
    for page in range(1, 101):
        current = path
        if args.paginate:
            split = urlsplit(path)
            query = dict(parse_qsl(split.query))
            query.update(per_page="100", page=str(page))
            current = split.path + "?" + urlencode(query)
        request = Request(
            config["broker"],
            method="POST",
            data=json.dumps({"method": method, "path": current, "body": body}).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + gateway_token(config, config_path),
            },
        )
        with urlopen(request, timeout=90) as response:
            result = json.load(response)
        if not args.paginate:
            results = result
            break
        if not isinstance(result, list):
            raise ValueError("Pagination requires an array endpoint")
        results.extend(result)
        if len(result) < 100:
            break
    else:
        raise ValueError("Pagination limit exceeded; result is incomplete")
    encoded = json.dumps(results, indent=2)
    if args.jq:
        subprocess.run(["jq", args.jq], input=encoded, text=True, check=True)
    else:
        print(encoded)


if __name__ == "__main__":
    try:
        main()
    except HTTPError as exc:
        print(
            f"GitHub gateway rejected request ({exc.code}): {exc.read().decode()[:1000]}",
            file=sys.stderr,
        )
        sys.exit(1)
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
