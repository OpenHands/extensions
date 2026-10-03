# Onboarding scanner reproduction and execution evidence

Base: OpenHands/extensions main `62f34e3` (v0.27.0).

## Before

A repository containing only these installed-package files has no authored
readiness evidence:

```text
node_modules/pkg/test_dependency.py
node_modules/.eslintrc.json
node_modules/pkg/AGENTS.md
node_modules/pkg/SECURITY.md
node_modules/pkg/pull_request_template.md
.venv/lib/test_dependency.py
.venv/Dockerfile
```

Invoked the five existing `bash scripts/scan_*.sh <fixture>` entrypoints on
unmodified main. They reported the dependency AGENTS.md, linter config,
SECURITY.md, PR template and virtualenv Dockerfile, plus `2 test files found`.
The build/policy/workflow scanners also returned 1 solely because their final
optional signal was absent. The captured stdout/exit codes are in
`onboarding-before.json`.

Ran the scanner regressions before the implementation: 9 failures (including
five scanner subcases), 6 passes. Dependency-only, nested dependency, snapshot/
benchmark and named-directory test-count cases all reproduced failures.

## Released-package end-to-end execution

```bash
PYTHONDONTWRITEBYTECODE=1 uv run --with openhands-sdk==1.49.0 python .pr/validate_onboarding.py
```

Actually ran this on Windows 11 / Git Bash / Python 3.12.11 and Ubuntu 24.04
(WSL2) / Bash / Python 3.12.3. SDK 1.49.0 was published on 2026-09-16; this
check uses its released wheel, not the SDK source tree.

The script copies the plugin into a clean temporary installation and loads it
with the SDK. It observes five skills, selects agent-readiness-report, checks
five positive and five negative keyword-trigger samples, then runs the installed
scanners on dependency-only and authored-monorepo fixtures and the real
extensions checkout. Each environment ran 15 successful scanner invocations.

Observed: no excluded dependency evidence; `0 test files found` for the
dependency-only fixture; `1 test files found` for the authored fixture; authored
instructions/policy/template/Dockerfile remain visible. A missing target returns
1 with `Cannot access`. Fixture file digests remain unchanged and the temporary
plugin installation is removed. Exact output is in `onboarding-e2e-linux.json`
and `onboarding-e2e-windows.json`.

These checks exercise deterministic plugin helpers and SDK keyword matching.
They do not measure model-selected skill activation or freely generated
readiness-report quality. No LLM key or service account is used.

## Automated validation

- Clean Linux checkout: `uv run pytest -q tests/ plugins/onboarding/tests/ plugins/runtime-api-configs/tests/`
  -> 1157 passed, 23 skipped, 5 subtests passed. Root tests ran with SDK 1.51.0.
- Final scanner checks after the missing-helper guard: 10 passed, 5 subtests
  passed on Linux and Windows Git Bash.
- `node --test tests/*.test.mjs` -> 1 passed.
- `npm run build` -> skills/integrations/automations builds pass; generated
  catalog files have no diff in the clean Linux checkout.
- `python scripts/sync_extensions.py --check` -> success, with the existing
  nonblocking unlisted issue-duplicate-checker warning.
- `python scripts/check_plugin_resources.py` -> success after clearing test
  bytecode in the temporary Linux checkout.
- Authenticated `python scripts/sync_openhands_sdk_skill.py --check` -> up to date.
- `shellcheck --severity=warning --external-sources --source-path=plugins/onboarding/skills/agent-readiness-report/scripts plugins/onboarding/skills/agent-readiness-report/scripts/*.sh`
  -> success.
- Claude CLI manifest validation -> all 12 plugin manifests pass. Existing
  symlink warnings on other plugins remain; onboarding has no warning.
- `git diff --check` -> success.

A first run against the Windows CRLF checkout produced eight unrelated
generated-bundle comparison failures. A fresh Linux checkout passed all tests
without changing those bundles. An unauthenticated SDK freshness check hit
fallback/network behavior; the authenticated check passed without source changes.

## Security and scope

One existing plugin, no new catalog entries or dependencies. The helpers read
only the user-selected repository and do not execute its code, use credentials,
make network requests, write project files or change host configuration. Roots
and arguments are quoted. No GitHub-event workflow or new authorization rule is
introduced. Keyword activation conveys no additional authority.

Depth limits and manual quality assessment remain. Exclusion is limited to
the four documented directory names; this is not a general vendor classifier.
macOS and model-behavior A/B evaluation were not performed. Related issue #27
contains broader dogfooding/product decisions and is not closed by this fix.

No screenshot: this contribution produces terminal evidence, not a visual UI.
