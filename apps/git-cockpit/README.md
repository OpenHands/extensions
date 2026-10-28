# Git Cockpit

Git Cockpit is a standalone Agent Canvas App that turns a selected Agent Server Git worktree into a focused, read-only dashboard. It covers repository status, local and remote branches, the latest 30 commits, changed files, staged and unstaged diff totals, individual tracked-file diffs, and commit detail.

React, CSS, command policy, parsers, onboarding, and routing are bundled into the checked-in `extension.js`. Runtime users do not need Node.js or any sibling App assets. Git is the only repository prerequisite.

## Execution boundary and safety

**Every active Git operation is read-only and executes on the active Agent Server machine.** Git Cockpit does not send repository data to a third party, expose a terminal or arbitrary command field, update Git configuration, use credentials, or write a repository file, ref, index entry, commit, stash, worktree, or remote.

The App enforces these boundaries:

1. Workspace candidates come only from `GET /api/workspaces` and `GET /api/file/search_subdirs` on the active Agent Server.
2. A workspace must be an absolute, control-character-free path without `.` or `..` traversal. It is passed in the structured `cwd` request field and is never interpolated into shell text.
3. Repository overview requests use exact command constants. `git status` sets `GIT_OPTIONAL_LOCKS=0` to suppress optional index refresh locks. Branch and history results are bounded to 100 refs and 30 commits.
4. An individual diff can be requested only for a strictly validated relative path already returned by status. The path is UTF-8/base64 encoded in the browser, checked against the base64 alphabet, decoded into a quoted shell variable, and passed after Git's `--` separator. The raw path never appears in command text. Output is capped at 180 KB.
5. Commit detail accepts only a full 40-character lowercase hexadecimal object ID already present in the bounded log. Output is capped at 180 KB.
6. Non-zero Agent Server command responses and stderr become visible error states. Route changes, unmounting, or disabling the App abort the browser-side operation and prevent stale results from rendering.

The active fixed repository command set is:

- non-mutating Git/worktree/package-manager prerequisite probe;
- `GIT_OPTIONAL_LOCKS=0 git status --porcelain=v2 --branch -z --untracked-files=all`;
- `git for-each-ref --sort=-committerdate --count=100 ... refs/heads refs/remotes`;
- `git log -n 30 ...`;
- staged and unstaged `git diff --numstat`;
- staged and unstaged `git diff --unified=3 -- "$file_path"`; and
- `git show --format=fuller --stat --summary --no-renames --max-count=1 <validated-hash> --`.

There is no common CLI abstraction or shared runtime. All code and policy are owned by `git-cockpit/`.

## Prerequisite onboarding

The first-run probe checks for Git, records `git --version`, validates the selected directory with `git rev-parse --is-inside-work-tree`, detects one supported package manager, and checks whether a non-interactive install is possible. The probe itself does not mutate state.

If Git is missing, the onboarding screen:

- states that installation changes software on the Agent Server;
- shows the exact fixed install template and what it may download or change;
- requires an explicit acknowledgement checkbox before enabling the install button;
- offers **Recheck Git**; and
- offers a fixed, copyable prompt for an OpenHands agent to inspect the host, explain the change, obtain any needed approval, install Git, and avoid repository changes.

Direct installation is the only mutating onboarding exception and is never represented as a Git repository operation. The supported templates are:

| Detected manager | Controlled command | Downloads and persistent changes |
| --- | --- | --- |
| Homebrew | `brew install git` | Downloads a Git formula and dependencies; writes under the configured Homebrew prefix and updates Homebrew's package records. |
| APT | `apt-get update` then `DEBIAN_FRONTEND=noninteractive apt-get install -y git`, using the current root user or non-interactive `sudo -n` | Refreshes package indexes; downloads Git and dependencies; updates the OS package database and system package files. |
| DNF | `dnf install -y git`, using the current root user or non-interactive `sudo -n` | Downloads Git and dependencies; updates the OS package database and system package files. |
| APK | `apk add git`, using the current root user or non-interactive `sudo -n` | Downloads Git and dependencies; updates the Alpine package database and system package files. |

If no supported manager or non-interactive privilege is available, the install button is not rendered; only the agent prompt and recheck flow remain. The App does not download packages itself, verify package checksums independently, start a background process, or create an App data directory. Package authenticity and checksums remain the configured package manager's responsibility.

## Planned write operations

The dashboard and workspace picker contain a clearly marked **Planned write operations** area. It previews staging/unstaging, branch creation and switching, commit, stash, fetch/pull/push, and revert/reset recovery.

Every preview control is a native disabled button. It has no event handler and cannot initiate an Agent Server request on click or focus. These capabilities are not available in version 0.1.0.

