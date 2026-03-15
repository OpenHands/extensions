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

Provide an OpenAPI spec (JSON or YAML) and run phases sequentially:

```
/generate-all path/to/openapi.yaml
```

Or run individual phases:

1. **Generate client**: Creates TypeScript types and API class
2. **Generate components**: Creates React components for each schema
3. **Generate frontend**: Creates a full application shell
4. **Generate tests**: Creates unit, integration, and e2e tests
5. **Generate CI**: Creates GitHub Actions workflows

## Plugin Contents

```
plugins/openapi-to-frontend/
├── README.md                           # This file
├── commands/
│   └── generate-all.md                 # Slash command: run all phases
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
