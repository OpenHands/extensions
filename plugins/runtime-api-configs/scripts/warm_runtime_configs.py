#!/usr/bin/env python3
"""Manage warm sandbox configurations on the OpenHands Enterprise runtime-api.

Standard-library-only CLI. Runs on any host with Python 3.9+, including
inside the runtime-api pod on Helm installs.

Environment variables:
    RUNTIME_API_URL   Base URL, e.g. https://runtime-api.example.com
    ADMIN_PASSWORD    Password used for the PBKDF2 challenge/response handshake
    API_KEY           Sent as X-API-Key on read operations. Optional: when
                      unset, list/template log in as admin and fetch the
                      'default' API key over HTTPS via /api/admin/api-keys
    ADMIN_TOKEN       Pre-obtained admin JWT; when set, skips the handshake
    NAMESPACE         Kubernetes namespace, default 'openhands' (bootstrap only)

Exit codes:
    0  success
    1  usage / precondition failure
    2  HTTP or connection error against the runtime-api
"""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


# ---------- HTTP helpers ---------------------------------------------------


def _runtime_api_url() -> str:
    url = os.environ.get("RUNTIME_API_URL", "").rstrip("/")
    if not url:
        _fail(
            "RUNTIME_API_URL is not set. Export it (e.g. "
            "https://runtime-api.<your-base-domain>) or run `bootstrap`."
        )
    return url


def _request(
    path: str,
    method: str = "GET",
    body: Any = None,
    headers: dict[str, str] | None = None,
) -> Any:
    api_url = _runtime_api_url()
    req_headers = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(
        f"{api_url}{path}", method=method, headers=req_headers
    )
    if body is not None:
        req.data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(req) as resp:
            payload = resp.read().decode()
            return json.loads(payload) if payload else {}
    except urllib.error.HTTPError as exc:
        _fail(f"HTTP {exc.code} {method} {path}: {exc.read().decode()}", code=2)
    except urllib.error.URLError as exc:
        _fail(f"Could not connect to {api_url}: {exc.reason}", code=2)


# ---------- Auth -----------------------------------------------------------


def _api_key() -> str:
    key = os.environ.get("API_KEY")
    if key:
        return key
    # No API_KEY exported. If admin creds are available, log in and pull the
    # 'default' key value over HTTPS - the same value bootstrap would extract
    # from the k8s secret. Lets an admin drive the CLI end-to-end with just
    # RUNTIME_API_URL + ADMIN_PASSWORD, no cluster access.
    if not (os.environ.get("ADMIN_TOKEN") or os.environ.get("ADMIN_PASSWORD")):
        _fail(
            "API_KEY is not set, and no ADMIN_PASSWORD (or ADMIN_TOKEN) to "
            "fall back to. Either export API_KEY, or export ADMIN_PASSWORD "
            "so the CLI can fetch the default API key over HTTPS."
        )
    token = _admin_token()
    keys = _request(
        "/api/admin/api-keys",
        headers={"Authorization": f"Bearer {token}"},
    )
    for k in keys or []:
        if k.get("name") == "default":
            return k["key_value"]
    _fail("No API key named 'default' returned by /api/admin/api-keys.")


def _admin_token() -> str:
    """Return a valid admin JWT, using ADMIN_TOKEN if set or logging in."""
    token = os.environ.get("ADMIN_TOKEN")
    if token:
        return token
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        _fail("ADMIN_PASSWORD (or ADMIN_TOKEN) is not set.")

    challenge = _request("/api/admin/challenge")
    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        (challenge["salt"] + challenge["challenge"]).encode(),
        challenge["iterations"],
        dklen=32,
    )
    resp = _request(
        "/api/admin/login",
        method="POST",
        body={
            "challenge": challenge["challenge"],
            "hash": binascii.hexlify(derived).decode(),
        },
    )
    return resp["token"]


# ---------- Subcommand implementations -------------------------------------


def cmd_list(args: argparse.Namespace) -> None:
    resp = _request(
        "/api/warm-runtime-configs", headers={"X-API-Key": _api_key()}
    )
    print(json.dumps(resp["configs"], indent=2))


def cmd_template(args: argparse.Namespace) -> None:
    resp = _request(
        "/api/warm-runtime-configs", headers={"X-API-Key": _api_key()}
    )
    match = next(
        (c for c in resp["configs"] if c.get("name") == args.source), None
    )
    if match is None:
        _fail(f"No configuration named {args.source!r} in the effective set.")

    # Strip identity fields that must not appear in a save body.
    for field in ("name", "source"):
        match.pop(field, None)

    if args.image is not None:
        match["image"] = args.image
    if args.count is not None:
        match["count"] = args.count

    payload = json.dumps(match, indent=2)
    if args.output and args.output != "-":
        with open(args.output, "w") as fh:
            fh.write(payload + "\n")
    else:
        print(payload)