A later App revision must treat each write workflow as a separate safety design. At minimum it will need an exact operation preview, validated and narrowly encoded inputs, worktree/ref/race checks, carefully scoped recoverability, credential and network boundaries where relevant, and explicit user confirmation immediately before execution. Visual presence in this release is not authorization to implement or invoke a write command.

## Persistence

Git Cockpit persists only the last selected workspace token and active dashboard tab in `localStorage`. The key is namespaced by the active backend's kind, organization ID, and backend ID. Repository results, paths beyond the selected-workspace token, diffs, commit data, source text, and onboarding state are not persisted.

No mutable data is written inside the installed App directory. No `.openhands/apps/git-cockpit/` directory, backend database, cache, downloaded asset, temporary repository file, or background service is created.

## Develop and verify

Requirements are Node.js 22.12 or newer, npm, Git, and Google Chrome (or `CHROME_PATH`). From this directory:

```sh
npm install
npm run check
```

`npm run check` performs:

1. strict TypeScript checking;
2. a Vite production build;
3. artifact validation proving `dist/extension.js` is the only output, the bundle exports `activate`, CSS and dependencies are inline, and no imports, external chunks, relative assets, CommonJS requires, or source map remain;
4. unit and real-Git integration tests for activation, routing, workspace selection/discovery, prerequisite parsing and deliberate installation, exact request shapes, status/branch/log/numstat parsing, path and hash validation, error states, backend preference scoping, detail views, cleanup, and planned controls; and
5. a real-Chrome smoke test that imports the checked-in bundle from a Blob URL, mounts picker/dashboard/file-detail/safety routes, verifies fixed requests and structured `cwd`, proves all six planned controls remain disabled and request-free, and verifies DOM and registration cleanup.

Individual commands are `npm run typecheck`, `npm run build`, `npm test`, `npm run test:blob`, and `npm run check:artifact`. `npm run build` copies the sole Vite output to the checked-in root `extension.js`.

## Local Canvas acceptance checklist

The Apps screen has no refresh action. After rebuilding, uninstall and reinstall the App before testing the changed bundle.

Prepare a disposable Git repository that has at least one committed file, one staged modification, one unstaged modification, one untracked file, multiple branches, and several commits.

1. Run `npm install` and `npm run check` in `git-cockpit/`.
2. Run `pwd` and copy the absolute `git-cockpit` directory path.
3. In Agent Canvas, open **Settings → Apps**, choose **Install from local path**, paste that absolute path, and install.
4. Enable **Git Cockpit**, open it from navigation, and confirm the **Planned write operations** area is visually separate, every control is disabled, and click/focus attempts cause no loading state or request.
5. Confirm the picker lists only workspaces reported by the active Agent Server. Select the disposable repository.
6. Confirm the non-mutating gate reports the Git version and validates the worktree. Also select a non-Git workspace and confirm the helpful invalid-worktree state.
7. If a safe disposable Agent Server without Git is available, confirm onboarding describes the machine boundary, manager-specific persistent changes, exact template, acknowledgement gate, fixed agent prompt, failed-install state, and recheck flow. Do not test package installation on a machine where changing system software is unwanted.
8. In **Changes**, compare staged, unstaged, and untracked paths and diff totals with `git status` and `git diff --numstat`. Open tracked paths and verify staged/unstaged patches. Open an untracked path and confirm the App explains why no Git diff exists.
9. In **History**, inspect recent author/date/subject values and open a commit detail. In **Branches**, compare local/remote refs and the current marker with Git CLI output.
10. Reload Canvas and confirm the workspace/tab preference is restored only for the same backend while repository results reload from Git.
11. Disable the App and confirm its page is unavailable. Re-enable it, reopen the page, and repeat the primary status/diff flow.
12. Rebuild, uninstall the App, reinstall from the same absolute local path, and repeat steps 4–11 to validate a changed bundle.

## App-local layout

- `src/git-service.ts` owns workspace discovery, validation, fixed command templates, onboarding installation templates, request handling, and Git protocol parsing.
- `src/preferences.ts` owns backend-scoped harmless browser preferences.
- `src/App.tsx` owns nested routing, picker/onboarding/dashboard/detail states, and the planned-write roadmap.
- `src/extension.tsx` owns page registration, style/React mounting, request cancellation, and cleanup.
- `src/git-integration.test.ts` runs the real fixed protocols against a temporary disposable Git repository.
- `scripts/check-artifact.mjs` and `scripts/blob-smoke.mjs` prove the installed artifact is one self-contained Blob-compatible ESM file.

All implementation, dependencies, tests, build assets, and documentation are local to `git-cockpit/`.
