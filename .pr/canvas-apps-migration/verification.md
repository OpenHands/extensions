# Canvas apps migration verification

Source: OpenHands/canvas-apps `b83068fdce5ec7f85c07b8aefa15d413982059d0`, the 14 Apps other than Kanban Manager (moved in #841). Terminal was imported and then removed again (see below), so 13 are added.
Destination: `OpenHands/extensions`, `apps/<app>/`, registered in `apps/catalog.json`.

## What changed beyond the import

The first commit imports each App unchanged, with the source repository's MIT license. Every later change is in its own commit:

| App | Problem | Fix |
|---|---|---|
| usage-insights | `shows reported cost provenance badge` failed once its 2026-09-29 fixtures were more than seven days old (the default view) | Tests pin the clock to 2026-09-30 |
| vite-showcase | `npm run check` failed at typecheck: `vite.config.ts` uses `node:path` and `import.meta.dirname` without Node types | `@types/node` ^25.9.9 (published 2026-10-01) and `"node"` in `types` |
| canvas-pulse, conversation-trace | Tests shipped with no package to run them | `package.json` + lockfile (vitest 3.2.7, jsdom 26.1.0, both published months ago) |
| 7 Apps with Blob smoke scripts | Defaulted to the macOS Chrome path | `CHROME_PATH`, then macOS and Linux locations, with a clear error |
| extension-lab | Manifest declares Pattern Gallery and Stress Test, but only the dashboard was registered, so Canvas showed no sidebar entries for them | Register all three pages; test |
| extension-lab | Stress Test page rendered its log above the header and navigation | Mount the log inside the shell after the header; test (fails on the old code) |
| all 13 | READMEs said Customize → Extensions, `github:owner/repository` or a local path | Install from the registry tree URL at a reviewed commit; credit and link the canvas-apps source |

Both Extension Lab bugs were found by the live catalog smoke below, not by the Apps' own tests.

Repository plumbing: catalog entries for all 13, a catalog test that every App directory is catalogued with a matching manifest, README, license and source credit, per-App `.gitignore`/`.npmignore` (no `node_modules`, `dist`, tests or lockfiles in the npm package), and a `Canvas Apps` CI matrix that runs each App's `npm run check`, the Canvas App validator and a check that the committed `extension.js` is current.

## Automated checks (local, Node 24)

For each of the 13 Apps: clean `npm ci --ignore-scripts`, `npm run check`, `validate-extension.mjs`. All pass, and every rebuilt `extension.js` is byte-identical to the committed bundle except extension-lab, whose bundle is its source copied verbatim.

| App | Unit tests | Also in `check` |
|---|---|---|
| agent-memory-viewer | 10 | Blob smoke |
| backend-sqlite-studio | 30 | typecheck, build, Blob smoke |
| browser-sql-lab | 20 | typecheck, build, Blob smoke (WASM + Worker query) |
| canvas-pulse | 1 | `node --check` |
| conversation-search-sidecar | 27 | Go native tests, typecheck, build, Blob smoke |
| conversation-trace | 5 | `node --check` |
| extension-lab | 27 | build |
| git-cockpit | 44 | typecheck, build, Blob smoke |
| personal-profile | 10 | |
| snake-arcade | 9 | `node --check` |
| usage-insights | 22 | `node --check` |
| vite-showcase | 12 | typecheck, build, Blob smoke |
| wasm-repo-lens | 26 | typecheck, build, Blob smoke (Rust/WASM) |

Repository suite: `uv run --group test pytest tests/` passes (1530 passed, 23 skipped). `npm pack --dry-run`: 2.9 MB packed / 918 files, up from 1.5 MB / 735 on main, with no `node_modules` or `dist`.

## Live Canvas smoke

OpenHands main `6354932`, a fresh isolated `control-openhands launch` (Agent Server 1.58.1, no LLM), real Chromium, no request mocks. The recipe is `F20.registry-smoke` from OpenHands/OpenHands#19049, run unchanged except that it cloned this branch instead of main.

For each of the 16 catalog Apps it pasted `https://github.com/OpenHands/extensions/tree/9269e5ad42128afef3412b31f56b4c29decfb3b3/apps/<id>` into **Add app**, checked that the card's resolved ref is that commit, enabled the App through the trust confirmation, clicked the rail entry of every page in its manifest, snapshotted and screenshotted it, swept `browser errors --app-only`, and uninstalled the App through its card.

Result: 19 of 19 pages pass, no unexpected app errors, and the installed list ends empty. Screenshots are in `smoke/`, with an overview in `contact-sheet.png`. Earlier runs of the same recipe on this branch were the before evidence for the Extension Lab fixes: at `b1bf199`, Pattern Gallery and Stress Test failed with no rail entry, and at `3f0e2cb` the Stress Test screenshot showed its log above the header.

VS Code's page reads `VS Code is unavailable because this Agent Server does not support managed App backends.` because a default launch has no app-backend ingress. That is the App's own message, and it is unchanged by this PR.

## Primary flows

Same run, Apps installed from the same commit:

- Browser SQL Lab: **Seed data**, then **Run query**; the result table lists 4 authors with book counts and average ratings (`flows/sql-lab-query.png`).
- Snake Arcade: **Start game** and arrow keys; the status reads `Game started.` and the board is in play (`flows/snake-playing.png`).

No page or app errors were logged during these flows.

## Left out

Terminal is not added. It runs arbitrary commands typed by the user, and `skills/canvas-extension-api/references/backend-safety.md` says Apps must never expose a general terminal; the #843 triage calls it out of scope for the public registry. It passed the same checks and smoke as the others before it was removed, so the smoke counts above (19 pages, 16 Apps) still include it.

## Not covered

Backend setup flows that write to the Agent Server home (SQLite Studio's initialize, Conversation Search's native build) were only shown at their read-only first-run probe. Data-driven Apps were seen with empty data on a fresh backend. Personal Profile's GitHub lookup was not exercised.

Installations made from canvas-apps do not follow the move, because **Update** re-clones the recorded source; each README says to uninstall and reinstall. Retiring the canvas-apps copies is a separate step for that repository.
