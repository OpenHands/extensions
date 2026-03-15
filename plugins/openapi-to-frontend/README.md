# openapi-to-frontend

Generate a full TypeScript client, React component library, and frontend app from an OpenAPI spec.

## Overview

This plugin converts an OpenAPI specification into three layers of output:

1. **TypeScript Client** — one class per schema, one method per API endpoint
2. **React Component Library** — one component per schema, wired to the TS client
3. **React Frontend App** — a purpose-built UI inferred from the API's description
4. **Comprehensive Tests** — unit, integration, and e2e tests
5. **GitHub Actions CI/CD** — build/test on PR, deploy to GitHub Pages, publish to npm

The plugin also handles **incremental updates**: given a change to the OpenAPI spec, it produces targeted changes rather than regenerating everything.

## Quick Start

**Initial generation** — generate a complete frontend from an OpenAPI spec:

```
/openapi-to-frontend path/to/openapi.yaml
```

**Incremental update** — update existing code when the spec changes:

```
/openapi-to-frontend new-spec.json old-spec.json
```

This generates/updates:

1. **TypeScript client** — types and API class
2. **React components** — Form, Detail, List per schema
3. **Frontend app** — routing, context, pages
4. **Tests** — unit, integration, and e2e
5. **CI workflows** — GitHub Actions for build/test/deploy

## Plugin Contents

```
plugins/openapi-to-frontend/
├── README.md                           # This file
├── commands/
│   └── openapi-to-frontend.md          # Main command: generate or update
├── skills/
│   ├── generate-client/
│   │   └── SKILL.md                    # Phase 1: OpenAPI → TypeScript client
│   ├── generate-components/
│   │   └── SKILL.md                    # Phase 2: TS client → React components
│   ├── generate-frontend/
│   │   └── SKILL.md                    # Phase 3: Components → full app
│   ├── generate-tests/
│   │   └── SKILL.md                    # Phase 4: Tests
│   ├── generate-ci/
│   │   └── SKILL.md                    # Phase 5: GitHub Actions
│   └── update-from-spec/
│       └── SKILL.md                    # Incremental updates
├── agents/
│   └── spec-differ.md                  # Subagent: diffs two spec versions
├── hooks/
│   └── hooks.json                      # (reserved for future use)
├── scripts/
│   ├── parse-openapi.py                # Extract schemas, endpoints, auth from spec
│   ├── lint-generated.sh               # Run eslint + tsc on generated code
│   ├── verify-coverage.py              # Cross-reference spec against client
│   └── verify-components.py            # Cross-reference components against client
├── references/
│   ├── auth-patterns.md                # Bearer, API key, OAuth2 handling
│   ├── naming-conventions.md           # Spec→TS→React naming rules
│   └── change-taxonomy.md              # Enumerated change types + handling
└── .mcp.json                           # (reserved for future use)
```

## Features

- **Full Stack Generation** — From spec to deployable frontend in one workflow
- **Type Safety** — TypeScript throughout, with proper generics and inference
- **Auth Support** — API Key, Bearer Token, and OAuth2 flows
- **Component Library** — Reusable Form, Detail, and List components per schema
- **Tailored UIs** — Frontend design inferred from API purpose (CRUD, analytics, workflow)
- **Incremental Updates** — Surgical edits when the spec changes
- **Test Coverage** — Unit, integration, and e2e tests with mock factories
- **CI/CD Ready** — GitHub Actions for build, test, deploy, and publish

## Prerequisites

- Node.js 18+ with npm or yarn
- TypeScript 5+
- React 18+
- OpenAPI 3.0+ specification (JSON or YAML)

## Output Structure

After running all phases:

```
your-project/
├── client/
│   ├── types.ts            # TypeScript interfaces for all schemas
│   ├── api.ts              # API class with async methods
│   ├── auth.ts             # Auth configuration
│   └── index.ts            # Barrel export
├── components/
│   ├── <SchemaName>/
│   │   ├── <SchemaName>Form.tsx
│   │   ├── <SchemaName>Detail.tsx
│   │   ├── <SchemaName>List.tsx
│   │   └── index.ts
│   ├── shared/
│   │   ├── LoadingSpinner.tsx
│   │   ├── ErrorDisplay.tsx
│   │   └── Pagination.tsx
│   └── index.ts
├── app/
│   ├── App.tsx
│   ├── pages/
│   ├── context/
│   ├── hooks/
│   └── utils/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── setup/
└── .github/
    └── workflows/
        ├── ci.yml
        ├── deploy.yml
        └── publish.yml
```

