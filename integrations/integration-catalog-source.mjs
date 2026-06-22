/**
 * Authoring source for the unified integration catalog.
 *
 * This is the ONLY place the catalog is assembled from hand-authored data
 * (the per-integration JSON files under `integrations/catalog/` plus the OAuth
 * provider registration defaults). The assembled catalog is serialized to
 * `integrations/integration-catalog.json` by
 * `scripts/build-integration-catalog.mjs`; runtime consumers (the JS package
 * and the Python package) read that JSON asset, not this module.
 *
 * Each entry can carry one or more `connectionOptions`, each of which is an
 * oauth and/or an mcp/http connector. Entries are tagged with boolean
 * `supportsOauth` / `supportsMcp` flags so callers can filter (e.g. "only
 * integrations that support an oauth connector") without re-inspecting every
 * option.
 */
import { listOAuthProviderCatalog } from "./oauth-provider-catalog-source.mjs";

import airtable from "./catalog/airtable.json" with { type: "json" };
import apify from "./catalog/apify.json" with { type: "json" };
import atlassian from "./catalog/atlassian.json" with { type: "json" };
import brave_search from "./catalog/brave-search.json" with { type: "json" };
import browser_mcp from "./catalog/browser-mcp.json" with { type: "json" };
import clickhouse from "./catalog/clickhouse.json" with { type: "json" };
import cloudflare_bindings from "./catalog/cloudflare-bindings.json" with { type: "json" };
import cloudflare_browser_rendering from "./catalog/cloudflare-browser-rendering.json" with { type: "json" };
import cloudflare_builds from "./catalog/cloudflare-builds.json" with { type: "json" };
import cloudflare_docs from "./catalog/cloudflare-docs.json" with { type: "json" };
import cloudflare_observability from "./catalog/cloudflare-observability.json" with { type: "json" };
import deepwiki from "./catalog/deepwiki.json" with { type: "json" };
import elevenlabs from "./catalog/elevenlabs.json" with { type: "json" };
import everything from "./catalog/everything.json" with { type: "json" };
import exa from "./catalog/exa.json" with { type: "json" };
import fetch from "./catalog/fetch.json" with { type: "json" };
import figma from "./catalog/figma.json" with { type: "json" };
import filesystem from "./catalog/filesystem.json" with { type: "json" };
import firecrawl from "./catalog/firecrawl.json" with { type: "json" };
import git from "./catalog/git.json" with { type: "json" };
import github from "./catalog/github.json" with { type: "json" };
import huggingface from "./catalog/huggingface.json" with { type: "json" };
import kagi from "./catalog/kagi.json" with { type: "json" };
import linear from "./catalog/linear.json" with { type: "json" };
import memory from "./catalog/memory.json" with { type: "json" };
import mongodb from "./catalog/mongodb.json" with { type: "json" };
import neon from "./catalog/neon.json" with { type: "json" };
import notion from "./catalog/notion.json" with { type: "json" };
import obsidian from "./catalog/obsidian.json" with { type: "json" };
import paypal from "./catalog/paypal.json" with { type: "json" };
import playwright from "./catalog/playwright.json" with { type: "json" };
import redis from "./catalog/redis.json" with { type: "json" };
import resend from "./catalog/resend.json" with { type: "json" };
import sentry from "./catalog/sentry.json" with { type: "json" };
import sequential_thinking from "./catalog/sequential-thinking.json" with { type: "json" };
import slack from "./catalog/slack.json" with { type: "json" };
import stripe from "./catalog/stripe.json" with { type: "json" };
import supabase from "./catalog/supabase.json" with { type: "json" };
import tavily from "./catalog/tavily.json" with { type: "json" };
import time from "./catalog/time.json" with { type: "json" };

