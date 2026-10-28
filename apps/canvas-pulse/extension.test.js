import { describe, expect, it, vi } from "vitest";
import { activate } from "./extension.js";

describe("Canvas Pulse extension", () => {
  it("renders server information, navigates to service details, and cleans up", async () => {
    let mountPage;
    const unregister = vi.fn();
    const navigate = vi.fn();
    const request = vi.fn().mockResolvedValue({
      version: "1.43.0",
      sdk_version: "1.43.0",
      uptime: 3_726,
      idle_time: 12,
      usable_tools: ["terminal", "file_editor"],
      agents: ["CodeActAgent"],
      runtime_services: {
        mode: "dev:automation",
        services: {
          agent_server: {
            description: "The active Agent Server.",
            url_from_agent: "http://localhost:18000",
          },
        },
      },
    });
    const host = {
      apiVersion: "1",
      extension: {
        name: "canvas-pulse",
        version: "0.1.0",
        resolvedRef: "test-ref",
      },
      backend: { id: "local-test", kind: "local", orgId: null },
      registerPage: vi.fn((id, mount) => {
        expect(id).toBe("pulse");
        mountPage = mount;
        return unregister;
      }),
      navigate,
      agentServer: { request },
    };

    const deactivate = activate(host);
    expect(deactivate).toBe(unregister);

    const container = document.createElement("div");
    const cleanup = mountPage({ container, path: "", navigate });

    await vi.waitFor(() => {
      expect(container.textContent).toContain("Connected");
    });
    expect(request).toHaveBeenCalledWith({ path: "/server_info" });
    expect(container.textContent).toContain("1.43.0");
    expect(container.textContent).toContain("terminal");
    expect(container.textContent).toContain("Agent Server");
    expect(container.textContent).toContain("local-test");

    const serviceButton = Array.from(container.querySelectorAll("button")).find(
      (button) => button.textContent.includes("Agent Server"),
    );
    serviceButton.click();
    expect(navigate).toHaveBeenCalledWith(
      "/extensions/canvas-pulse/pulse/services/agent_server",
    );

    cleanup();
    expect(container.childElementCount).toBe(0);

    const detailCleanup = mountPage({
      container,
      path: "services/agent_server",
      navigate,
    });
    await vi.waitFor(() => {
      expect(container.textContent).toContain("Runtime service details");
    });
    expect(container.textContent).toContain("URL From Agent");
    expect(container.textContent).toContain("http://localhost:18000");

    detailCleanup();
    expect(container.childElementCount).toBe(0);
  });
});
