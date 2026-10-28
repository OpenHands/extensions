# Kanban Manager

**Beta.** Install explicitly and enable only after reviewing the source.

Kanban Manager is a board for agent work. You queue requests as cards, a
manager agent picks them up and dispatches workers, and the board shows what
each agent is doing right now and what has landed.

It is a Canvas Extension with no server of its own. Everything it needs — the
board, its settings, ticket attachments — is JSON on the Agent Server's own
filesystem, written through the file API.

(Previously published here as `vibe-board`.)


## Install in Agent Canvas

In **Customize -> Apps -> Add app**, use:

- Source: `https://github.com/OpenHands/extensions`
- Path within repository: `apps/kanban-manager`
- Revision: choose the reviewed release tag or commit containing this app.

Installation leaves the app disabled. Review the source and revision, then
choose **Enable trusted app**. Open **Kanban Manager** from the navigation.
The app uses the active Agent Server's file API. Cloud backends do not currently
support Canvas Apps.

### Existing installations

The app name remains `kanban-manager` (version `0.2.0`), and its board data
remains at `~/.openhands/vibe-manager/` on the same Agent Server. Browser keys
such as `vibe.workspace` and `vibe.theme` also stay unchanged. Moving this
package does not move, rewrite, or delete that data or any manager automation.

When switching an existing installation, stop active UI edits, disable the old
app, and remove its installed package through Canvas. Do not delete its board
data. Install the new coordinates above on the **same backend**, then enable
and check that the existing workspaces and tickets appear. Do not run two
copies under different app names against the same data. A workspace that moved
to a different Agent Server needs a separate, deliberate data migration.

### Compatibility and optional manager

The board works as a manual Kanban without starting an automation. Enabling the
app does not start a manager or create a conversation. **Start manager** is an
explicit, separate action and can dispatch agents that use paid models.

The imported manager, chat, and attachment features rely on the existing
Canvas backend registry and a deployment that exposes the Automation service
at `/api/automation/v1` using the selected backend's credentials. This is not
a portable host-API guarantee: a remote backend without that route can use the
manual board, but manager actions may be unavailable. The migration does not
add routes, change credentials, or grant access to another backend.

## Credits and migration source

Originally authored by Robert Brennan, with contributions from OpenHands.
This migration preserves their app and automation code.

Moved from [OpenHands/canvas-apps](https://github.com/OpenHands/canvas-apps/tree/b83068fdce5ec7f85c07b8aefa15d413982059d0/kanban-manager)
at `b83068fdce5ec7f85c07b8aefa15d413982059d0`, retaining the MIT [LICENSE](LICENSE).
The app vendors its original board styles and automation from
[rbren/vibe-manager](https://github.com/rbren/vibe-manager).

The separate [canvas-apps PR #21](https://github.com/OpenHands/canvas-apps/pull/21)
proposes a React/FastAPI/SQLite rewrite. It was still open when this migration
was prepared and is **not** included. Its code and any live database must not
be treated as migrated; a future port requires its own review and data plan.

## Lanes

Cards move left to right: **Pending** → **In progress** → **Needs input** →
**Finished**, plus a **Verified** lane you can toggle for the archive. Drag a
card to reprioritise within a lane. Click one to open a drawer with the full
append-only history; adding a note to a finished ticket reopens it.

In-progress cards show the worker's most recent action as it happens, so you
can see an agent working without opening its conversation.

## The manager

The control in the top right owns the manager automation for the selected
workspace, so a board can be made autonomous without leaving Canvas:

- **Start manager** (orange) — there is no manager yet, or it was stopped.
  Clicking it packs the automation's python sources (compiled into the bundle,
  `src/automation/`) plus a per-workspace `config.json` into a `tar.gz`,
  uploads it to `POST /api/automation/v1/uploads`, and creates a cron
  automation that runs `python3 main.py` once a minute. The automation id is
  recorded on the workspace.
- **manager ✓ / working / ✗** — a manager is running. The badge reports the
  last run and the manager conversation; clicking it triggers a run now.
- **Stop manager** — `PATCH {"enabled": false}`. The automation and its run
  history are kept, so starting again is a re-enable with a fresh tarball.

Two implementation notes, since neither is obvious:

- The tar archive is built in the browser and gzipped with
  `CompressionStream`. Sizes in the ustar header must be **byte** counts, not
  string lengths, or a file with any multi-byte character truncates and every
  following header lands mid-stream.
- The upload is a plain `fetch` rather than `host.agentServer.request`,
  because the host client JSON-stringifies any body that is not `FormData`,
  which would corrupt the gzip bytes. Every other call goes through the host.

Without a manager the board is still a perfectly good manual kanban: you can
create, edit, reorder and verify tickets, and open the conversation behind any
card.

## How it stores state

There is no database and no backend process. The store is a directory tree
under the Agent Server's home:

```
~/.openhands/vibe-manager/
  index.json                                  workspaces + settings
  workspaces/<id>/tickets/<tid>/ticket.json   one file per ticket
  attachments/<id>/<filename>                 uploaded files
```

The directory keeps its old name so boards created by earlier installs — and
by the manager automation, which writes the same files from the shell — are
still found.

Reads are `GET /api/file/download`, writes are `POST /api/file/upload`, both
through the host's `agentServer.request` so they are same-origin and
authenticated by Canvas. The home directory is resolved at runtime from
`GET /api/file/home` rather than assumed, so this works whatever user the
Agent Server runs as.

Two consequences worth knowing:

- **One file per ticket is what keeps writers apart.** There is no conditional
  upload to build a compare-and-swap on, so the extension, the manager
  automation and the manager's CLI would lose each other's edits if they all
  rewrote one board document. Touching separate files, they cannot. The two
  documents still shared — `index.json`, and a ticket two writers both target —
  carry a `rev`/`writer` pair that detects a lost write and re-applies it.
- **Reads bypass the HTTP cache.** The file API sends `ETag`/`Last-Modified`
  but no `Cache-Control`, so a browser may reuse a stale response for its
  heuristic freshness window. On the directory listing that assembles the
  board, that means a ticket created moments earlier never appears at all.
  Both the listing and `readJson` defeat it per request; attachment blobs are
  immutable and stay cacheable.

## Build

The checked-in `extension.js` is the built bundle; the sources are in `src/`.

```bash
npm ci
npm run check     # build + test
```

`build.mjs` bundles the ES modules with esbuild and inlines two things that
must travel with a single-file extension:

- `src/board.css`, scoping every selector under `.vibe-ext` and rewriting
  `rem` lengths onto a local `--vibe-rem`, so the board can size itself
  without restyling Canvas;
- `src/automation/*.py`, the manager automation, because "Start manager"
  uploads it from the browser and the machine running Canvas has no checkout
  of it to read.

Both are vendored from [rbren/vibe-manager](https://github.com/rbren/vibe-manager),
which is where they are maintained. The bundle's destination comes from the
manifest's `entrypoint`, so the declared and built paths cannot drift.

## Tests

`test/extension.test.js` mounts the built bundle against a linkedom DOM and a
fake host, and covers rendering, lane sorting, the submit path, the manager
start/stop control and disposal. It runs on the bundle rather than the
sources, so a broken build fails the suite.

`test/manager.test.mjs` checks the browser-built tarball with real GNU tar. It
also has two tests that talk to a running automation backend; they skip unless
a session key is available (`OH_SESSION_API_KEYS_0`, plus `VIBE_TEST_INGRESS`
if it is not on `http://127.0.0.1:8000`).

The upstream repository additionally has tests that drive the real Agent Server
file API; those need a running server and are not included here.