const DIRECT_INTEGRATIONS = [
  airtable,
  apify,
  atlassian,
  brave_search,
  browser_mcp,
  clickhouse,
  cloudflare_bindings,
  cloudflare_browser_rendering,
  cloudflare_builds,
  cloudflare_docs,
  cloudflare_observability,
  deepwiki,
  elevenlabs,
  everything,
  exa,
  fetch,
  figma,
  filesystem,
  firecrawl,
  git,
  github,
  huggingface,
  kagi,
  linear,
  memory,
  mongodb,
  neon,
  notion,
  obsidian,
  paypal,
  playwright,
  redis,
  resend,
  sentry,
  sequential_thinking,
  slack,
  stripe,
  supabase,
  tavily,
  time,
];

const optionIdForDefaults = (defaults) => {
  const strategy = defaults?.authStrategy ?? (defaults?.authorizationUrl || defaults?.tokenUrl ? "oauth2" : "oauth2");
  if (strategy === "oauth2") return "oauth";
  if (strategy === "none") return "none";
  return "api";
};

const providerConnectionOption = (provider) => {
  const defaults = provider.registrationDefaults;
  if (!defaults) return null;
  const option = {
    id: optionIdForDefaults(defaults),
    provider: defaults.provider ?? (defaults.serverUrl ? "mcp" : "http"),
    auth: {
      strategy: defaults.authStrategy ?? provider.authStrategy ?? "oauth2",
      authModes: defaults.authModes,
      credentialLabel: defaults.credentialLabel,
      credentialPlaceholder: defaults.credentialPlaceholder,
      credentialHelp: defaults.credentialHelp,
      apiKeyHeaderName: defaults.apiKeyHeaderName,
      oauth: defaults.authorizationUrl || defaults.tokenUrl ? {
        authorizationUrl: defaults.authorizationUrl,
        tokenUrl: defaults.tokenUrl,
        scopes: defaults.scopes ?? [],
        optionalScopes: defaults.optionalScopes,
        toolScopes: defaults.toolScopes,
        scopeSeparator: defaults.scopeSeparator,
        pkce: defaults.pkce,
        clientAuthentication: defaults.clientAuthentication,
        registrationUrl: defaults.registrationUrl,
        additionalAuthorizationParams: defaults.additionalAuthorizationParams,
        additionalTokenParams: defaults.additionalTokenParams,
      } : undefined,
    },
  };

  if (option.provider === "mcp") {
    option.transport = { kind: "shttp", url: defaults.serverUrl };
  } else {
    option.http = {
      apiBaseUrl: defaults.apiBaseUrl,
      openApiUrl: defaults.openApiUrl,
      defaultTool: defaults.toolName ? {
        name: defaults.toolName,
        description: defaults.toolDescription,
        method: defaults.requestMethod,
        path: defaults.requestPath,
        scopes: defaults.toolScopes,
      } : undefined,
    };
  }

  return option;
};

const providerIntegration = (provider) => {
  const option = providerConnectionOption(provider);
  return {
    id: provider.slug,
    kind: option?.provider ?? "http",
    name: provider.name,
    description: provider.description,
    categories: provider.categories,
    appUrl: provider.appUrl,
    docsUrl: provider.docsUrl,
    notes: provider.notes,
    catalogStatus: provider.availability,
    managedConnectorSlug: provider.managedConnectorSlug,
    authStrategy: provider.authStrategy,
    popularityRank: provider.popularityRank,
    registrationDefaults: provider.registrationDefaults,
    ...(option ? { defaultConnectionOptionId: option.id, connectionOptions: [option] } : { connectionOptions: [] }),
  };
};

const mergeOptions = (left = [], right = []) => {
  const options = new Map();
  for (const option of left) options.set(option.id, option);
  for (const option of right) {
    if (!options.has(option.id)) options.set(option.id, option);
  }
  return [...options.values()];
};

const mergeIntegration = (base, override) => {
  const connectionOptions = mergeOptions(base.connectionOptions, override.connectionOptions);
  return {
    ...base,
    ...override,
    catalogStatus: base.catalogStatus ?? override.catalogStatus,
    managedConnectorSlug: base.managedConnectorSlug ?? override.managedConnectorSlug,
    authStrategy: base.authStrategy ?? override.authStrategy,
    registrationDefaults: base.registrationDefaults ?? override.registrationDefaults,
    connectionOptions,
    defaultConnectionOptionId:
      base.defaultConnectionOptionId ?? override.defaultConnectionOptionId ?? connectionOptions[0]?.id,
  };
};