def cmd_save(args: argparse.Namespace) -> None:
    if args.file in (None, "-"):
        raw = sys.stdin.read()
        if not raw.strip():
            _fail("No JSON body on stdin. Pass --file, or pipe JSON in.")
    else:
        with open(args.file) as fh:
            raw = fh.read()
    try:
        body = json.loads(raw)
    except json.JSONDecodeError as exc:
        _fail(f"Invalid JSON: {exc}")

    name = urllib.parse.quote(args.name, safe="")
    token = _admin_token()
    saved = _request(
        f"/api/admin/warm-runtime-configs/{name}",
        method="PUT",
        body=body,
        headers={"Authorization": f"Bearer {token}"},
    )
    print(
        f"Saved {saved['name']} image={saved['image']} count={saved.get('count')}"
    )


def cmd_delete(args: argparse.Namespace) -> None:
    name = urllib.parse.quote(args.name, safe="")
    token = _admin_token()
    resp = _request(
        f"/api/admin/warm-runtime-configs/{name}",
        method="DELETE",
        headers={"Authorization": f"Bearer {token}"},
    )
    print(resp.get("message", f"Deleted {args.name}"))


def cmd_bootstrap(args: argparse.Namespace) -> None:
    if shutil.which("kubectl") is None:
        _fail("kubectl not found on PATH. bootstrap needs cluster access.")

    ns = args.namespace
    lines: list[str] = []

    if not args.skip_url:
        host = _kubectl(
            [
                "get", "ingress", "-n", ns,
                "-l", "app.kubernetes.io/name=runtime-api",
                "-o", "jsonpath={.items[0].spec.rules[0].host}",
            ],
            allow_empty=True,
        )
        if host:
            lines.append(f"export RUNTIME_API_URL=https://{host}")
        else:
            print(
                "# No runtime-api ingress found; export RUNTIME_API_URL manually",
                file=sys.stderr,
            )

    lines.append(
        "export API_KEY="
        + _decode_secret(ns, "default-api-key", "default-api-key")
    )
    lines.append(
        "export ADMIN_PASSWORD="
        + _decode_secret(ns, "admin-password", "admin-password")
    )
    print("\n".join(lines))


# ---------- kubectl helpers (bootstrap only) -------------------------------


def _kubectl(argv: list[str], *, allow_empty: bool = False) -> str:
    try:
        out = subprocess.check_output(["kubectl", *argv], stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as exc:
        _fail(
            f"kubectl {' '.join(argv)} failed:\n{exc.stderr.decode()}",
            code=2,
        )
    text = out.decode().strip()
    if not text and not allow_empty:
        _fail(f"kubectl {' '.join(argv)} returned no output.", code=2)
    return text


def _decode_secret(namespace: str, secret: str, key: str) -> str:
    encoded = _kubectl(
        [
            "get", "secret", secret, "-n", namespace,
            "-o", f"jsonpath={{.data.{key}}}",
        ]
    )
    try:
        return base64.b64decode(encoded).decode()
    except (binascii.Error, ValueError) as exc:
        _fail(f"Could not decode secret {secret}/{key}: {exc}", code=2)


# ---------- Utility --------------------------------------------------------


def _fail(msg: str, *, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="warm_runtime_configs",
        description="Manage warm sandbox configurations on OpenHands Enterprise.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List effective warm runtime configurations.").set_defaults(func=cmd_list)

    t = sub.add_parser(
        "template",
        help="Fetch a config, strip name/source, override image/count, print JSON.",
    )
    t.add_argument("source", help="Name of an existing config to derive from (e.g. v1_current).")
    t.add_argument("--image", help="Override the image field.")
    t.add_argument("--count", type=int, help="Override the count field.")
    t.add_argument("-o", "--output", help="Write to file instead of stdout ('-' = stdout).")
    t.set_defaults(func=cmd_template)

    s = sub.add_parser("save", help="Create or update a configuration (upsert).")
    s.add_argument("name", help="Configuration name (URL identity).")
    s.add_argument(
        "--file", "-f",
        help="Path to JSON body. Use '-' or omit to read from stdin.",
    )
    s.set_defaults(func=cmd_save)

    d = sub.add_parser("delete", help="Delete a database-managed configuration.")
    d.add_argument("name", help="Configuration name to delete.")
    d.set_defaults(func=cmd_delete)

    b = sub.add_parser(
        "bootstrap",
        help="Print `export` lines for RUNTIME_API_URL, API_KEY, ADMIN_PASSWORD.",
    )
    b.add_argument(
        "--namespace", "-n",
        default=os.environ.get("NAMESPACE", "openhands"),
        help="Kubernetes namespace (default: %(default)s).",
    )
    b.add_argument(
        "--skip-url", action="store_true",
        help="Do not emit RUNTIME_API_URL (useful with `kubectl port-forward`).",
    )
    b.set_defaults(func=cmd_bootstrap)

    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
