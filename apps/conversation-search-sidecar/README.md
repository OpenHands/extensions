# Conversation Search Sidecar

Conversation Search is a local-first Agent Canvas App backed by a native Go sidecar and a persistent [Bleve](https://blevesearch.com/) full-text index. It searches Agent Server conversation history without uploading conversation contents or exposing a daemon port to the browser.

The App is independent: its React bundle, Go source, build/test configuration, documentation, and checked-in `extension.js` live only in this directory. It does not add a repository workspace, shared runtime, or reusable sidecar foundation.

## Evidence from the active SDK store

The implementation was chosen after read-only inspection of the active Agent Server environment and the installed OpenHands SDK 1.17 persistence code. On 2026-09-09 the active store contained 556 conversation directories, roughly 834 MB, and 25,360 files at:

```text
~/.openhands/agent-canvas/dev_conversations/<conversation-id>/
├── meta.json
├── base_state.json
├── events/
│   ├── .eventlog.lock
│   └── event-<five-digit-index>-<event-id>.json
├── observations/             # optional, out-of-line large output
└── TASKS.json                # optional
```

The standard `~/.openhands/dev_conversations` and `~/.openhands/conversations` candidates were absent on that host. `meta.json` supplied stable conversation id, title, creation/update timestamps, and optional initial message. Event JSON supplied stable event id, timestamp, source, `kind`, message content, action/observation variants, tool name, summary, and selected command/output text. Observed kinds included `MessageEvent`, `ActionEvent`, `ObservationEvent`, `ConversationStateUpdateEvent`, `ConversationErrorEvent`, `AgentErrorEvent`, `Condensation`, `InterruptEvent`, and `PauseEvent`.

The installed SDK confirms events are append-only files named by a five-digit sequence and stable event id. The App therefore validates that evidence rather than assuming a monolithic transcript or database.

Discovery always includes these read-only candidates:

- `<agent-server-home>/.openhands/dev_conversations`
- `<agent-server-home>/.openhands/conversations`
- `<agent-server-home>/.openhands/*/dev_conversations`, for explicit persistence roots such as `agent-canvas`
- `<agent-server-home>/dev_conversations`, when the home endpoint already names a persistence root

Candidates are deduplicated and symlinks/non-directories are rejected. Missing, empty, unreadable, unsupported, dual-layout, and partially malformed stores are reported separately. Only `meta.json` and SDK-named `events/event-*.json` files are considered. Source files are never modified.

## Index design and privacy boundary

Bleve 2.5.5 was selected because the observed store is already hundreds of megabytes and tens of thousands of files. Bleve provides a durable native inverted index, relevance ranking, term vectors/highlighting, stored inspector fields, exact keyword filters, date ranges, batched upserts, and deletes. It needs no external database process or CGO library.

Each indexed document has a deterministic SHA-256 id derived from source path, stable conversation id, and stable event id. Stored/indexed fields are:

- conversation id, event id, source JSON path;
- title, timestamp, role/source, event kind, and tool name;
- initial/message/extended text;
- event summary and selected action command or observation content, capped at 32 KiB per record.

The App deliberately excludes `base_state.json`, SDK configuration, configured secret records, system prompts, hidden thoughts/reasoning, raw tool schemas, lock files, out-of-line observations, and task files. Source data may still contain sensitive user or tool text, so the UI explicitly warns that the local index is a searchable sensitive-data copy.

Incremental indexing stores a manifest keyed by absolute source path with file size, nanosecond modification time, SHA-256 content hash, conversation id, indexed document ids, and malformed state. Equal size/mtime files are skipped. If metadata changes, the content hash is the fallback; equal hashes avoid unnecessary indexing. Changed files are upserted, changed conversation metadata refreshes event titles, missing files delete their old documents, and malformed JSON is recorded and skipped without aborting healthy records. **Full rebuild** deletes only the App-owned Bleve index and source manifest, then recreates both.

No App code sends conversation text to a remote service. Network access happens only during deliberate local compilation, when Go downloads the pinned module graph from the configured Go proxy.

## Authenticated CLI bridge and service lifecycle

The browser uses only existing authenticated Agent Server APIs:

1. `GET /api/file/home` discovers and validates the active home.
2. `POST /api/bash/execute_bash_command` runs fixed commands with that home as structured `cwd`.
3. Search/filter/inspector values are JSON encoded and then base64 encoded as one shell-safe argument. They never become shell source.

The one native executable is both the index engine and companion CLI:

```text
conversation-search version
conversation-search once <base64-json>  # one-shot command mode
conversation-search serve               # loopback service mode
conversation-search rpc <base64-json>   # CLI-to-daemon bridge
```

Service mode binds a random `127.0.0.1` port and writes a mode-0600 state file containing its random 256-bit bearer token, pid, port, version, and timestamps. The browser never reads that port and never calls it. The companion CLI reads the state and performs authenticated JSON RPC. Stop is a structured RPC request rather than an interpolated `kill` command. The daemon deletes its state on clean shutdown and automatically stops after ten idle minutes, so browser closure or App disablement cannot leave a permanent process. One-shot mode remains available while the daemon is stopped.

## Deliberate setup and native verification

The first request is a non-mutating Python probe running on the Python-based Agent Server. It reports OS/architecture, Go availability, supported target, partial runtime files, and all data-location diagnostics. It does not create directories, parse conversation contents, download modules, compile code, or start a process.

Supported local-build targets are macOS and Linux on arm64 or amd64. Setup requires Go 1.23 or newer. The App offers no unverified prebuilt download. Before setup, the UI shows:

- source origin/version and target;
- combined source SHA-256 and the exact App data directory;
- module-network and disk actions;
- the sensitive-index disclosure; and
- an explicit acknowledgment checkbox.

After approval, the fixed install command writes the exact bundled `main.go`, `go.mod`, and `go.sum`, verifies their recorded SHA-256 values, downloads the pinned Bleve module graph, builds locally with `-trimpath`, records the output binary SHA-256 and build metadata, and version-checks it. All source and Go module/build caches are redirected into the App data directory. The read-only probe and every native command verify the runtime/source versions and recalculate the binary SHA-256 before execution; a mismatch is never launched. **Repair runtime** stops a verified daemon, or replaces an unverifiable binary before using the repaired CLI to stop it, and preserves the index.

If Go or a supported target is unavailable, **Copy agent setup prompt** asks an OpenHands agent to inspect prerequisites, explain system/network changes, get approval, and keep all App-owned material below the exact directory. The App never guesses a package manager.

Install/build, start, stop, full index rebuild, runtime repair, and data deletion are distinct user-visible actions. Deletion has a second confirmation and targets only the exact App directory.

## App-owned files

```text
<agent-server-home>/.openhands/apps/conversation-search-sidecar/
├── .runtime-version
├── artifact.json                 # version, origin, target, source/binary hashes
├── bin/conversation-search
├── build/
│   ├── src/{main.go,go.mod,go.sum}
│   ├── modcache/
│   ├── gocache/
│   └── gopath/
├── index/
│   ├── bleve/                    # persistent full-text index
│   └── sources.json              # incremental source manifest
├── logs/service.log
└── run/daemon.json               # present only while service runs
```

## Build and automated verification

Go 1.23+ and Node.js are required for the full contributor check:

```bash
cd conversation-search-sidecar
npm install
npm run check
```

`npm run check` verifies the native metadata hashes, TypeScript, a Vite library build, exactly one self-contained `dist/extension.js`, Vitest suites, Go suites, and a real Chromium Blob-import smoke test. The successful build copies the artifact to checked-in `extension.js`.

The Go tests cover missing/empty/dual layouts, observed SDK parsing, safe field selection, valid and malformed records, deterministic persistent indexing, ranking/filtering, incremental no-op/update/deletion behavior, corrupt-index rebuild, daemon health/RPC/search/stop, and idle cleanup. Browser tests cover the single declared page, its search/index-operations nested routes, unknown routing, disposal, unsafe home rejection, non-mutating diagnostics, supported/missing prerequisite states, approval-gated build, source/binary verification commands, base64 query isolation, search/inspection, index/rebuild controls, service start/stop state, repair, and two-step deletion.

## Local Agent Canvas acceptance checklist

The Apps UI has no refresh button. Rebuild, uninstall, and reinstall the App before testing a changed bundle.

1. Run `npm install && npm run check` in this directory.
2. Install the App from the absolute local `conversation-search-sidecar/` path and enable its single **Conversation Search** page. **Index operations** is a nested route inside that page, not a second manifest registration.
3. Open **Conversation Search**. Confirm the initial probe says it was read-only; verify target, Go version, exact App data path, and diagnostics for `dev_conversations`, `conversations`, and any discovered persistence root.
4. Confirm install is disabled until the sensitive-data/network/disk acknowledgment is selected. If Go is absent, copy the agent prompt and verify it requests approval before system changes. With Go available, build/install and confirm the binary/source/artifact files stay below the displayed App directory.
5. In **Index operations**, click **Index now** in command mode. For real data, verify document/source/conversation counts, progress summary, malformed count, timestamp, and nonzero index size. Check that source conversation mtimes/content did not change.
6. Run Index now again and verify most/all files are reported unchanged. Add or change a disposable SDK-format event, index again, and verify only affected records update. Remove that disposable event and verify its search result disappears.
7. Search known message text. Exercise role, kind, tool, after, and before filters. Open a result and verify conversation id, event id, source path, metadata, and capped selected text. Confirm hidden reasoning/system configuration is not present.
8. Start service mode. Search again, reload Canvas, and verify the App reconnects through the companion CLI. Inspect `service.log` and `run/daemon.json` permissions without copying its token. Stop the service and verify command mode still searches.
9. Start service, leave it idle for more than ten minutes, and verify the process and daemon state stop automatically. Disable/re-enable the App and verify it reconnects if still inside the idle window or falls back cleanly to command mode.
10. Corrupt only a disposable copy of the App index, confirm the error is clear, then use **Full rebuild** and verify recovery. Use **Repair runtime** and verify the index remains.
11. Click **Review deletion**, cancel once, and confirm nothing changed. With disposable index data, click **Delete exact directory** and verify only `.openhands/apps/conversation-search-sidecar/` is removed; conversation stores and sibling Apps remain.

If a local Agent Server, suitable real conversations, or a ten-minute manual idle window is unavailable, record those checks as not run. The Blob smoke test is not a substitute for local Canvas acceptance.
