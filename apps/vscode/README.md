# VS Code App

Install this App in Agent Canvas by opening **Apps → Add App** and entering:

```text
https://github.com/OpenHands/extensions/tree/main/apps/vscode
```

The App provides a full-height code-server editor. Before the backend is ready, it shows backend status, an optional workspace-folder input, and revision-bound prepare/start/stop/refresh actions. Once ready, the page contains only the editor iframe.

## Artifact delivery

The repository contains no code-server binaries. During the explicit **Prepare and start** step, Agent Server downloads only the current platform's pinned code-server `v4.145.2` archive from its public GitHub Release, verifies the manifest-pinned SHA-256 digest, safely extracts it into an App-owned content-addressed cache, and starts it with App-owned home, user-data, and extensions directories. It does not send Agent Server or repository credentials to the artifact host.

The optional folder is persisted in browser storage and forwarded as the editor folder. It is a user convenience, not OS sandboxing.

## Draft migration dependencies

This code-server migration depends on OpenHands/software-agent-sdk#6792 for
macOS platform support through `additional_artifacts`. The same SDK PR adds
general Windows x64 App backend support. This migration is not merge-ready:
the pinned upstream archives require the contained-file-link extraction
support in that SDK PR. End-to-end installation against its final revision
must pass before release. The editor remains Linux/macOS-only because
[code-server does not publish Windows releases](https://coder.com/docs/code-server/install#windows).
General Windows App support does not supply a Windows editor artifact.

The editor starts without a default folder to avoid an initial redirect that
the authenticated app bridge rejects. Workspace selection also requires a
Canvas host that forwards the app view's folder query.

## Installation smoke coverage

The `VS Code backend smoke` workflow builds the installable App package and
runs it through Agent Server on native Linux and macOS runners. It downloads
the pinned upstream archive, prepares it, serves the editor HTML, stops and
restarts the process, and verifies persistent App data. The workflow pins
an immutable revision of SDK PR #6792 until a containing release is available.
This covers backend installation, not browser editing or Canvas host setup.
