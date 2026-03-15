# /generate-all

Run all generation phases end-to-end from an OpenAPI specification.

## Usage

```
/generate-all <spec-file> [options]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `spec-file` | Path to OpenAPI specification (JSON or YAML) |

## Options

| Option | Description |
|--------|-------------|
| `--output-dir <dir>` | Output directory (default: current directory) |
| `--skip-tests` | Skip test generation |
| `--skip-ci` | Skip CI/CD workflow generation |
| `--client-only` | Generate only the TypeScript client |
| `--dry-run` | Show what would be generated without writing files |

## Examples

### Full generation

```
/generate-all ./openapi.yaml
```

This will:
1. Parse the OpenAPI spec
2. Generate TypeScript client in `client/`
3. Generate React components in `components/`
4. Generate React frontend in `app/`
5. Generate tests in `tests/`
6. Generate GitHub Actions in `.github/workflows/`

### Client only

```
/generate-all ./api-spec.json --client-only
```

### Custom output directory

```
/generate-all ./openapi.yaml --output-dir ./packages/generated
```

### Skip CI

```
/generate-all ./openapi.yaml --skip-ci
```

## Workflow

The command runs these phases in sequence:

### Phase 1: Parse Spec

```bash
python scripts/parse-openapi.py <spec-file> > .generated/spec-summary.json
```

Extracts schemas, endpoints, and auth schemes into a normalized format.

### Phase 2: Generate Client

Uses `skills/generate-client/SKILL.md`:

- Creates `client/types.ts` with TypeScript interfaces
- Creates `client/api.ts` with API class and methods
- Creates `client/auth.ts` with auth handlers
- Creates `client/index.ts` barrel export

### Phase 3: Generate Components

Uses `skills/generate-components/SKILL.md`:

- Creates `components/<Schema>/` directories
- Creates Form, Detail, List components per schema
- Creates `components/shared/` utilities
- Creates barrel exports

### Phase 4: Generate Frontend

Uses `skills/generate-frontend/SKILL.md`:

- Infers app type from API structure
- Creates `app/App.tsx` with routing
- Creates `app/pages/` per resource
- Creates `app/context/` for API and auth
- Creates `app/hooks/` for data fetching

### Phase 5: Generate Tests

Uses `skills/generate-tests/SKILL.md`:

- Creates `tests/setup/` with config and factories
- Creates `tests/unit/` for client and components
- Creates `tests/integration/` for flows
- Creates `tests/e2e/` for Playwright

### Phase 6: Generate CI

Uses `skills/generate-ci/SKILL.md`:

- Creates `.github/workflows/ci.yml`
- Creates `.github/workflows/deploy.yml`
- Creates `.github/workflows/publish.yml`

## Verification

After generation, the command runs:

```bash
# Lint check
./scripts/lint-generated.sh

# Coverage verification
python scripts/verify-coverage.py <spec-file> client/
python scripts/verify-components.py client/ components/
```

## Output Structure

```
<output-dir>/
├── client/
│   ├── types.ts
│   ├── api.ts
│   ├── auth.ts
│   └── index.ts
├── components/
│   ├── <Schema>/
│   │   ├── <Schema>Form.tsx
│   │   ├── <Schema>Detail.tsx
│   │   ├── <Schema>List.tsx
│   │   └── index.ts
│   ├── shared/
│   └── index.ts
├── app/
│   ├── App.tsx
│   ├── Layout.tsx
│   ├── main.tsx
│   ├── pages/
│   ├── context/
│   ├── hooks/
│   └── utils/
├── tests/
│   ├── setup/
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── .github/
    └── workflows/
        ├── ci.yml
        ├── deploy.yml
        └── publish.yml
```

## Interactive Mode

When the API purpose is ambiguous, the command asks for confirmation:

> "Based on the API, this appears to be a **user management system**. I'll generate:
> - Dashboard with user list
> - User detail and edit pages
> - Role management section
> - OAuth2 login flow
>
> Does this match your expectations? [Y/n]"

## Incremental Updates

For updating existing generated code when the spec changes, use:

```
/update-from-spec <old-spec> <new-spec>
```

See `skills/update-from-spec/SKILL.md` for details.
