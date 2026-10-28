# WASM Repo Lens

WASM Repo Lens is a standalone Agent Canvas App that turns a selected Agent Server workspace into an in-browser repository analysis. Two fixed, read-only command templates collect a bounded repository snapshot. A dependency-free Rust engine, compiled to WebAssembly and running inside an inline Web Worker, computes language and directory distribution, large-file and churn hotspots, declared dependencies, and import summaries.

React, CSS, Worker source, and the compiled WASM engine are embedded in the checked-in `extension.js`. Runtime users do not need Node.js, Rust, Cargo, wasm-pack, or a network download.

## Data boundary and safety

The App has one explicit data flow:

1. It discovers candidates from `GET /api/workspaces` and `GET /api/file/search_subdirs` on the active Agent Server.
2. It accepts only absolute, control-character-free paths returned by that discovery. A selected path is passed as the structured `cwd` field to `POST /api/bash/execute_bash_command`; it is never interpolated into shell text.
3. A fixed prerequisite script detects `git` and `rg`. A second fixed script reads a bounded inventory, source samples, branch, and recent Git path history.
4. The snapshot moves to an inline browser Worker. The embedded Rust/WASM engine performs the analysis there.
5. The source snapshot is kept only in memory for that run. The App uses no localStorage, IndexedDB, server-side index, analytics endpoint, or background process. **Export analysis JSON** is a deliberate user action and exports aggregates only, never sampled source.

There is no terminal UI and no text field that can become a command. The App never writes repository files and never runs an installer. If `git` or `rg` is missing, onboarding offers a fixed, copyable OpenHands-agent setup prompt and a recheck action. The agent must detect the operating system and obtain user authority for any relevant system change.

## Bounded snapshot

The snapshot command:

- uses `rg --files --hidden` and excludes `.git`, dependency, environment, build, and generated-output directories;
- inventories at most 5,000 files;
- reads at most the first 4,096 bytes from each of at most 250 supported source or manifest files;
- reads only file paths from the latest 200 Git commits for churn counts;
- base64-encodes paths and sampled bytes before emitting the line protocol, so shell metacharacters never become executable text; and
- preserves complete protocol records while independently limiting inventory to 300 KB, history to 150 KB, and source samples to 350 KB; and
- runs with a 45-second Agent Server timeout. The combined response remains below the Agent Server synchronous endpoint's 1 MiB event boundary.

The Rust engine validates and decodes that protocol, rejects parent traversal paths, classifies common language extensions, and bounds every rendered ranking. A repository exceeding the file cap is marked as truncated in the UI and export.

## Prerequisites

App users need an active Agent Server whose selected workspace has:

- `git`, for current-branch and churn data; and
- `rg` (ripgrep), for bounded file discovery.

The first-run probe is non-mutating. Missing tools are explained in the App. The copyable setup prompt asks an OpenHands agent to identify the host package manager, install only missing prerequisites after appropriate user action, avoid repository changes, and verify both version commands.

No background services, writable App data directory, downloads, or persistent files are created by WASM Repo Lens.

## Develop and verify

Requirements for ordinary App development are Node.js 22.12 or newer, npm, and Google Chrome (or `CHROME_PATH`). Run from this directory:

```sh
npm install
npm run check
```

`npm run check` performs:

1. strict TypeScript checking;
2. a Vite production build;
3. artifact validation proving `dist/extension.js` is the only output, includes inline CSS, Worker code, and WASM, and has no unresolved imports or sibling runtime URLs;
4. 26 tests covering activation, declared-page registration, host-version validation, nested routing, workspace/probe success and failures, path validation, exact command request shapes, Worker RPC/error/cancellation, visualization state, onboarding, and cleanup; and
5. a real-Chrome smoke test that Blob-imports the checked-in bundle, discovers a fixture workspace, runs both fixed commands, executes the actual Rust/WASM engine in the inline Worker, checks rendered metrics and the nested data-boundary route, and verifies DOM/Worker/registration cleanup.

Individual commands are `npm run typecheck`, `npm run build`, `npm test`, `npm run test:blob`, and `npm run check:artifact`.

### Rebuild the Rust engine

Rust is a contributor-only requirement. Install a current stable Rust toolchain through the official rustup installer, add the compilation target, and rebuild:

```sh
rustup target add wasm32-unknown-unknown
npm run build:wasm
npm run build
```

The build compiles `rust-engine/src/lib.rs` as an optimized `cdylib` and copies `rust-engine/target/wasm32-unknown-unknown/release/repo_lens_engine.wasm` to `src/repo_lens_engine.wasm`. No third-party Rust crates, wasm-bindgen, or wasm-pack are used. Cargo build output remains ignored under `rust-engine/target/`.

The checked-in WASM for version 0.1.0 has SHA-256:

```text
370bed950deee7e2d04d6cfe764436360545413cc0dfbc8e57867d9bd7a307c2  src/repo_lens_engine.wasm
```

After changing Rust, commit the rebuilt `src/repo_lens_engine.wasm` and the regenerated root `extension.js`. `npm run build` synchronizes the sole Vite output to the checked-in root artifact.

## Local Canvas acceptance checklist

The Apps screen currently has no refresh action. After any rebuild, uninstall and reinstall the App rather than expecting Canvas to refresh its bundle.

Use a small test Git repository with several language types, at least one supported dependency manifest, a large file, and a few commits touching different files.

1. Run `npm install` and `npm run check` from this directory.
2. Run `pwd` and copy the absolute `wasm-repo-lens` directory path.
3. In Agent Canvas, open **Settings → Apps**, choose **Install from local path**, paste that absolute path, and install.
4. Enable **WASM Repo Lens** and open **Repo Lens** from the navigation.
5. Confirm the workspace picker contains only directories reported by the active Agent Server. Select the small test repository.
6. Confirm the non-mutating readiness check marks `git` and `ripgrep` available. If either is absent, confirm the App explains the missing tool, copies the fixed setup prompt, performs no install itself, and **Recheck prerequisites** works after external setup.
7. Choose **Analyze repository**. Confirm file/byte/language/dependency totals and the language, directory, large-file, churn, dependency, and import panels render plausible results.
8. Start another analysis and immediately select a different workspace or open **Data boundary**. Confirm the in-flight operation cancels without an error toast or stale results.
9. Return to the original repository and analyze again. Choose **Export analysis JSON** and confirm the downloaded file contains metrics but no sampled source text.
10. Open **Data boundary** directly through its nested route and return to **Analysis**.
11. Reload Canvas, reopen the App, and confirm no previous source snapshot or analysis is restored.
12. Disable the App and confirm its page is unavailable. Re-enable it, reopen the page, select the repository, and complete one more analysis.
13. For a source change, rebuild, uninstall the App, reinstall from the same absolute path, and repeat the primary flow.

## App-local layout

- `src/repository-service.ts` owns discovery, path validation, and the two fixed Agent Server commands.
- `src/analysis-client.ts` owns cancellable Worker RPC. Cancellation terminates active WASM work and creates a fresh Worker for later analysis.
- `src/analysis.worker.ts` loads the embedded WASM data URL and bridges its allocation/result ABI.
- `rust-engine/` owns the Rust protocol parser and repository-analysis domain logic.
- `src/App.tsx` owns routing, prerequisite onboarding, visualization, explicit aggregate export, and the user-facing data boundary.
- `scripts/check-artifact.mjs` and `scripts/blob-smoke.mjs` prove the installed artifact is one self-contained Blob-compatible ESM file.

All implementation, dependencies, tests, build assets, and documentation are local to `wasm-repo-lens/`.
