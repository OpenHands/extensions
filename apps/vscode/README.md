# VS Code App

Install this App in Agent Canvas by opening **Apps → Add App** and entering:

```text
https://github.com/OpenHands/extensions/tree/main/apps/vscode
```

The App provides a full-height code-server editor. Before the backend is ready, it shows backend status, an optional workspace-folder input, and revision-bound prepare/start/stop/refresh actions. Once ready, the page contains only the editor iframe.

## Artifact delivery

The repository contains no code-server binaries. During the explicit **Prepare and start** step, Agent Server downloads only the current platform's pinned code-server Server `v4.145.2` archive from its public GitHub Release, verifies the manifest-pinned SHA-256 digest, safely extracts it into an App-owned content-addressed cache, and starts it with App-owned home, user-data, and extensions directories. It does not send Agent Server or repository credentials to the artifact host.

The optional folder is persisted in browser storage and forwarded as the editor folder. It is a user convenience, not OS sandboxing.

## Draft migration dependencies

This code-server migration depends on OpenHands/software-agent-sdk#6792 for
macOS platform support through `additional_artifacts`. It is not merge-ready:
the upstream archives contain symbolic links rejected by the current Agent
Server extractor. A verified artifact packaging or safe extraction solution
is required before these URLs can be used directly. Windows is not advertised
until managed-backend process ownership is implemented and tested there.

The editor starts without a default folder to avoid an initial redirect that
the authenticated app bridge rejects. Workspace selection also requires a
Canvas host that forwards the app view's folder query.
