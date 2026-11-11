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

  it("main: the only installable option is the third-party stdio server", () => {
    const options = getInstallableMcpConnectionOptions(load(MAIN_ENTRY_PATH));
    console.log(
      "[probe] main installable:",
      JSON.stringify(options.map((o) => [o.id, o.transport])),
    );
    expect(options.map((o) => o.id)).toEqual(["api"]);
    expect(options[0].transport).toMatchObject({
      kind: "stdio",
      args: ["-y", "@zencoderai/slack-mcp-server"],
    });
  });

  it("PR: the only installable option is Slack's hosted server with a bearer token", () => {
    const options = getInstallableMcpConnectionOptions(load(PR_ENTRY_PATH));
    console.log(
      "[probe] PR installable:",
      JSON.stringify(options.map((o) => [o.id, o.transport, o.auth.strategy])),
    );
    expect(options.map((o) => o.id)).toEqual(["api"]);
    expect(options[0].transport).toEqual({
      kind: "shttp",
      url: "https://mcp.slack.com/mcp",
    });
    expect(options[0].auth).toMatchObject({
      strategy: "bearer",
      credentialSecretName: "SLACK_USER_TOKEN",
      saveCredentialAsSecretByDefault: true,
    });
  });

  it("PR: the dialog asks for the user token, then tests and saves the hosted server", async () => {
    const entry = load(PR_ENTRY_PATH);
    const testSpy = vi
      .spyOn(McpService, "testServer")
      .mockResolvedValue({ ok: true, tools: [] });
    const getSpy = vi
      .spyOn(SettingsService, "getSettings")
      .mockResolvedValue(MOCK_DEFAULT_USER_SETTINGS);
    const saveSpy = vi
      .spyOn(SettingsService, "saveSettings")
      .mockResolvedValue(true);
    const secretSpy = vi
      .spyOn(SecretsService, "createSecret")
      .mockResolvedValue();

    renderWith(
      <InstallServerModal
        existingServers={[]}
        entry={entry}
        onClose={vi.fn()}
      />,
    );
    await screen.findByTestId("mcp-install-modal");
    await waitFor(() => expect(getSpy).toHaveBeenCalled());

    // No leftover fields from the old stdio option.
    expect(screen.queryByTestId("mcp-install-field-SLACK_BOT_TOKEN")).toBeNull();
    expect(screen.queryByTestId("mcp-install-field-SLACK_TEAM_ID")).toBeNull();

    const field = screen.getByTestId("mcp-install-field-api_key");
    const modalText = screen.getByTestId("mcp-install-modal").textContent ?? "";
    console.log("[probe] placeholder:", field.getAttribute("placeholder"));
    console.log("[probe] dialog text:", modalText.replace(/\s+/g, " ").trim());
    expect(field.getAttribute("placeholder")).toBe("xoxp-...");
    expect(modalText).toContain("User OAuth token");
    expect(modalText).toContain("Slack Model Context Protocol (MCP) Server");

    // The token is required.
    fireEvent.click(screen.getByTestId("mcp-install-submit"));
    await waitFor(() => expect(saveSpy).not.toHaveBeenCalled());
    expect(testSpy).not.toHaveBeenCalled();

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
    const sent = (saveSpy.mock.calls[0][0] as Record<string, unknown>)
      .agent_settings_diff as { mcp_config: Record<string, unknown> };
    console.log("[probe] saved mcp_config:", JSON.stringify(sent.mcp_config));
    expect(sent.mcp_config).toMatchObject({
      slack: {
        url: "https://mcp.slack.com/mcp",
        auth: { strategy: "bearer", value: "xoxp-abc" },
      },
    });

    await waitFor(() => expect(secretSpy).toHaveBeenCalled());
    const secretCalls = JSON.stringify(secretSpy.mock.calls);
    console.log(
      "[probe] secret saved under:",
      secretCalls.replace("xoxp-abc", "<token>"),
    );
    expect(secretCalls).toContain("SLACK_USER_TOKEN");
    expect(secretCalls).toContain("xoxp-abc");
  });

  it("PR: an installed hosted server counts as the Slack entry; an old stdio install does not", () => {
    const entry = load(PR_ENTRY_PATH);
    const hosted = findInstalledEntryMatch(entry, [
      {
        id: "shttp-0",
        type: "shttp",
        name: "slack",
        url: "https://mcp.slack.com/mcp",
      },
    ]);
    const oldStdio = findInstalledEntryMatch(entry, [
      {
        id: "stdio-0",
        type: "stdio",
        name: "slack",
        command: "npx",
        args: ["-y", "@zencoderai/slack-mcp-server"],
      },
    ]);
    console.log(
      "[probe] hosted install matched:",
      hosted !== null,
      "| old stdio install matched:",
      oldStdio !== null,
    );
    expect(hosted).not.toBeNull();
    expect(oldStdio).toBeNull();
  });
});
