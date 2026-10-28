# Browser SQL Lab

Browser SQL Lab is a standalone Agent Canvas App that runs a genuine SQLite database entirely in the browser. SQL.js and its WebAssembly engine execute inside an inline Web Worker; the Worker serializes the database into IndexedDB after migrations and mutations. React, CSS, Worker code, WASM, a SQL migration, and JSON seed data are all embedded in the checked-in `extension.js`.

The App does not call the Agent Server, use a CDN or Service Worker, install prerequisites, download runtime files, or start a background process.

## What it includes

- A SQL editor with Cmd/Ctrl+Enter execution and request cancellation
- Scrollable result grids with bounded rendering for large results
- A live schema explorer and applied migration list
- Persistent query history
- An idempotent seed action backed by imported `src/seed-data.json`
- Database export as a standard `.sqlite3` file
- A confirmed reset flow that rebuilds the database and reapplies `src/migrations/001-create-library.sql`
- Startup and actionable IndexedDB/WASM error states
- `/sql-lab`, `/sql-lab/lab`, and `/sql-lab/about` route handling plus unknown-route recovery

## Persistence and privacy

Data is browser-local. Each database is stored in IndexedDB under a database name shaped like:

```text
browser-sql-lab::<URL-encoded host.backend.id>
```

That namespaces data by both the App name and active Canvas backend. Reloading or disabling and re-enabling the App preserves data for the same browser profile and backend. A different backend ID opens a separate database. Clearing site data, using a different browser profile, or choosing **Reset** removes or replaces that local state. No database bytes or SQL text are sent to the Agent Server.

## Develop and verify

Requirements: Node.js 22.12 or newer, npm, and Google Chrome (or set `CHROME_PATH`).

```sh
npm install
npm run check
```

Run commands from this `browser-sql-lab` directory. The checks perform:

1. TypeScript validation.
2. A Vite 8 production build.
3. Artifact validation proving `dist/extension.js` is the only output, contains the embedded WASM/migration/seed assets, and has no unresolved imports or sibling runtime URLs. A successful build synchronizes this output to the checked-in root `extension.js`.
4. Unit and integration tests covering activation, declared-page registration, routing, Worker RPC success/error/cancellation, real SQLite migration and seed execution, per-backend IndexedDB isolation, query rendering, reset, remounting, and cleanup.
5. A real-Chrome smoke test that imports the checked-in bundle from a Blob URL, starts WASM in the inline Worker, seeds and queries SQLite, verifies data survives remount for one backend, verifies a second backend is empty, and checks Worker/DOM cleanup.

Individual commands are available as `npm run typecheck`, `npm run build`, `npm test`, `npm run test:blob`, and `npm run check:artifact`.

## Local Canvas acceptance checklist

The Apps screen currently has no refresh action. After any rebuild, uninstall and reinstall the App rather than expecting Canvas to refresh its bundle.

1. From this directory, run `npm install` and `npm run check`.
2. Run `pwd` and copy the absolute `browser-sql-lab` directory path.
3. In Agent Canvas, open **Settings → Apps**, choose **Install from local path**, paste that absolute path, and install.
4. Enable **Browser SQL Lab** and open **SQL Lab** from the navigation.
5. Confirm the startup screen resolves to the workbench and the green browser-local banner shows a namespace containing the active backend ID.
6. Choose **Seed data**, run the starter query, and confirm authors and average ratings render in the results grid. Run invalid SQL and confirm a SQLite error appears without breaking the App.
7. Open a schema table, select a query from History, visit **About**, and return to **Workbench**.
8. Reload Canvas. Run `SELECT COUNT(*) AS total FROM books;` and confirm the five rows survived.
9. Export the database and confirm a non-empty `.sqlite3` file downloads.
10. Switch Canvas to a backend with a different `host.backend.id`, reopen SQL Lab, and confirm its namespace differs and `books` initially has zero rows. Switch back and confirm the original five rows remain.
11. Choose **Reset**, cancel once with **Keep data**, then confirm reset. Verify the `books` schema and migration remain while the table and History are empty.
12. Disable the App and confirm its page is unavailable. Re-enable it and confirm the correct backend-local database reopens.
13. For a source change, rebuild, uninstall, reinstall from the same absolute path, and repeat the primary flow.

## Source and artifact layout

All implementation and build machinery is local to this directory. `src/database.worker.ts` owns SQLite initialization and IndexedDB writes; `src/database-client.ts` owns cancellable Worker RPC; `src/database-core.ts` owns migrations, schema/history inspection, query execution, and seed insertion. Vite inlines the Worker and every asset into exactly one `extension.js`. Mutable database state never lives in the installed App directory.
