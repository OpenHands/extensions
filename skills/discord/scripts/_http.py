from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class DiscordRateLimitInfo:
    retry_after: float
    is_global: bool
    bucket: str | None
    remaining: str | None
    reset_after: str | None


class DiscordHTTPError(RuntimeError):
    pass


def _read_http_body(error: urllib.error.HTTPError) -> str:
    try:
        raw = error.read()
    except Exception:
        return ""

    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""



def _sanitize_url_for_logs(url: str) -> str:
    """Redact secrets from Discord URLs before logging.

    Incoming webhook URLs include a token in the path. Treat them like secrets.
    """

    try:
        parts = urllib.parse.urlsplit(url)
        path_parts = parts.path.split("/")

        # Redact webhook token if we recognize /webhooks/{id}/{token}.
        # Examples:
        # - https://discord.com/api/webhooks/<id>/<token>
        # - https://discord.com/api/v10/webhooks/<id>/<token>
        if "webhooks" in path_parts:
            i = path_parts.index("webhooks")
            if len(path_parts) > i + 2:
                # path_parts[i+1] is webhook id, i+2 is token
                path_parts[i + 2] = "<redacted>"

        safe_path = "/".join(path_parts)
        return urllib.parse.urlunsplit((parts.scheme, parts.netloc, safe_path, parts.query, parts.fragment))
    except Exception:
        return "<unavailable>"


def _parse_rate_limit_info(*, error: urllib.error.HTTPError, body: str) -> DiscordRateLimitInfo | None:
    if error.code != 429:
        return None

    retry_after: float | None = None
    is_global = False

    if body:
        try:
            parsed = json.loads(body)
            retry_after_val = parsed.get("retry_after")
            if isinstance(retry_after_val, (int, float, str)):
                retry_after = float(retry_after_val)
            is_global = bool(parsed.get("global", False))
        except Exception:
            pass

    if retry_after is None:
        hdr = error.headers.get("Retry-After")
        if hdr is not None:
            try:
                retry_after = float(hdr)
            except ValueError:
                retry_after = None

    if retry_after is None:
        reset_after = error.headers.get("X-RateLimit-Reset-After")
        if reset_after is not None:
            try:
                retry_after = float(reset_after)
            except ValueError:
                retry_after = None

    if retry_after is None:
        return None

    bucket = error.headers.get("X-RateLimit-Bucket")
    remaining = error.headers.get("X-RateLimit-Remaining")
    reset_after_hdr = error.headers.get("X-RateLimit-Reset-After")

    return DiscordRateLimitInfo(
        retry_after=retry_after,
        is_global=is_global,
        bucket=bucket,
        remaining=remaining,
        reset_after=reset_after_hdr,
    )


def post_json(
    *,
    request: urllib.request.Request,
    payload: Mapping[str, object],
    timeout_s: float = 30,
    max_retries: int = 3,
    max_retry_after_s: float = 60.0,
    jitter_s: float = 0.25,
) -> dict[str, object] | None:
    data = json.dumps(payload).encode("utf-8")
    request.data = data

    attempt = 0
    while True:
        attempt += 1
        try:
            with urllib.request.urlopen(request, timeout=timeout_s) as resp:
                body = resp.read().decode("utf-8", errors="replace")
                if not body:
                    return None
                return json.loads(body)
        except urllib.error.HTTPError as e:
            body = _read_http_body(e)
            rl = _parse_rate_limit_info(error=e, body=body)

            if rl is not None and attempt <= max_retries:
                sleep_s = min(max(0.0, rl.retry_after), max_retry_after_s)
                if jitter_s > 0:
                    sleep_s += random.uniform(0.0, jitter_s)
                time.sleep(sleep_s)
                continue

            context_bits = []
            try:
                context_bits.append(f"url={_sanitize_url_for_logs(request.full_url)}")
            except Exception:
                context_bits.append("url=<unavailable>")

            if rl is not None:
                context_bits.append(f"rate_limit_global={rl.is_global}")
                if rl.bucket is not None:
                    context_bits.append(f"rate_limit_bucket={rl.bucket}")
                if rl.remaining is not None:
                    context_bits.append(f"rate_limit_remaining={rl.remaining}")
                if rl.reset_after is not None:
                    context_bits.append(f"rate_limit_reset_after={rl.reset_after}")

            context = (" " + " ".join(context_bits)) if context_bits else ""

            msg = f"HTTP request failed (HTTP {e.code}).{context}"
            if body:
                msg += f" Response: {body[:500]}"
            raise DiscordHTTPError(msg) from e
        except urllib.error.URLError as e:
            raise DiscordHTTPError(f"HTTP request failed ({e}).") from e
