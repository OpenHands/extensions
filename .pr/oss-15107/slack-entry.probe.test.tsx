// Probe: how Agent Canvas treats the Slack catalog entry on extensions main
// versus the entry on this PR branch. Copy it into an Agent Canvas checkout as
// __tests__/slack-entry.probe.test.tsx and run:
//
//   SLACK_ENTRY_MAIN=<slack.json from extensions main> \
//   SLACK_ENTRY_PR=<slack.json from this branch> \
//   npx vitest run __tests__/slack-entry.probe.test.tsx
import fs from "node:fs";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { IntegrationCatalogEntry as MarketplaceEntry } from "@openhands/extensions/integrations";
import SettingsService from "#/api/settings-service/settings-service.api";
import McpService from "#/api/mcp-service/mcp-service.api";
import { __resetActiveStoreForTests } from "#/api/backend-registry/active-store";
import { SecretsService } from "#/api/secrets-service";
import { MOCK_DEFAULT_USER_SETTINGS } from "#/mocks/handlers";
import { ActiveBackendProvider } from "#/contexts/active-backend-context";
import { InstallServerModal } from "#/components/features/mcp-page/install-server-modal";
import {
  findInstalledEntryMatch,
  getInstallableMcpConnectionOptions,
} from "#/utils/mcp-marketplace-utils";

const MAIN_ENTRY_PATH = process.env.SLACK_ENTRY_MAIN!;
const PR_ENTRY_PATH = process.env.SLACK_ENTRY_PR!;

const load = (path: string) =>
  JSON.parse(fs.readFileSync(path, "utf8")) as MarketplaceEntry;

const OLD_STDIO_CONFIG = {
  command: "npx",
  args: ["-y", "@zencoderai/slack-mcp-server"],
  env: { SLACK_BOT_TOKEN: "xoxb-abc", SLACK_TEAM_ID: "T01" },
};

function renderWith(ui: React.ReactNode) {
  return render(ui, {
    wrapper: ({ children }) => (
      <QueryClientProvider
        client={
          new QueryClient({ defaultOptions: { queries: { retry: false } } })
        }
      >
        <ActiveBackendProvider>{children}</ActiveBackendProvider>
      </QueryClientProvider>
    ),
  });
}

function spies() {
  return {
    testSpy: vi
      .spyOn(McpService, "testServer")
      .mockResolvedValue({ ok: true, tools: [] }),
    getSpy: vi
      .spyOn(SettingsService, "getSettings")
      .mockResolvedValue(MOCK_DEFAULT_USER_SETTINGS),
    saveSpy: vi.spyOn(SettingsService, "saveSettings").mockResolvedValue(true),
    secretSpy: vi.spyOn(SecretsService, "createSecret").mockResolvedValue(),
  };
}

const savedMcpConfig = (saveSpy: ReturnType<typeof spies>["saveSpy"]) =>
  (
    (saveSpy.mock.calls[0][0] as Record<string, unknown>)
      .agent_settings_diff as { mcp_config: Record<string, unknown> }
  ).mcp_config;

