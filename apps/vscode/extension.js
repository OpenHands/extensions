const BACKEND = "/api/canvas-extensions/installed/vscode/backend";
const FOLDER_KEY_PREFIX = "openhands.apps.vscode.folder";

function folderKey(host) {
  return `${FOLDER_KEY_PREFIX}:${host.backend.id}:${host.backend.orgId || "local"}:${host.extension.name}`;
}

function button(label, onClick) {
  const element = document.createElement("button");
  element.type = "button";
  element.textContent = label;
  element.addEventListener("click", onClick);
  return element;
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

      const panel = document.createElement("section");
      panel.setAttribute("aria-live", "polite");
      const heading = document.createElement("h2");
      heading.textContent = "VS Code setup";
      const detail = document.createElement("p");
      detail.textContent = status.detail || `Backend status: ${status.state}.`;
      panel.append(heading, detail);
      const folder = document.createElement("input");
      folder.type = "text";
      folder.placeholder = "Workspace folder path (optional)";
      folder.value = localStorage.getItem(storageKey) || "";
      folder.setAttribute("aria-label", "Workspace folder path");
      panel.append(folder);
      const actions = document.createElement("p");
      if (status.state === "missing" || status.state === "stopped" || status.state === "unhealthy") {
        actions.append(button("Prepare and start", async () => {
          const selectedFolder = folder.value.trim();
          if (selectedFolder) localStorage.setItem(storageKey, selectedFolder);
          else localStorage.removeItem(storageKey);
          actions.replaceChildren(document.createTextNode("Preparing..."));
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
            actions.replaceChildren(button("Prepare and start", () => render(status)));
          }
        }));
      }
      if (status.state === "ready" || status.state === "starting") {
        actions.append(button("Stop", async () => render(await request("POST", `${BACKEND}/stop`))));
      }
      actions.append(button("Refresh", async () => render(await request("GET"))));
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
