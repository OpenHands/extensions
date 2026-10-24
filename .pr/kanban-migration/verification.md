# Kanban migration verification

Source: OpenHands/canvas-apps `b83068fdce5ec7f85c07b8aefa15d413982059d0`, `kanban-manager/`.
Destination: `OpenHands/extensions`, `apps/kanban-manager/`.

## Preserved identity

- Manifest name `kanban-manager`, version `0.2.0`, page `board`, `/board` contribution.
- `.openhands/vibe-manager/` board files and manager automation names.
- Existing browser preference keys and all application/automation source files.
- Built bundle differs only in esbuild source-path comments and trailing whitespace; executable content is unchanged.

Changes are migration metadata/docs, package-local build inputs, pinned development dependencies and a lockfile, and CI. The catalog entry sets `beta: true`, not automatic enablement.

## Automated checks

- Clean `npm ci --ignore-scripts --no-audit --no-fund` and `npm run check`: 42 passed, two live automation tests skipped without credentials.
- Static App validator passes.
- Apps catalog tests: two passed.
- Public package catalog exports the beta entry; npm dry-run includes manifest, bundle, README and LICENSE, and excludes app node_modules.
- Build dependency publication times checked against npm: esbuild 0.25.12 (2025-11-01), linkedom 0.18.13 (2026-07-07), postcss 8.5.30 (2026-10-12), postcss-prefix-selector 2.2.1 (2026-09-07). All exceed seven days at preparation.

## Real Canvas walkthrough

Unmodified Canvas `fee10e3d2909ebbf9950578575b1ee011492171e`, isolated private HOME and backend, Agent Server/SDK 1.58.1, real Chrome. No browser request mocks. The existing Canvas runtime imports enabled App code through its Blob-based loader.

1. Doctor: authenticated backend, automation health, matching build revision and frontend all pass.
2. Skip first-run setup with telemetry disabled. No model key is configured.
3. Add the migrated package through the real Apps UI. Inventory reports disabled v0.2.0.
4. Enable through the trusted-code confirmation and open Kanban. Empty-board state renders.
5. Arrange a disposable git workspace and saved workspace parent through the real APIs; select the workspace in the Kanban UI.
6. Create a ticket in Pending. Reload and confirm the ticket persists.
7. Open its drawer and append a note; history updates.
8. Disable; navigation disappears. Re-enable; ticket remains.
9. View the board at 390x844 and 1440x1000.
10. Uninstall the package, reinstall, enable, and confirm the existing ticket remains on the same backend.
11. Verify zero automations and zero conversations. Start manager was never clicked. No provider resource or paid model was used.
12. Stop this isolated run and confirm every allocated port is closed.

Evidence: `manual-board-flow.gif`, `reinstalled-board.png`, `phone-board.png`.

The run initially saw expected 404s before its first index file existed. Two fixture-arrangement API requests were corrected (endpoint/schema); these were setup errors, not app failures. A combined status-text wait after reinstall did not match its split DOM text; the actual controls, inventory and persisted ticket verified installation independently.

## Limits and ordering

Manager execution, paid worker dispatch, external/Cloud backends and the open React/SQLite rewrite in canvas-apps #21 were not tested or migrated. Existing app limitations around private backend-registry access and automation routing remain documented, not represented as new portable API guarantees.

No Canvas patch is needed for this move. Its generic source/path install and explicit enable flow already work. The registry's beta metadata is not a new Canvas marketplace UI.

Merge and make the extensions replacement available before retiring the source directory. Existing source URLs pinned to the old commit remain available; old main-branch install/update coordinates will stop working after deletion. Retirement must account for the still-open #21 rewrite. No live data or running service is removed by either source PR.
