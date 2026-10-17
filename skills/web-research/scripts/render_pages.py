#!/usr/bin/env python3
"""Render pages with headless Chromium so post-hydration content is in the DOM.

Many pages return 200 with no useful text in the raw HTML: prices, docs, and
feature tables arrive after JavaScript runs. A raw fetch of such a page looks
like evidence of absence and is not. Render it before concluding anything.

Usage:
    render_pages.py https://example.com/pricing [more URLs ...]
    render_pages.py --url-file urls.txt
    render_pages.py --url-file pages.json      # [{"slug": ..., "url": ...}]

Options:
    --out DIR      output directory (default: rendered)
    --workers N    parallel renders (default: 2)
    --chrome PATH  explicit browser binary
    --timeout N    per-page timeout in seconds (default: 100)

Output: <out>/<slug>.html per page, plus a summary on stderr.

Chromium is discovered via --chrome, then CHROME_BIN, then a Playwright cache,
then PATH. Set CHROME_BIN if none of those finds your browser. Keep --workers
low: headless Chromium is CPU-hungry and oversubscribing it is slower than
running serially.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

DISCOVERY_GLOBS = (
    "~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome",
    "~/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
    "~/.cache/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
    "~/Library/Caches/ms-playwright/chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
)
PATH_NAMES = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome")


def find_chrome(explicit: str | None = None) -> str | None:
    """Return a browser binary path, or None if none can be found."""
    if explicit:
        if os.path.exists(explicit):
            return explicit
        sys.exit(f"--chrome path does not exist: {explicit}")

    env = os.environ.get("CHROME_BIN")
    if env and os.path.exists(env):
        return env

    found: list[str] = []
    for pattern in DISCOVERY_GLOBS:
        found.extend(glob.glob(os.path.expanduser(pattern)))
    if found:
        return sorted(found)[-1]

    for name in PATH_NAMES:
        path = shutil.which(name)
        if path:
            return path
    return None


def slugify(url: str) -> str:
    """Derive a filesystem-safe slug from a URL."""
    stripped = re.sub(r"^[a-zA-Z]+://", "", url)
    slug = re.sub(r"[^A-Za-z0-9]+", "-", stripped).strip("-").lower()
    return slug[:120] or "page"


def render(chrome: str, outdir: str, item: dict, timeout: int) -> tuple[str, str]:
    slug, url = item["slug"], item["url"]
    dst = os.path.join(outdir, f"{slug}.html")
    if os.path.exists(dst) and os.path.getsize(dst) > 5000:
        return slug, "cached"
    cmd = [
        chrome, "--headless=new", "--disable-gpu", "--no-sandbox",
        "--disable-dev-shm-usage", "--hide-scrollbars", "--no-first-run",
        "--disable-extensions", "--disable-sync", "--disable-background-networking",
        "--disable-default-apps", "--mute-audio",
        "--virtual-time-budget=5000", "--dump-dom", url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return slug, "timeout"
    data = proc.stdout.decode("utf-8", "ignore")
    if not data.strip():
        return slug, "empty"
    with open(dst, "w", encoding="utf-8") as handle:
        handle.write(data)
    # Some pages are legitimately tiny, so a small render is flagged rather than
    # discarded -- a thin result should be visible, not silently missing.
    return slug, f"small:{len(data)}" if len(data) < 2000 else f"ok:{len(data)}"


def load_items(args) -> list[dict]:
    if args.url_file:
        raw = open(args.url_file, encoding="utf-8").read().strip()
        if raw.startswith("["):
            entries = json.loads(raw)
            return [{"slug": e.get("slug") or slugify(e["url"]), "url": e["url"]} for e in entries]
        return [{"slug": slugify(line.strip()), "url": line.strip()}
                for line in raw.splitlines() if line.strip()]
    return [{"slug": slugify(u), "url": u} for u in args.urls]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("urls", nargs="*", help="URLs to render")
    ap.add_argument("--url-file", help="file of URLs, one per line, or a JSON [{slug,url}] list")
    ap.add_argument("--out", default="rendered")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--chrome")
    ap.add_argument("--timeout", type=int, default=100)
    args = ap.parse_args()

    items = load_items(args)
    if not items:
        ap.error("no URLs given; pass URLs or --url-file")

    chrome = find_chrome(args.chrome)
    if not chrome:
        print("No Chromium/Chrome binary found.", file=sys.stderr)
        print("Install one, or set CHROME_BIN=/path/to/chrome and retry.", file=sys.stderr)
        print("If you have a browser tool available, prefer it over this script.", file=sys.stderr)
        return 2

    os.makedirs(args.out, exist_ok=True)
    print(f"rendering {len(items)} page(s) with {args.workers} worker(s) via {chrome}", file=sys.stderr)
    results = {}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(render, chrome, args.out, item, args.timeout) for item in items]
        for future in as_completed(futures):
            slug, status = future.result()
            results[slug] = status

    good = sum(1 for s in results.values() if s == "cached" or s.startswith(("ok:", "small:")))
    print(f"rendered ok: {good}/{len(items)}", file=sys.stderr)
    for slug, status in sorted(results.items()):
        if status.startswith("small:"):
            print(f"  WARN {slug}: thin render ({status.split(':')[1]} bytes)", file=sys.stderr)
        elif not (status.startswith("ok:") or status == "cached"):
            print(f"  FAIL {slug}: {status}", file=sys.stderr)
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main())