describe("Slack catalog entry in Agent Canvas (probe)", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    window.localStorage.clear();
    __resetActiveStoreForTests();
    vi.spyOn(SettingsService, "createMcpServer").mockImplementation(
      (settingsKey, server) =>
        SettingsService.saveSettings({
          agent_settings_diff: {
            mcp_config: { [settingsKey]: server },
          },
        }),
    );
  });

  it("main: the only installable option is the local bot-token server", () => {
    const options = getInstallableMcpConnectionOptions(load(MAIN_ENTRY_PATH));
    expect(options.map((o) => o.id)).toEqual(["api"]);
    expect(options[0].transport).toMatchObject({
      kind: "stdio",
      args: ["-y", "@zencoderai/slack-mcp-server"],
    });
  });

  it("PR: the default option is the same local server, and Slack's hosted server is offered second", () => {
    const main = getInstallableMcpConnectionOptions(load(MAIN_ENTRY_PATH));
    const pr = getInstallableMcpConnectionOptions(load(PR_ENTRY_PATH));
    expect(pr.map((o) => o.id)).toEqual(["api", "user-token"]);
    expect(pr[0].transport).toEqual(main[0].transport);
    expect(pr[1].transport).toEqual({
      kind: "shttp",
      url: "https://mcp.slack.com/mcp",
    });
    expect(pr[1].auth).toMatchObject({
      strategy: "bearer",
      credentialSecretName: "SLACK_USER_TOKEN",
    });
  });

  it("PR: the dialog opens on the same fields as before and saves the same local server", async () => {
    const { getSpy, saveSpy } = spies();
    renderWith(
      <InstallServerModal
        existingServers={[]}
        entry={load(PR_ENTRY_PATH)}
        onClose={vi.fn()}
      />,
    );
    await screen.findByTestId("mcp-install-modal");
    await waitFor(() => expect(getSpy).toHaveBeenCalled());

    // Both connection methods are offered; the hosted token field is not
    // shown until the user switches.
    expect(screen.getByTestId("mcp-install-option-api")).toBeTruthy();
    expect(screen.getByTestId("mcp-install-option-user-token")).toBeTruthy();
    expect(screen.queryByTestId("mcp-install-field-api_key")).toBeNull();

    fireEvent.change(screen.getByTestId("mcp-install-field-SLACK_BOT_TOKEN"), {
      target: { value: "xoxb-abc" },
    });
    fireEvent.change(screen.getByTestId("mcp-install-field-SLACK_TEAM_ID"), {
      target: { value: "T01" },
    });
    fireEvent.click(screen.getByTestId("mcp-install-submit"));

    await waitFor(() => expect(saveSpy).toHaveBeenCalledTimes(1));
    expect(savedMcpConfig(saveSpy)).toMatchObject({ slack: OLD_STDIO_CONFIG });
  });

  it("PR: switching the connection method installs Slack's hosted server with a user token", async () => {
    const { getSpy, saveSpy, testSpy, secretSpy } = spies();
    renderWith(
      <InstallServerModal
        existingServers={[]}
        entry={load(PR_ENTRY_PATH)}
        onClose={vi.fn()}
      />,
    );
    await screen.findByTestId("mcp-install-modal");
    await waitFor(() => expect(getSpy).toHaveBeenCalled());

    fireEvent.click(screen.getByTestId("mcp-install-option-user-token"));
    const field = await screen.findByTestId("mcp-install-field-api_key");
    expect(screen.queryByTestId("mcp-install-field-SLACK_BOT_TOKEN")).toBeNull();
    expect(field.getAttribute("placeholder")).toBe("xoxp-...");

    // The token is required.
    fireEvent.click(screen.getByTestId("mcp-install-submit"));
    await waitFor(() => expect(saveSpy).not.toHaveBeenCalled());

    fireEvent.change(field, { target: { value: "xoxp-abc" } });
    fireEvent.click(screen.getByTestId("mcp-install-submit"));

    await waitFor(() => expect(saveSpy).toHaveBeenCalledTimes(1));
    expect(testSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "shttp",
        url: "https://mcp.slack.com/mcp",
        auth: { strategy: "bearer", value: "xoxp-abc" },
      }),
    );
    expect(savedMcpConfig(saveSpy)).toMatchObject({
      slack: {
        url: "https://mcp.slack.com/mcp",
        auth: { strategy: "bearer", value: "xoxp-abc" },
      },
    });
    await waitFor(() => expect(secretSpy).toHaveBeenCalled());
    expect(JSON.stringify(secretSpy.mock.calls)).toContain("SLACK_USER_TOKEN");
  });

  it("PR: an existing local install and a hosted install both count as the Slack entry", () => {
    const entry = load(PR_ENTRY_PATH);
    const existingLocal = findInstalledEntryMatch(entry, [
      { id: "stdio-0", type: "stdio", name: "slack", ...OLD_STDIO_CONFIG },
    ]);
    const hosted = findInstalledEntryMatch(entry, [
      {
        id: "shttp-0",
        type: "shttp",
        name: "slack",
        url: "https://mcp.slack.com/mcp",
      },
    ]);
    expect(existingLocal).not.toBeNull();
    expect(hosted).not.toBeNull();
  });
});