## Workflow Phases

### Phase 1: Generate Client

Creates the TypeScript API client:

- **types.ts** — Interface for every schema in `components/schemas`
- **api.ts** — Class with async methods for every endpoint
- **auth.ts** — Auth handlers based on `securitySchemes`

See [skills/generate-client/SKILL.md](skills/generate-client/SKILL.md)

### Phase 2: Generate Components

Creates React components for each schema:

- **Form** — Create/edit with validation
- **Detail** — Read-only view
- **List** — Table with pagination

See [skills/generate-components/SKILL.md](skills/generate-components/SKILL.md)

### Phase 3: Generate Frontend

Creates the application shell:

- Routing based on API resources
- Auth context and guards
- UI tailored to API purpose (CRUD, analytics, workflow, search)

See [skills/generate-frontend/SKILL.md](skills/generate-frontend/SKILL.md)

### Phase 4: Generate Tests

Creates comprehensive test coverage:

- **Unit** — Client methods, type guards, component rendering
- **Integration** — Form→Client flows, auth context
- **E2E** — Smoke tests, CRUD flows, auth flows

See [skills/generate-tests/SKILL.md](skills/generate-tests/SKILL.md)

### Phase 5: Generate CI

Creates GitHub Actions workflows:

- **ci.yml** — Build + test on push/PR
- **deploy.yml** — Deploy to GitHub Pages
- **publish.yml** — Publish packages to npm

See [skills/generate-ci/SKILL.md](skills/generate-ci/SKILL.md)

## Incremental Updates

When the OpenAPI spec changes:

1. The spec-differ agent compares old and new specs
2. Changes are classified (new schema, removed endpoint, etc.)
3. Surgical edits are applied to existing files

See [skills/update-from-spec/SKILL.md](skills/update-from-spec/SKILL.md)

## Auth Patterns

The plugin supports three auth styles:

| Style | Client Handling | Frontend UI |
|-------|-----------------|-------------|
| API Key | Attached as header/query per spec | Settings page for key input |
| Bearer Token | `Authorization: Bearer <token>` | Token input or login form |
| OAuth2 | Full flow with PKCE, auto-refresh | Login/callback/logout pages |

See [references/auth-patterns.md](references/auth-patterns.md)

## Naming Conventions

| OpenAPI | TypeScript | React Component |
|---------|------------|-----------------|
| `UserProfile` schema | `interface UserProfile` | `UserProfileForm`, `UserProfileDetail` |
| `GET /users/{id}` | `getUser(id: string)` | Used in `UserDetail` |
| `POST /users` | `createUser(data)` | Used in `UserForm` |
| `snake_case` field | `camelCase` property | "Title Case" label |

See [references/naming-conventions.md](references/naming-conventions.md)

## Automated Generation with GitHub Actions

You can set up a GitHub Action that automatically generates and updates your frontend codebase from a remote OpenAPI spec. The workflow:

1. **First run**: Fetches the spec, generates the full codebase, and commits the spec as a snapshot
2. **Subsequent runs**: Fetches the new spec, compares with the snapshot, applies incremental updates

### Sample Workflow

Create `.github/workflows/sync-openapi.yml` in your repository:

