from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Any, Mapping

import requests


@dataclass(frozen=True)
class DiscordRateLimitInfo:
    retry_after: float
    is_global: bool
    bucket: str | None
    remaining: str | None
    reset_after: str | None


class DiscordHTTPError(RuntimeError):
    pass


def _parse_rate_limit_info(*, status_code: int, headers: Mapping[str, str], json_body: Any) -> DiscordRateLimitInfo | None:
    if status_code != 429:
        return None

    retry_after: float | None = None
    is_global = False

    if isinstance(json_body, dict):
        retry_after_val = json_body.get("retry_after")
        if isinstance(retry_after_val, (int, float, str)):
            try:
                retry_after = float(retry_after_val)
            except ValueError:
                retry_after = None
        is_global = bool(json_body.get("global", False))

    if retry_after is None:
        hdr = headers.get("Retry-After")
        if hdr is not None:
            try:
                retry_after = float(hdr)
            except ValueError:
                retry_after = None

    if retry_after is None:
        reset_after = headers.get("X-RateLimit-Reset-After")
        if reset_after is not None:
            try:
                retry_after = float(reset_after)
            except ValueError:
                retry_after = None

    if retry_after is None:
        return None

    return DiscordRateLimitInfo(
        retry_after=retry_after,
        is_global=is_global,
        bucket=headers.get("X-RateLimit-Bucket"),
        remaining=headers.get("X-RateLimit-Remaining"),
        reset_after=headers.get("X-RateLimit-Reset-After"),
    )


def post_json(
    *,
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, object],
    timeout_s: float = 30,
    max_retries: int = 3,
    max_retry_after_s: float = 60.0,
    jitter_s: float = 0.25,
    redact_url_in_errors: bool = False,
) -> dict[str, object] | None:
    attempt = 0
    while True:
        attempt += 1
        try:
            resp = requests.post(url, headers=dict(headers), json=dict(payload), timeout=timeout_s)
        except requests.RequestException as e:
            raise DiscordHTTPError(f"HTTP request failed ({e}).") from e

        body_text = resp.text or ""
        json_body: Any = None
        if body_text:
            try:
                json_body = resp.json()
            except ValueError:
                json_body = None

        rl = _parse_rate_limit_info(status_code=resp.status_code, headers=resp.headers, json_body=json_body)
        if rl is not None and attempt <= max_retries:
            sleep_s = min(max(0.0, rl.retry_after), max_retry_after_s)
            if jitter_s > 0:
                sleep_s += random.uniform(0.0, jitter_s)
            time.sleep(sleep_s)
            continue

        if resp.status_code >= 400:
            context_bits: list[str] = []
            if not redact_url_in_errors:
                context_bits.append(f"url={url}")
            if rl is not None:
                context_bits.append(f"rate_limit_global={rl.is_global}")
                if rl.bucket is not None:
                    context_bits.append(f"rate_limit_bucket={rl.bucket}")
                if rl.remaining is not None:
                    context_bits.append(f"rate_limit_remaining={rl.remaining}")
                if rl.reset_after is not None:
                    context_bits.append(f"rate_limit_reset_after={rl.reset_after}")

            context = (" " + " ".join(context_bits)) if context_bits else ""

            msg = f"HTTP request failed (HTTP {resp.status_code}).{context}"
            if body_text:
                msg += f" Response: {body_text[:500]}"
            raise DiscordHTTPError(msg)

        if not body_text:
            return None
        if isinstance(json_body, dict):
            return json_body
        return {"raw": body_text}