const entrySupportsOauth = (entry) =>
  entry.connectionOptions.some((option) => option.auth?.strategy === "oauth2");

const entrySupportsMcp = (entry) =>
  entry.connectionOptions.some((option) => option.provider === "mcp");

/**
 * Build the unified integration catalog snapshot serialized into
 * `integration-catalog.json`. Runtime consumers (JS and Python) read the
 * generated JSON, not this module.
 *
 * Each entry carries:
 *  - `connectionOptions`: one or more connectors, each an oauth and/or an
 *    mcp/http connector (merged from the OAuth provider defaults and the
 *    direct-integration JSON files).
 *  - `supportsOauth`: true if any option uses the `oauth2` auth strategy.
 *  - `supportsMcp`: true if any option is an `mcp` provider.
 *
 * The snapshot also includes the OAuth-provider-only `providers` view (for
 * the hub backend contract) and the derived `defaultManagedConnectors` /
 * `defaultManagedConnectorSlugs`, so a single asset serves every consumer.
 */
export const buildIntegrationCatalog = () => {
  const entriesById = new Map();
  for (const provider of listOAuthProviderCatalog().map(providerIntegration)) {
    entriesById.set(provider.id, provider);
  }
  for (const direct of DIRECT_INTEGRATIONS) {
    entriesById.set(
      direct.id,
      entriesById.has(direct.id)
        ? mergeIntegration(entriesById.get(direct.id), direct)
        : direct,
    );
  }

  const integrations = [...entriesById.values()]
    .map((entry) => ({
      ...entry,
      supportsOauth: entrySupportsOauth(entry),
      supportsMcp: entrySupportsMcp(entry),
    }))
    .sort((a, b) => {
      const rankDelta = (b.popularityRank ?? 0) - (a.popularityRank ?? 0);
      return rankDelta || a.name.localeCompare(b.name);
    });

  // OAuth-provider-only view (hub backend contract): the providers array
  // shape matches the legacy oauth-provider-catalog.json so existing hub
  // consumers are unaffected.
  const providers = listOAuthProviderCatalog();

  const isDefaultManagedConnectorProvider = (p) => {
    const defaults = p.registrationDefaults;
    if (!defaults?.authStrategy || defaults.authStrategy === "oauth2") {
      return false;
    }
    if (defaults.provider === "http" && defaults.apiBaseUrl && defaults.openApiUrl) {
      return true;
    }
    if (defaults.provider === "mcp" && defaults.serverUrl) {
      return true;
    }
    return false;
  };

  const defaultManagedConnector = (p) => {
    const defaults = p.registrationDefaults;
    return {
      slug: p.managedConnectorSlug ?? p.slug,
      name: p.name,
      description: p.description,
      appUrl: p.appUrl,
      docsUrl: p.docsUrl,
      categories: p.categories,
      authModes:
        defaults.authModes?.length && defaults.authModes.every(Boolean)
          ? defaults.authModes
          : [defaults.authStrategy],
      authStrategy: defaults.authStrategy,
      provider: defaults.provider,
      credentialLabel: defaults.credentialLabel ?? `${p.name} credential`,
      credentialPlaceholder:
        defaults.credentialPlaceholder ?? `Paste your ${p.name} credential`,
      credentialHelp: defaults.credentialHelp ?? `Credential required by ${p.name}.`,
      apiKeyHeaderName: defaults.apiKeyHeaderName?.trim() || undefined,
      apiBaseUrl: defaults.apiBaseUrl,
      openApiUrl: defaults.openApiUrl,
      serverUrl: defaults.serverUrl,
      oauthConfigured: true,
    };
  };

  const defaultManagedConnectors = providers
    .filter(isDefaultManagedConnectorProvider)
    .map(defaultManagedConnector);

  return {
    integrations,
    providers,
    defaultManagedConnectors,
    defaultManagedConnectorSlugs: defaultManagedConnectors.map((c) => c.slug),
  };
};