```yaml
name: Sync OpenAPI Frontend

on:
  # Run on demand
  workflow_dispatch:
  # Or on a schedule (e.g., daily at midnight)
  schedule:
    - cron: '0 0 * * *'
  # Or when the workflow file itself changes
  push:
    paths:
      - '.github/workflows/sync-openapi.yml'

env:
  # ⚠️ CONFIGURE THIS: URL to your OpenAPI specification
  OPENAPI_SPEC_URL: 'https://api.example.com/openapi.json'
  # Where to store the spec snapshot
  SPEC_SNAPSHOT_PATH: '.openapi/spec.json'
  # OpenHands extensions branch (use 'main' for stable, or a feature branch)
  OPENHANDS_EXTENSIONS_BRANCH: ${{ vars.OPENHANDS_EXTENSIONS_BRANCH || 'main' }}

jobs:
  sync:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install OpenHands CLI
        run: |
          pip install uv
          uv tool install openhands --python 3.12

      - name: Install openapi-to-frontend plugin
        run: |
          # Clone the OpenHands extensions repository
          git clone --depth 1 --branch "$OPENHANDS_EXTENSIONS_BRANCH" \
            https://github.com/OpenHands/extensions.git \
            /tmp/openhands-extensions
          
          # Install the plugin to the OpenHands skills directory
          mkdir -p ~/.openhands/plugins
          cp -r /tmp/openhands-extensions/plugins/openapi-to-frontend ~/.openhands/plugins/
          
          echo "✅ Installed openapi-to-frontend plugin from branch: $OPENHANDS_EXTENSIONS_BRANCH"

      - name: Configure OpenHands
        run: |
          mkdir -p ~/.openhands
          cat > ~/.openhands/settings.json << EOF
          {
            "llm_provider": "${{ vars.LLM_PROVIDER || 'anthropic' }}",
            "llm_model": "${{ vars.LLM_MODEL || 'claude-sonnet-4-20250514' }}",
            "llm_api_key": "${{ secrets.LLM_API_KEY }}"
          }
          EOF

      - name: Create spec directory
        run: mkdir -p $(dirname $SPEC_SNAPSHOT_PATH)

      - name: Download current OpenAPI spec
        run: |
          curl -fSL "$OPENAPI_SPEC_URL" -o new-spec.json
          echo "Downloaded spec from $OPENAPI_SPEC_URL"

      - name: Check if this is initial generation or update
        id: check-mode
        run: |
          if [ -f "$SPEC_SNAPSHOT_PATH" ]; then
            echo "mode=update" >> $GITHUB_OUTPUT
            echo "📝 Existing spec found - will perform incremental update"
          else
            echo "mode=initial" >> $GITHUB_OUTPUT
            echo "🆕 No existing spec - will perform initial generation"
          fi

      - name: Check for spec changes (update mode only)
        id: check-changes
        if: steps.check-mode.outputs.mode == 'update'
        run: |
          if diff -q "$SPEC_SNAPSHOT_PATH" new-spec.json > /dev/null 2>&1; then
            echo "changed=false" >> $GITHUB_OUTPUT
            echo "✅ Spec unchanged - no update needed"
          else
            echo "changed=true" >> $GITHUB_OUTPUT
            echo "🔄 Spec changed - update required"
            # Keep the old spec for diff
            cp "$SPEC_SNAPSHOT_PATH" old-spec.json
          fi

      - name: Generate initial codebase
        if: steps.check-mode.outputs.mode == 'initial'
        run: |
          openhands --headless -t "Read ~/.openhands/plugins/openapi-to-frontend/commands/openapi-to-frontend.md and execute: /openapi-to-frontend new-spec.json"

      - name: Apply incremental updates
        if: steps.check-mode.outputs.mode == 'update' && steps.check-changes.outputs.changed == 'true'
        run: |
          openhands --headless -t "Read ~/.openhands/plugins/openapi-to-frontend/commands/openapi-to-frontend.md and execute: /openapi-to-frontend new-spec.json old-spec.json"

      - name: Update spec snapshot
        if: steps.check-mode.outputs.mode == 'initial' || steps.check-changes.outputs.changed == 'true'
        run: |
          cp new-spec.json "$SPEC_SNAPSHOT_PATH"
          echo "📸 Spec snapshot updated"

      - name: Create Pull Request
        if: steps.check-mode.outputs.mode == 'initial' || steps.check-changes.outputs.changed == 'true'
        uses: peter-evans/create-pull-request@v6
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          commit-message: |
            ${{ steps.check-mode.outputs.mode == 'initial' && 'chore: initial frontend generation from OpenAPI spec' || 'chore: update frontend from OpenAPI spec changes' }}
          title: |
            ${{ steps.check-mode.outputs.mode == 'initial' && '🆕 Initial frontend generation from OpenAPI' || '🔄 Update frontend from OpenAPI changes' }}
          body: |
            ## Summary
            
            ${{ steps.check-mode.outputs.mode == 'initial' && 'This PR contains the initial frontend codebase generated from the OpenAPI specification.' || 'This PR contains incremental updates based on changes to the OpenAPI specification.' }}
            
            **Spec URL:** `${{ env.OPENAPI_SPEC_URL }}`
            **Plugin branch:** `${{ env.OPENHANDS_EXTENSIONS_BRANCH }}`
            
            ## What's included
            
            ${{ steps.check-mode.outputs.mode == 'initial' && '- TypeScript API client (`client/`)
            - React components (`components/`)
            - Frontend application (`app/`)
            - Test suite (`tests/`)
            - CI/CD workflows (`.github/workflows/`)
            - OpenAPI spec snapshot (`.openapi/spec.json`)' || '- Updated TypeScript types and API methods
            - Updated React components
            - Updated tests
            - New OpenAPI spec snapshot' }}
            
            ## Review checklist
            
            - [ ] Generated code compiles without errors
            - [ ] Tests pass
            - [ ] UI renders correctly
            - [ ] API integration works as expected
          branch: openapi-frontend-sync
          delete-branch: true

      - name: Skip message
        if: steps.check-mode.outputs.mode == 'update' && steps.check-changes.outputs.changed == 'false'
        run: echo "✅ No changes detected in OpenAPI spec - nothing to do"
```

