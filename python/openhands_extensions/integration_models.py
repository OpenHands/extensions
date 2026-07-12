"""Typed models for the OpenHands integration catalog.

The hand-authored JSON files under ``integrations/catalog`` remain the source
of truth. These models provide a Python representation of the public catalog
contract defined by ``integrations/catalog.schema.json`` and
``integrations/index.d.ts``.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


NonEmptyString = Annotated[str, Field(min_length=1)]
HttpsUrl = Annotated[str, Field(pattern=r"^https://", min_length=8)]
IdentityPath = Annotated[
    str,
    Field(pattern=r"^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*$", min_length=1),
]
IntegrationAuthStrategy = Literal["none", "api_key", "bearer", "basic", "oauth2"]
IntegrationProvider = Literal["mcp", "http"]


class CatalogModel(BaseModel):
    """Base model for strict, portable catalog data."""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def reject_explicit_nulls(cls, values: Any) -> Any:
        """Match the JSON Schema: optional fields may be omitted, never null."""
        if not isinstance(values, dict):
            return values

        null_fields = [field for field, value in values.items() if value is None]
        if null_fields:
            raise ValueError(
                "Catalog fields must be omitted instead of set to null: "
                f"{', '.join(null_fields)}"
            )
        return values


class MarketplaceField(CatalogModel):
    key: NonEmptyString
    label: NonEmptyString
    type: Literal["text", "password"]
    placeholder: str | None = None
    helperText: str | None = None
    helperLink: HttpsUrl | None = None
    required: bool

    @model_validator(mode="after")
    def password_fields_have_help(self) -> MarketplaceField:
        if self.type == "password" and not self.helperText:
            raise ValueError("Password marketplace fields require helperText.")
        return self


class StreamableHttpTransport(CatalogModel):
    kind: Literal["shttp"]
    url: HttpsUrl
    apiKeyOptional: bool | None = None
    headerFields: list[MarketplaceField] | None = None
    urlEditable: bool | None = None


class SseTransport(CatalogModel):
    kind: Literal["sse"]
    url: HttpsUrl
    apiKeyOptional: bool | None = None
    headerFields: list[MarketplaceField] | None = None
    urlEditable: bool | None = None


class StdioTransport(CatalogModel):
    kind: Literal["stdio"]
    serverName: NonEmptyString
    command: NonEmptyString
    args: list[str]
    envFields: list[MarketplaceField] | None = None
    argFields: list[MarketplaceField] | None = None


IntegrationTransport = Annotated[
    StreamableHttpTransport | SseTransport | StdioTransport,
    Field(discriminator="kind"),
]


class IntegrationOAuthConfig(CatalogModel):
    authorizationUrl: HttpsUrl | None = None
    tokenUrl: HttpsUrl | None = None
    scopes: list[NonEmptyString] | None = None
    optionalScopes: list[NonEmptyString] | None = None
    toolScopes: list[NonEmptyString] | None = None
    scopeSeparator: Literal["space", "comma"] | None = None
    pkce: bool | None = None
    clientAuthentication: Literal["basic", "body", "none"] | None = None
    registrationUrl: HttpsUrl | None = None
    additionalAuthorizationParams: dict[str, str] | None = None
    additionalTokenParams: dict[str, str] | None = None


class IntegrationAuthConfig(CatalogModel):
    strategy: IntegrationAuthStrategy
    authModes: list[IntegrationAuthStrategy] | None = Field(default=None, min_length=1)
    credentialLabel: NonEmptyString | None = None
    credentialPlaceholder: NonEmptyString | None = None
    credentialHelp: NonEmptyString | None = None
    credentialSecretName: NonEmptyString | None = None
    saveCredentialAsSecretByDefault: bool | None = None
    apiKeyHeaderName: NonEmptyString | None = None
    apiKeyOptional: bool | None = None
    oauth: IntegrationOAuthConfig | None = None


class IntegrationHttpConfig(CatalogModel):
    apiBaseUrl: HttpsUrl
    openApiUrl: HttpsUrl


class IntegrationIdentityMapping(CatalogModel):
    source: Literal["oauth_token_response", "access_token_claims", "identity_api"]
    endpoint: HttpsUrl | None = None
    externalPrincipalIdPath: IdentityPath
    externalTenantIdPath: IdentityPath | None = None
    externalResourceIdPath: IdentityPath | None = None
    resourceNamePath: IdentityPath | None = None
    resourceUrlPath: IdentityPath | None = None

    @model_validator(mode="after")
    def identity_api_requires_endpoint(self) -> IntegrationIdentityMapping:
        if self.source == "identity_api" and not self.endpoint:
            raise ValueError("identity_api mappings require an endpoint.")
        if self.source != "identity_api" and self.endpoint:
            raise ValueError("Only identity_api mappings may define an endpoint.")
        return self


class IntegrationResourceDiscovery(CatalogModel):
    endpoint: HttpsUrl
    itemsPath: IdentityPath | None = None
    externalResourceIdPath: IdentityPath
    resourceNamePath: IdentityPath | None = None
    resourceUrlPath: IdentityPath | None = None


class IntegrationConnectionModel(CatalogModel):
    principalType: Literal["user", "bot", "service_account", "application"]
    credentialScope: Literal["account", "tenant", "organization", "resource"]
    resourceType: NonEmptyString
    resourceCardinality: Literal["one", "many"]
    selectionMode: Literal["automatic", "post_auth", "runtime"]
    identityMapping: IntegrationIdentityMapping | None = None
    resourceDiscovery: IntegrationResourceDiscovery | None = None

    @model_validator(mode="after")
    def post_auth_requires_resource_discovery(self) -> IntegrationConnectionModel:
        if self.selectionMode == "post_auth" and not self.resourceDiscovery:
            raise ValueError("post_auth connections require resourceDiscovery.")
        return self


class McpConnectionOption(CatalogModel):
    id: NonEmptyString
    provider: Literal["mcp"]
    transport: IntegrationTransport
    auth: IntegrationAuthConfig
    connectionModel: IntegrationConnectionModel | None = None


class HttpConnectionOption(CatalogModel):
    id: NonEmptyString
    provider: Literal["http"]
    http: IntegrationHttpConfig
    auth: IntegrationAuthConfig
    connectionModel: IntegrationConnectionModel | None = None


IntegrationConnectionOption = Annotated[
    McpConnectionOption | HttpConnectionOption,
    Field(discriminator="provider"),
]


class IntegrationCatalogEntry(CatalogModel):
    id: NonEmptyString
    name: NonEmptyString
    description: NonEmptyString
    categories: list[NonEmptyString] | None = Field(default=None, min_length=1)
    appUrl: HttpsUrl | None = None
    docsUrl: HttpsUrl
    notes: NonEmptyString | None = None
    iconBg: NonEmptyString | None = None
    iconColor: NonEmptyString | None = None
    logoUrl: HttpsUrl | None = None
    keywords: list[NonEmptyString] | None = None
    popularityRank: int | None = Field(default=None, ge=0)
    installHint: NonEmptyString | None = None
    connectionOptions: list[IntegrationConnectionOption] = Field(min_length=1)

    @field_validator("categories", "keywords")
    @classmethod
    def list_values_are_unique(
        cls, values: list[NonEmptyString] | None
    ) -> list[NonEmptyString] | None:
        if values is not None and len(values) != len(set(values)):
            raise ValueError("Catalog list values must be unique.")
        return values

    @model_validator(mode="after")
    def validate_auth_requirements(self) -> IntegrationCatalogEntry:
        for option in self.connectionOptions:
            if option.provider == "http" and option.auth.strategy == "api_key":
                if not option.auth.apiKeyHeaderName:
                    raise ValueError(
                        "HTTP API-key connections require apiKeyHeaderName."
                    )
            if option.provider == "http" and option.auth.strategy == "oauth2":
                oauth = option.auth.oauth
                if not oauth or not oauth.authorizationUrl or not oauth.tokenUrl:
                    raise ValueError(
                        "HTTP OAuth connections require authorizationUrl and tokenUrl."
                    )
        return self


class IntegrationCatalogSnapshot(CatalogModel):
    integrations: list[IntegrationCatalogEntry]
