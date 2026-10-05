const BACKEND = "/api/canvas-extensions/installed/vscode/backend";
const FOLDER_KEY_PREFIX = "openhands.apps.vscode.folder";

function folderKey(host) {
  return `${FOLDER_KEY_PREFIX}:${host.backend.id}:${host.backend.orgId || "local"}:${host.extension.name}`;
}

function button(label, onClick, variant = "secondary") {
  const element = document.createElement("button");
  element.type = "button";
  element.textContent = label;
  element.style.cssText = [
    "min-height:40px",
    "padding:0 18px",
    "border-radius:8px",
    "border:1px solid transparent",
    "font:inherit",
    "font-size:14px",
    "font-weight:600",
    "cursor:pointer",
    "transition:opacity 120ms ease,background-color 120ms ease",
    variant === "primary"
      ? "background:#f3ce49;color:#171717"
      : "background:#262626;color:#fafafa;border-color:#525252",
  ].join(";");
  element.addEventListener("click", onClick);
  return element;
}

function statusLabel(state) {
  return state.charAt(0).toUpperCase() + state.slice(1);
}

export function activate(host) {
  return host.registerPage("editor", async ({ container }) => {
    container.style.minHeight = "100vh";
    const shell = document.createElement("div");
    shell.style.cssText = "height:100vh;min-height:100vh;width:100%;display:flex;flex-direction:column";
    container.replaceChildren(shell);

    if (!host.appBackendView) {
      const error = document.createElement("p");
      error.setAttribute("role", "alert");
      error.textContent = "VS Code is unavailable because this Agent Server does not support managed App backends.";
      shell.append(error);
      return () => container.replaceChildren();
    }

    let disposed = false;
    let mounted;
    const storageKey = folderKey(host);
    const request = (method, path = BACKEND, body) => host.agentServer.request({ method, path, ...(body ? { body } : {}) });
    const cleanup = () => {
      disposed = true;
      mounted?.();
      mounted = undefined;
      container.replaceChildren();
    };

    const render = (status) => {
      if (disposed) return;
      shell.replaceChildren();
      if (status.state === "ready") {
        const editor = document.createElement("div");
        editor.style.cssText = "flex:1;min-height:100vh;width:100%;overflow:hidden";
        shell.append(editor);
        const folder = localStorage.getItem(storageKey)?.trim();
        mounted = host.appBackendView.mount({
          container: editor,
          ...(folder ? { query: { folder } } : {}),
        });
        return;
      }

      shell.style.justifyContent = "center";
      shell.style.alignItems = "center";
      shell.style.padding = "32px";
      shell.style.boxSizing = "border-box";

      const panel = document.createElement("section");
      panel.setAttribute("aria-live", "polite");
      panel.style.cssText = "width:min(100%,520px);padding:32px;border:1px solid #262626;border-radius:12px;background:#0a0a0a;color:#fafafa;box-sizing:border-box;text-align:center";
      const heading = document.createElement("h2");
      heading.textContent = "Set up VS Code";
      heading.style.cssText = "margin:0;font-size:24px;line-height:32px;font-weight:600";
      const description = document.createElement("p");
      description.textContent = "Start the secure VS Code backend for this Agent Canvas session. The first launch downloads and verifies the pinned editor package.";
      description.style.cssText = "margin:12px auto 0;max-width:440px;color:#a3a3a3;font-size:14px;line-height:21px";
      const statusRow = document.createElement("div");
      statusRow.style.cssText = "display:flex;align-items:center;justify-content:center;gap:8px;margin:20px 0 24px;font-size:13px;color:#a3a3a3";
      const statusDot = document.createElement("span");
      statusDot.setAttribute("aria-hidden", "true");
      statusDot.style.cssText = `width:8px;height:8px;border-radius:999px;background:${status.state === "unhealthy" ? "#fda4af" : "#737373"}`;
      const detail = document.createElement("span");
      detail.textContent = status.detail || `Backend status: ${statusLabel(status.state)}`;
      statusRow.append(statusDot, detail);
      panel.append(heading, description, statusRow);

      const field = document.createElement("label");
      field.style.cssText = "display:flex;flex-direction:column;gap:8px;text-align:left";
      const fieldLabel = document.createElement("span");
      fieldLabel.textContent = "Workspace folder";
      fieldLabel.style.cssText = "font-size:13px;font-weight:500;color:#fafafa";
      const folder = document.createElement("input");
      folder.type = "text";
      folder.placeholder = "Optional path to open in VS Code";
      folder.value = localStorage.getItem(storageKey) || "";
      folder.setAttribute("aria-label", "Workspace folder path");
      folder.style.cssText = "width:100%;height:42px;padding:0 12px;border:1px solid #525252;border-radius:8px;background:#1a1a1a;color:#fafafa;font:inherit;font-size:14px;box-sizing:border-box;outline:none";
      const hint = document.createElement("span");
      hint.textContent = "Leave blank to open the default App workspace.";
      hint.style.cssText = "font-size:12px;color:#8c8c8c";
      field.append(fieldLabel, folder, hint);
      panel.append(field);

      const actions = document.createElement("div");
      actions.style.cssText = "display:flex;justify-content:center;gap:10px;margin-top:24px;flex-wrap:wrap";
      if (status.state === "missing" || status.state === "stopped" || status.state === "unhealthy") {
        actions.append(button("Prepare and start", async () => {
          const selectedFolder = folder.value.trim();
          if (selectedFolder) localStorage.setItem(storageKey, selectedFolder);
          else localStorage.removeItem(storageKey);
          actions.replaceChildren(document.createTextNode("Preparing and verifying VS Code..."));
          try {
            let approval = status;
            if (!approval.revision) approval = await request("GET");
            if (!approval.revision) throw new Error("The backend did not report an immutable revision.");
            try {
              await request("POST", `${BACKEND}/prepare`, { revision: approval.revision });
            } catch (error) {
              if (error?.status !== 409) throw error;
              approval = await request("GET");
              if (!approval.revision) throw error;
              await request("POST", `${BACKEND}/prepare`, { revision: approval.revision });
            }
            await request("POST", `${BACKEND}/start`, { revision: approval.revision });
            render(await request("GET"));
          } catch (error) {
            detail.textContent = `Setup failed: ${error.message}`;
            statusDot.style.background = "#fda4af";
            actions.replaceChildren(button("Try again", () => render(status), "primary"));
          }
        }, "primary"));
      }
      if (status.state === "ready" || status.state === "starting") {
        actions.append(button("Stop", async () => render(await request("POST", `${BACKEND}/stop`))));
      }
      actions.append(button("Refresh status", async () => render(await request("GET"))));
      panel.append(actions);
      shell.append(panel);
    };

    try { render(await request("GET")); }
    catch (error) {
      const failure = document.createElement("p");
      failure.setAttribute("role", "alert");
      failure.textContent = `Unable to read VS Code backend status: ${error.message}`;
      shell.replaceChildren(failure);
    }
    return cleanup;
  });
}
