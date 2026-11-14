# VS Code App

Install this App in Agent Canvas by opening **Apps → Add App** and entering:

```text
https://github.com/OpenHands/extensions/tree/main/apps/vscode
```

The App provides a full-height OpenVSCode editor. Before the backend is ready, it shows backend status, an optional workspace-folder input, and revision-bound prepare/start/stop/refresh actions. Once ready, the page contains only the editor iframe.

## Artifact delivery

The repository contains no OpenVSCode binaries. During the explicit **Prepare and start** step, Agent Server downloads only the current platform's pinned OpenVSCode Server `v1.109.5` archive from its public GitHub Release, verifies the manifest-pinned SHA-256 digest, safely extracts it into an App-owned content-addressed cache, and starts it with App-owned home, user-data, and extensions directories. It does not send Agent Server or repository credentials to the artifact host.

The optional folder is persisted in browser storage and forwarded as the editor folder. It is a user convenience, not OS sandboxing.
