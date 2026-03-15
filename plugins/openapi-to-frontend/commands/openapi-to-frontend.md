# /openapi-to-frontend

Generate or update a frontend codebase from an OpenAPI specification.

## Usage

```
/openapi-to-frontend <new-spec> [old-spec]
```

## Arguments

| Argument | Description |
|----------|-------------|
| `new-spec` | Path to the current/new OpenAPI specification (JSON or YAML) |
| `old-spec` | (Optional) Path to the previous OpenAPI spec for incremental updates |

## Behavior

**Initial generation** (no `old-spec` provided):
```
/openapi-to-frontend openapi.json
```
Generates a complete frontend codebase from scratch.

**Incremental update** (both specs provided):
```
/openapi-to-frontend new-spec.json old-spec.json
```
Compares the specs and applies surgical updates to existing code.

---

## What This Command Does

### Initial Generation Mode

When only `new-spec` is provided, run all generation phases:

1. **Read the spec** at the provided path
2. **Generate TypeScript client** in `client/`:
   - `types.ts` — interfaces for all schemas
   - `api.ts` — API class with typed methods  
   - `auth.ts` — auth handlers based on securitySchemes
   - `index.ts` — barrel export
3. **Generate React components** in `components/`:
   - `<Schema>/` directory per schema with Form, Detail, List components
   - `shared/` — LoadingSpinner, ErrorDisplay, Pagination
4. **Generate React frontend** in `app/`:
   - `App.tsx` with routing
   - `pages/` — one page per resource
   - `context/` — API client and auth providers
   - `hooks/` — useResource, usePagination
   - `utils/` — localStorage helpers
5. **Generate tests** in `tests/`:
   - `setup/` — factories, type guards, config
   - `unit/` — client and component tests
   - `integration/` — flow tests
   - `e2e/` — Playwright tests
6. **Generate CI workflows** in `.github/workflows/`:
   - `ci.yml` — build and test on PR
   - `deploy.yml` — deploy to GitHub Pages
   - `publish.yml` — publish to npm
7. **Verify** the generated code compiles correctly

### Incremental Update Mode

When both `new-spec` and `old-spec` are provided:

1. **Compare the specs** to identify changes:
   - Schemas added/removed/modified
   - Endpoints added/removed/modified
   - Fields added/removed/type changed
   - Auth schemes changed
2. **Apply surgical updates** to existing code:
   - Add new interfaces for new schemas
   - Update existing interfaces for changed fields
   - Add/remove API methods for endpoint changes
   - Update components to reflect schema changes
   - Update tests and factories
3. **Do NOT regenerate from scratch** — preserve user customizations
4. **Verify** the updated code compiles and tests pass

---

## Reference Skills

This command orchestrates these skills (read them for detailed implementation guidance):

| Phase | Skill | Description |
|-------|-------|-------------|
| Client | `skills/generate-client/SKILL.md` | TypeScript types and API class |
| Components | `skills/generate-components/SKILL.md` | React Form/Detail/List components |
| Frontend | `skills/generate-frontend/SKILL.md` | App shell, routing, context |
| Tests | `skills/generate-tests/SKILL.md` | Unit, integration, e2e tests |
| CI | `skills/generate-ci/SKILL.md` | GitHub Actions workflows |
| Updates | `skills/update-from-spec/SKILL.md` | Incremental change application |
| Diffing | `agents/spec-differ.md` | Spec comparison logic |

## Reference Documents

| Topic | Reference |
|-------|-----------|
| Auth patterns | `references/auth-patterns.md` |
| Naming rules | `references/naming-conventions.md` |
| Change types | `references/change-taxonomy.md` |

---

## Output Structure

```
./
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

## Examples

### Generate from a local spec

```
/openapi-to-frontend ./api/openapi.yaml
```

### Update after spec changes

```
/openapi-to-frontend ./new-spec.json ./old-spec.json
```

### In CI/CD (GitHub Actions)

```yaml
- name: Generate/update frontend
  run: openhands --headless -t "/openapi-to-frontend new-spec.json old-spec.json"
```
