"""Python bindings for the OpenHands extensions integration catalog.

The source of truth is the hand-authored ``integrations/catalog/<id>.json``
directory. ``integration-catalog.json`` is a generated package asset assembled
from that directory and mirrored byte-for-byte into this package. The JavaScript
and Python packages derive the same read-time convenience fields from
``connectionOptions``.
"""

from __future__ import annotations

import copy
import json
from functools import lru_cache
from importlib import resources
from typing import Any

__all__ = [
    "INTEGRATION_CATALOG_SNAPSHOT",
    "get_integration_catalog_entry",
    "list_integration_catalog",
]


@lru_cache(maxsize=1)
def _load_snapshot() -> dict[str, Any]:
    with resources.files(__package__).joinpath("integration-catalog.json").open(
        "r", encoding="utf-8"
    ) as handle:
        return json.load(handle)


def _raw_integrations() -> list[dict[str, Any]]:
    return _load_snapshot()["integrations"]


def _defined_values(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _default_connection_option(entry: dict[str, Any]) -> dict[str, Any] | None:
    options = entry.get("connectionOptions", [])
    return options[0] if options else None


def _entry_supports_mcp(entry: dict[str, Any]) -> bool:
    return any(option.get("provider") == "mcp" for option in entry.get("connectionOptions", []))


def _entry_supports_oauth(entry: dict[str, Any]) -> bool:
    return any(
        option.get("auth", {}).get("strategy") == "oauth2"
        for option in entry.get("connectionOptions", [])
    )


def _registration_defaults_for(entry: dict[str, Any]) -> dict[str, Any] | None:
    if not entry.get("availability"):
        return None
    option = _default_connection_option(entry)
    if not option:
        return None
    auth = option.get("auth", {})
    oauth = auth.get("oauth", {})
    http = option.get("http", {})
    tool = http.get("defaultTool", {})
    transport = option.get("transport", {})
    return _defined_values(
        {
            "provider": option.get("provider"),
            "authModes": auth.get("authModes"),
            "authStrategy": auth.get("strategy"),
            "credentialLabel": auth.get("credentialLabel"),
            "credentialPlaceholder": auth.get("credentialPlaceholder"),
            "credentialHelp": auth.get("credentialHelp"),
            "credentialSecretName": auth.get("credentialSecretName"),
            "saveCredentialAsSecretByDefault": auth.get("saveCredentialAsSecretByDefault"),
            "apiKeyHeaderName": auth.get("apiKeyHeaderName"),
            "apiKeyOptional": auth.get("apiKeyOptional"),
            "apiBaseUrl": http.get("apiBaseUrl"),
            "serverUrl": transport.get("url"),
            "openApiUrl": http.get("openApiUrl"),
            "authorizationUrl": oauth.get("authorizationUrl"),
            "tokenUrl": oauth.get("tokenUrl"),
            "scopes": oauth.get("scopes"),
            "optionalScopes": oauth.get("optionalScopes"),
            "toolScopes": oauth.get("toolScopes"),
            "scopeSeparator": oauth.get("scopeSeparator"),
            "pkce": oauth.get("pkce"),
            "clientAuthentication": oauth.get("clientAuthentication"),
            "registrationUrl": oauth.get("registrationUrl"),
            "additionalAuthorizationParams": oauth.get("additionalAuthorizationParams"),
            "additionalTokenParams": oauth.get("additionalTokenParams"),
            "toolName": tool.get("name"),
            "toolDescription": tool.get("description"),
            "requestMethod": tool.get("method"),
            "requestPath": tool.get("path"),
        }
    )


def _with_derived_fields(entry: dict[str, Any]) -> dict[str, Any]:
    enriched = copy.deepcopy(entry)
    default_option = _default_connection_option(entry)
    registration_defaults = _registration_defaults_for(entry)
    if entry.get("availability") is not None:
        enriched["catalogStatus"] = entry["availability"]
    if default_option is not None:
        enriched["defaultConnectionOptionId"] = default_option.get("id")
        enriched["authStrategy"] = default_option.get("auth", {}).get("strategy")
    if entry.get("availability") and entry.get("availability") != "planned":
        enriched["managedConnectorSlug"] = entry["id"]
    if registration_defaults is not None:
        enriched["registrationDefaults"] = registration_defaults
    enriched["supportsMcp"] = _entry_supports_mcp(entry)
    enriched["supportsOauth"] = _entry_supports_oauth(entry)
    return enriched


@lru_cache(maxsize=1)
def _integrations() -> tuple[dict[str, Any], ...]:
    return tuple(_with_derived_fields(entry) for entry in _raw_integrations())


@lru_cache(maxsize=1)
def _integration_by_id() -> dict[str, dict[str, Any]]:
    return {entry["id"]: entry for entry in _integrations()}


def list_integration_catalog(
    mcp: bool | None = None,
    oauth: bool | None = None,
) -> list[dict[str, Any]]:
    """Return the integration catalog, optionally filtered by connector type."""
    result = []
    for entry in _integrations():
        if mcp is not None and entry["supportsMcp"] != mcp:
            continue
        if oauth is not None and entry["supportsOauth"] != oauth:
            continue
        result.append(copy.deepcopy(entry))
    return result


def get_integration_catalog_entry(id: str) -> dict[str, Any] | None:
    """Return one integration catalog entry by id, or ``None``."""
    entry = _integration_by_id().get(id)
    return copy.deepcopy(entry) if entry is not None else None


INTEGRATION_CATALOG_SNAPSHOT: dict[str, Any] = copy.deepcopy(_load_snapshot())
