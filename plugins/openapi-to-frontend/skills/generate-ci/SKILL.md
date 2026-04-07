---
name: openapi-generate-ci
description: Generate GitHub Actions workflows for CI/CD. Includes build/test on PR, deploy to GitHub Pages, and publish to npm.
license: MIT
compatibility: Requires GitHub Actions, optionally npm for publishing
triggers:
  - openapi ci
  - generate ci
  - github actions
  - ci cd
  - deploy workflow
---

Generate GitHub Actions workflows for the generated codebase.

## Overview

This skill produces three workflow files:

- `.github/workflows/ci.yml` — Build + test on push/PR
- `.github/workflows/deploy.yml` — Deploy frontend to GitHub Pages
- `.github/workflows/publish.yml` — Publish packages to npm

## Prerequisites

- Generated codebase (client, components, frontend, tests)
- GitHub repository
- Optional: npm account for publishing

## Workflow

### Step 1: Detect Project Configuration

Analyze `package.json` to determine:

- Node.js version (from `engines.node` or default to LTS)
- Package manager (npm, yarn, pnpm)
- Test commands available
- Build commands
- Scope for npm packages (from name or repo)

### Step 2: Generate ci.yml

**.github/workflows/ci.yml:**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run ESLint
        run: npm run lint

      - name: Type check
        run: npm run typecheck

  test-unit:
    name: Unit Tests
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run unit tests
        run: npm run test:unit

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage/lcov.info
          fail_ci_if_error: false

  test-integration:
    name: Integration Tests
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run integration tests
        run: npm run test:integration

  test-e2e:
    name: E2E Tests
    runs-on: ubuntu-latest
    # E2E Backend Strategy: Detected method documented here
    # Using: Docker Compose / npm start / Prism mock / E2E_BASE_URL
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps chromium

      # Option 1: Docker Compose backend
      - name: Start backend (Docker)
        run: |
          docker compose up -d
          # Wait for backend to be ready
          timeout 60 bash -c 'until curl -s http://localhost:3000/health; do sleep 2; done'
        if: hashFiles('docker-compose.yml') != ''

      # Option 2: Start mock server with Prism
      - name: Start mock server
        run: |
          npm install -g @stoplight/prism-cli
          prism mock openapi.yaml --port 3000 &
          sleep 5
        if: hashFiles('docker-compose.yml') == '' && hashFiles('openapi.yaml') != ''

      - name: Build frontend
        run: npm run build

      - name: Run E2E tests
        run: npm run test:e2e
        env:
          E2E_BASE_URL: ${{ secrets.E2E_BASE_URL || 'http://localhost:3000' }}

      - name: Upload test artifacts
        uses: actions/upload-artifact@v4
        if: failure()
        with:
          name: playwright-report
          path: playwright-report/
          retention-days: 7

      - name: Stop backend
        run: docker compose down
        if: always() && hashFiles('docker-compose.yml') != ''

  build:
    name: Build
    runs-on: ubuntu-latest
    needs: [lint, test-unit, test-integration]
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
          retention-days: 1
```

### Step 3: Generate deploy.yml

**.github/workflows/deploy.yml:**

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  build:
    name: Build
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build
        env:
          # Set base path for GitHub Pages
          VITE_BASE_URL: /${{ github.event.repository.name }}/

      - name: Setup Pages
        uses: actions/configure-pages@v4

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: dist/

  deploy:
    name: Deploy
    runs-on: ubuntu-latest
    needs: build
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

### Step 4: Generate publish.yml

**.github/workflows/publish.yml:**

```yaml
name: Publish to npm

on:
  release:
    types: [published]
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to publish (e.g., 1.0.0)'
        required: true
        type: string

