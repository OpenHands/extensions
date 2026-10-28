# Backend SQLite Studio

Backend SQLite Studio is a focused Canvas App for a durable SQLite database on the active Agent Server. Multiple Canvas clients and OpenHands agents can share the same database because the persistence boundary is the backend filesystem, not browser storage.

The App deliberately separates two kinds of state:

- Shared data, schema, migrations, and query history live in `~/.openhands/apps/backend-sqlite-studio/studio.sqlite3` on the selected Agent Server.
- The small action record used to explain setup/data mutations is browser-local and scoped by backend id. Editor text is React state and disappears on remount.

The real home directory is never assumed. Every mount discovers it with `GET /api/file/home`, validates the returned absolute path, and passes it as the structured `cwd` field to the authenticated `POST /api/bash/execute_bash_command` endpoint.

## First-run and repair flow

The first request is a non-mutating probe. It checks for `python3`, verifies that Python can import its standard-library `sqlite3` module, reports Python and SQLite versions, optionally reports the `sqlite3` CLI version, and inspects whether the App-owned wrapper, runtime marker, and database already exist. The probe does not create a directory, open a database, download software, or run an installer.

Before **Install** or **Repair** is enabled, the UI shows:

- the detected runtime and versions;
- the exact App data directory and database path;
- every file the App setup owns;
- the consequences of setup; and
- a confirmation checkbox.

Install and Repair use the same fixed command template. It creates only `.openhands/apps/backend-sqlite-studio/`, writes the bundled versioned `wrapper.py` and `.runtime-version`, and asks that wrapper to initialize the database and apply migrations. Repair replaces the wrapper and marker but preserves an existing database. Nothing is downloaded and no background process is started.

If Python's SQLite runtime is unavailable, the App does not guess a package manager or install it. **Copy agent setup prompt** gives an OpenHands agent a fixed, path-aware request to inspect the host, explain any system changes, get user approval, install only if needed, and verify the runtime. **Recheck** reruns only the non-mutating probe.

## Structured SQL boundary

There is no shell console. SQL editor text is split into complete statements in the browser, serialized as JSON, UTF-8/base64 encoded, and passed as one shell-safe argument to the fixed Python wrapper. Import bytes use the same base64 JSON envelope. The wrapper decodes the payload and uses Python's `sqlite3` API; user text never becomes shell source.

The wrapper rejects transaction-control statements, `ATTACH`, `DETACH`, `VACUUM INTO`, extension loading, writable-schema changes, and references to its internal migration/history tables. This keeps the editor within the one App-owned database and intentionally avoids becoming a generic database administration console. Result sets are limited to 250 rendered rows.

The initial migration creates a small `notes` table. The Studio includes a schema browser, applied migration list, SQL editor, result grids, recent persistent query history, database size/journal status, validated import, export, and a browser-local mutation record. The Agent handoff page exposes the exact database path and copyable safety instructions for parameterized agent writes.

## Import, export, and reset

- **Export** uses SQLite's backup API to create a consistent temporary snapshot inside the App directory, downloads it in the browser, and removes the temporary file.
- **Import** accepts at most 16 MiB, requires a second explicit click, checks the SQLite header and `PRAGMA integrity_check`, atomically replaces only `studio.sqlite3`, and reapplies App migrations.
- **Reset data** first opens an alert dialog showing the exact directory. Only the second **Delete exact directory** action runs the fixed reset command. That command resolves and compares `.openhands/apps/backend-sqlite-studio` under the validated home `cwd`, then deletes only that directory. Reset removes the database, migrations, persistent query history, wrapper, and marker and cannot be undone. The browser-local action record retains the reset event.

## App-owned backend files

```text
<agent-server-home>/.openhands/apps/backend-sqlite-studio/
├── .runtime-version       # wrapper contract version
├── wrapper.py             # fixed, bundled structured SQLite wrapper
└── studio.sqlite3         # shared database, migrations, query history
```

Temporary import/export data is written as `.import.sqlite3.tmp` or `.export.sqlite3.tmp` in that same directory and removed whether the operation succeeds or fails. The App performs no network downloads and starts no background service.

## Build and automated verification

The App is independent and has no repository-wide workspace or shared runtime.

```bash
cd backend-sqlite-studio
npm install
npm run check
```

`npm run check` performs TypeScript checking, a Vite library build, artifact validation, Vitest suites, and a real Chromium Blob-import smoke test. The build emits exactly one `dist/extension.js`; validation checks that it has inline CSS, no bare imports, external chunks, sibling assets, source map, or external runtime URLs. A successful build copies that artifact to the checked-in `extension.js`.

Tests cover activation, both declared pages, nested/unknown routing, cleanup, home discovery, unsafe-home rejection, non-mutating probe states, fixed setup commands, migration success/failure envelopes, SQL parsing, base64 command construction, result rendering, query failures, data-directory isolation, reset confirmation, exact reset targeting, action recording, and agent handoff text.

## Local Agent Canvas acceptance checklist

The Apps UI has no refresh control. After every code change, rebuild and then uninstall/reinstall this App from its absolute local path before retesting.

1. Run `npm install && npm run check` in this directory.
2. In Agent Canvas, install the App from the absolute `backend-sqlite-studio/` path and enable both pages.
3. Open **SQLite Studio**. Confirm the first-run probe explains that it did not mutate state and shows the resolved home, exact data directory, database path, Python/SQLite versions, and optional CLI state.
4. Confirm **Install** is disabled until the acknowledgment is selected. Install, then verify the status cards, `notes` schema, migration `001-create-notes`, empty history, and database path.
5. Run `INSERT INTO notes(title, body) VALUES ('Canvas', 'durable');`, then run the starter query. Verify the row, result grid, and history.
6. Reload Canvas and verify the row remains. If a second browser/client is available, connect it to the same backend, install/enable the App there, and verify the same row appears.
7. Open **Agent handoff**, copy the instructions, and ask an OpenHands agent to insert a row with parameterized SQL at the displayed path. Return to Studio, reload, and verify the agent-written row.
8. Export the database. Choose it for Import, cancel once, then confirm import and verify schema/data remain.
9. Open Reset data. Confirm no backend request occurs before the second confirmation, the exact App directory is visible, and cancel once. Confirm reset only with disposable test data; verify onboarding returns and no sibling `.openhands/apps/` directory was touched.
10. Reinstall, create another row, disable and re-enable the App, and verify durable data remains. Exercise Repair and confirm rows are preserved.

If no second client or local Agent Server is available, record those manual checks as not run rather than treating the Blob smoke test as a substitute.