### Configuration

1. **Set your OpenAPI URL**: Update the `OPENAPI_SPEC_URL` environment variable to point to your API's spec
2. **Configure triggers**: Adjust the `on:` section for your needs (manual, scheduled, or event-based)
3. **Set up secrets**:
   - `LLM_API_KEY` (required): Your LLM provider API key (e.g., Anthropic, OpenAI)
   - `GITHUB_TOKEN`: Ensure it has write permissions for contents and pull-requests
4. **Optional variables** (repository variables, not secrets):
   - `LLM_PROVIDER`: Your LLM provider (defaults to `anthropic`)
   - `LLM_MODEL`: Override the default model (defaults to `claude-sonnet-4-20250514`)
   - `OPENHANDS_EXTENSIONS_BRANCH`: Branch of OpenHands/extensions to use (defaults to `main`)

### How the Snapshot Works

The workflow maintains a snapshot of the OpenAPI spec at `.openapi/spec.json`:

```
your-repo/
├── .openapi/
│   └── spec.json          # Committed snapshot of the last processed spec
├── client/
├── components/
├── app/
└── ...
```

- **Initial run**: No snapshot exists, so full generation runs and the spec is committed
- **Subsequent runs**: The snapshot is compared with the freshly downloaded spec
  - If unchanged: workflow exits early
  - If changed: incremental update runs, using `old-spec.json` (the snapshot) and `new-spec.json` (the download)

This ensures the agent always knows the exact state of the codebase relative to the spec it was generated from.

### Alternative: Local Spec File

If your OpenAPI spec is checked into the repository instead of fetched from a URL:

```yaml
env:
  # Path to spec in your repo
  OPENAPI_SPEC_PATH: 'api/openapi.yaml'
  SPEC_SNAPSHOT_PATH: '.openapi/last-processed-spec.yaml'

# ... in steps:
- name: Check for spec changes
  run: |
    if [ -f "$SPEC_SNAPSHOT_PATH" ]; then
      if diff -q "$OPENAPI_SPEC_PATH" "$SPEC_SNAPSHOT_PATH" > /dev/null; then
        echo "No changes"
      else
        cp "$SPEC_SNAPSHOT_PATH" old-spec.yaml
        cp "$OPENAPI_SPEC_PATH" new-spec.yaml
        # ... trigger update
      fi
    else
      cp "$OPENAPI_SPEC_PATH" new-spec.yaml
      # ... trigger initial generation
    fi
```

## Scripts

### parse-openapi.py

```bash
python scripts/parse-openapi.py openapi.yaml > spec-summary.json
```

Outputs structured JSON with schemas, endpoints, and auth schemes.

### lint-generated.sh

```bash
./scripts/lint-generated.sh
```

Runs eslint and tsc on generated code. Returns non-zero on errors.

### verify-coverage.py

```bash
python scripts/verify-coverage.py openapi.yaml client/
```

Ensures every schema and endpoint has corresponding TypeScript code.

### verify-components.py

```bash
python scripts/verify-components.py client/ components/
```

Ensures every type has corresponding React components.

## Contributing

See the main [extensions repository](https://github.com/OpenHands/extensions) for contribution guidelines.

## License

This plugin is part of the OpenHands extensions repository. See [LICENSE](../../LICENSE) for details.