jobs:
  publish:
    name: Publish Packages
    runs-on: ubuntu-latest
    # Only run if NPM_TOKEN is available
    if: ${{ secrets.NPM_TOKEN != '' }}
    permissions:
      contents: read
      id-token: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          registry-url: 'https://registry.npmjs.org'

      - name: Install dependencies
        run: npm ci

      - name: Run tests
        run: |
          npm run test:unit
          npm run test:integration

      - name: Build packages
        run: npm run build

      # Publish TypeScript client
      - name: Publish client package
        run: |
          cd client
          npm publish --access public --provenance
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

      # Publish React components
      - name: Publish components package
        run: |
          cd components
          npm publish --access public --provenance
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}

  skip-publish:
    name: Skip Publish (no NPM_TOKEN)
    runs-on: ubuntu-latest
    if: ${{ secrets.NPM_TOKEN == '' }}
    steps:
      - name: Notice
        run: |
          echo "::notice::Skipping npm publish - NPM_TOKEN secret not configured"
          echo "To enable publishing, add NPM_TOKEN to repository secrets"
```

### Step 5: Generate Dependabot Configuration

**.github/dependabot.yml:**

```yaml
version: 2
updates:
  - package-ecosystem: npm
    directory: /
    schedule:
      interval: weekly
    groups:
      dev-dependencies:
        patterns:
          - '*'
        exclude-patterns:
          - 'react*'
          - 'typescript'
      react:
        patterns:
          - 'react*'
          - '@types/react*'
    ignore:
      - dependency-name: '*'
        update-types: ['version-update:semver-major']

  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
    groups:
      actions:
        patterns:
          - '*'
```

### Step 6: Generate Branch Protection Suggestion

Output a reminder for the user:

```
## Recommended Branch Protection Rules

For the `main` branch, consider enabling:

1. **Require status checks to pass before merging:**
   - lint
   - test-unit
   - test-integration
   - build

2. **Require branches to be up to date before merging**

3. **Require pull request reviews:**
   - At least 1 approval

4. **Do not allow bypassing the above settings**

You can configure these at:
Settings → Branches → Add branch protection rule
```

## Secrets Configuration

| Secret | Required By | Purpose |
|--------|-------------|---------|
| `NPM_TOKEN` | publish.yml | npm authentication (optional) |
| `E2E_BASE_URL` | ci.yml | Backend URL for e2e (optional fallback) |
| `CODECOV_TOKEN` | ci.yml | Coverage upload (optional) |

## Package.json Scripts

Ensure these scripts exist:

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext .ts,.tsx",
    "typecheck": "tsc --noEmit",
    "test": "vitest",
    "test:unit": "vitest run tests/unit",
    "test:integration": "vitest run tests/integration",
    "test:e2e": "playwright test"
  }
}
```

## E2E Backend Strategy Selection

The ci.yml workflow uses this priority order for starting the backend:

1. **Docker Compose** — If `docker-compose.yml` exists, start services and wait for health endpoint
2. **Mock Server** — If only OpenAPI spec exists, use Prism to mock the API
3. **External URL** — Fall back to `E2E_BASE_URL` secret

The workflow includes comments documenting which strategy was selected.

## Vite Configuration for GitHub Pages

**vite.config.ts:**

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // Use VITE_BASE_URL for GitHub Pages deployment
  base: process.env.VITE_BASE_URL || '/',
});
```

## Output Files

| File | Purpose |
|------|---------|
| `.github/workflows/ci.yml` | Build + test on push/PR |
| `.github/workflows/deploy.yml` | Deploy to GitHub Pages |
| `.github/workflows/publish.yml` | Publish to npm on release |
| `.github/dependabot.yml` | Automated dependency updates |

## Verification

After generating, verify:

1. Push to a branch and check that CI runs
2. Create a PR and verify all checks pass
3. Merge to main and verify GitHub Pages deploy
4. Create a release to test npm publish (if configured)

## Next Steps

All phases complete! The generated codebase now includes:

- TypeScript API client
- React component library
- Frontend application
- Comprehensive tests
- CI/CD pipelines

For incremental updates when the spec changes, see:
[../update-from-spec/SKILL.md](../update-from-spec/SKILL.md)
