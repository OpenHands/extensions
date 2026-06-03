# Agent Readiness Criteria

Features that make a codebase ready for AI-assisted development, organized into
five pillars.  Derived from cluster analysis of 123 repositories, but written to
be tool-agnostic.  Every feature answers one question: *if this is missing, what
goes wrong for the agent?*

---

## Pillar 1 · Agent Instructions

How the repo tells AI agents what to do, what to avoid, and how the codebase
works.  This is the highest-signal pillar — it's the difference between an agent
that understands the project and one that's guessing.

| # | Feature | What to look for | Evidence |
|---|---------|------------------|----------|
| 1 | **Agent instruction file** | A dedicated file telling agents how to work in this repo — conventions, banned patterns, common commands | `AGENTS.md`, `CLAUDE.md`, `COPILOT.md`, `CONVENTIONS.md` at root |
| 2 | **AI IDE configuration** | Settings or rules for AI-powered editors/IDEs | `.cursor/rules/`, `.cursorrules`, `.github/copilot-instructions.md`, `.github/instructions/`, `.claude/settings.json` |
| 3 | **Multi-model support** | Instructions that work across different AI models/tools, not locked to one vendor | 2+ distinct agent config types from features 1–2 present in same repo |
| 4 | **Agent skills or capabilities** | Packaged, reusable abilities the agent can invoke | `.claude/skills/`, `.factory/skills/`, `skill.md` files, tool definition files |
| 5 | **Tool server configuration** | Config for agent tool protocols (lets agents use external tools) | `.mcp.json`, `mcp.config.js`, tool server manifests |
| 6 | **Agent prompt library** | Pre-built prompts for common tasks in this repo | `.github/prompts/`, `prompts/` directory, prompt template files |
| 7 | **Component-level agent guidance** | Different parts of the codebase have their own agent instructions | `AGENTS.md` or instruction files in subdirectories (e.g. `frontend/AGENTS.md`, `api/CLAUDE.md`) |
| 8 | **README with build/run/test** | README includes the commands to build, run, and test the project | `README.md` containing code blocks with build/install/test commands |
| 9 | **Contributing guide** | How to contribute — code style, PR process, commit conventions | `CONTRIBUTING.md`, `docs/contributing.md`, contributing section in README |
| 10 | **Architecture documentation** | High-level overview of how the system is structured and why | `ARCHITECTURE.md`, `docs/architecture/`, Mermaid/PlantUML diagrams, `doc/design/` |
| 11 | **API documentation** | Reference docs for the project's interfaces | `openapi.yaml`, generated HTML docs, `doc.go` files, Swagger UI, `api-docs/` |
| 12 | **Inline code documentation** | Doc comments, docstrings — agents read these to understand intent | JSDoc `/** */` blocks, Python docstrings, GoDoc comments, RDoc `#` blocks, Rust `///` |
| 13 | **Runnable examples** | Working example code the agent can study and imitate | `examples/` directory, `_examples/`, example apps with their own READMEs |
| 14 | **Changelog** | History of what changed and how entries should be written | `CHANGELOG.md`, `CHANGES.md`, `HISTORY.md`, release notes in GitHub Releases |
| 15 | **Environment variable documentation** | Template or docs for required env vars | `.env.example`, `.env.template`, env var table in README or docs |
| 16 | **Documentation site or directory** | Organized docs beyond the README | `docs/` directory, Docusaurus/Sphinx/MkDocs/VitePress config, published doc site |
| 17 | **Decision records** | Documented reasoning behind past architectural choices | `doc/adr/`, `decisions/`, `rfcs/`, numbered markdown decision files |
| 18 | **Module-level READMEs** | Individual packages/modules have their own READMEs | `packages/*/README.md`, `libs/*/README.md`, per-crate/per-module READMEs |

---

## Pillar 2 · Feedback Loops

How quickly and clearly the agent learns whether its changes are correct.  Fast,
clear feedback is the difference between an agent that converges on a solution
and one that spirals.

| # | Feature | What to look for | Evidence |
|---|---------|------------------|----------|
| 19 | **Linter** | Static analysis that catches bugs and style issues | `.eslintrc.*`, `ruff.toml`, `.golangci.yml`, `clippy.toml`, `pylintrc`, lint config in `pyproject.toml` |
| 20 | **Formatter** | Auto-formatter that enforces consistent style | `.prettierrc`, `rustfmt.toml`, `[tool.black]` in pyproject.toml, `gofmt`/`goimports` in CI |
| 21 | **Type checking** | Static type system or type checker | `tsconfig.json` with `strict`, `mypy.ini`, `[tool.mypy]`, `py.typed` marker, Go (inherent) |
| 22 | **Pre-commit hooks** | Checks that run before commit — catches issues before CI | `.pre-commit-config.yaml`, `.husky/`, `lefthook.yml`, `lint-staged` config |
| 23 | **Unit tests** | Tests for individual components | `*_test.go`, `*_test.py`, `*.spec.ts`, `test/`, `__tests__/`, test runner config |
| 24 | **Integration tests** | Tests that verify components work together | `test/integration/`, `tests/e2e/`, API test suites, test files with service dependencies |
| 25 | **End-to-end tests** | Full system/browser tests | Playwright config, Cypress config, Selenium tests, `e2e/` directory |
| 26 | **Test coverage measurement** | Coverage tracking so the agent knows if new code is tested | `.codecov.yml`, `coverageThreshold` in jest config, `--cov` in pytest, `cover` profile in Go |
| 27 | **CI pipeline** | Automated checks on every push or PR | `.github/workflows/ci.yml`, `.circleci/config.yml`, `.gitlab-ci.yml`, `Jenkinsfile` |
| 28 | **Fast CI feedback** | CI completes quickly enough for agent iteration | CI workflow with documented expected duration, parallel jobs, test splitting |
| 29 | **Test run documentation** | Agent knows exactly how to run which tests | Test commands in README, AGENTS.md, CONTRIBUTING.md, or Makefile help target |
| 30 | **Config/schema validation** | YAML, JSON, config files validated automatically | `yamllint` config, JSON schema `$schema` refs, `actionlint` in CI, `taplo` for TOML |
| 31 | **Snapshot or golden-file tests** | Tests that detect unexpected output changes | `__snapshots__/` directories, `.snap` files, `testdata/` golden files, VCR cassettes |
| 32 | **Benchmark suite** | Performance tests the agent can run to check for regressions | `bench/`, `benchmarks/`, `*_bench_test.go`, pytest-benchmark, Criterion.rs |
| 33 | **Warnings-as-errors** | Compiler/runtime warnings treated as failures | `-Werror`, `warningsAsErrors` in build config, `filterwarnings = error` in pytest |
| 34 | **Spell/typo checking** | Automated spelling checks in CI or hooks | `.cspell.json`, `codespell` in pre-commit, `typos.toml`, spell check CI step |

---

## Pillar 3 · Workflows & Automation

The processes that support agent-driven development — how work is structured,
tracked, and shipped.

| # | Feature | What to look for | Evidence |
|---|---------|------------------|----------|
| 35 | **Issue templates** | Structured templates for bug reports, feature requests | `.github/ISSUE_TEMPLATE/` with `bug_report.md`, `feature_request.md`, `config.yml` |
| 36 | **PR template** | Template that guides PR descriptions | `.github/pull_request_template.md`, PR template with checklist items |
| 37 | **Dependency update automation** | Automated PRs for dependency updates | `.github/dependabot.yml`, `renovate.json`, `.renovaterc`, Renovate preset configs |
| 38 | **Release automation** | Automated release pipeline (build, tag, publish) | Release workflow in CI, `semantic-release` config, GoReleaser config, `release-please` |
| 39 | **Branch protection** | Protected main branch with required checks | Branch protection rules (inferred from merge queue config, required status checks in CI) |
| 40 | **Merge automation** | Merge queue, auto-merge, or merge bot | `merge_group` trigger in CI, Mergify config, auto-merge labels, `gh pr merge --auto` |
| 41 | **Task runner** | Single entry point for common commands | `Makefile`, `Justfile`, `Taskfile.yml`, `package.json` scripts section, `Rakefile` |
| 42 | **Structured change tracking** | Changesets, conventional commits, or similar discipline | `.changeset/` directory, `commitlint` config, conventional commit enforcement in CI |
| 43 | **CI concurrency control** | Cancel-in-progress, concurrency groups to avoid CI pile-up | `concurrency:` blocks in GitHub Actions, `cancel-in-progress: true` |
| 44 | **Automated release notes** | Changelog/release notes generated from commits or PRs | `release-please` config, `auto-changelog`, `git-cliff`, `conventional-changelog` |
| 45 | **Stale issue/PR management** | Automation to close or label stale items | `.github/workflows/stale.yml`, `stale` bot config, issue lifecycle labels |
| 46 | **Label automation** | Automatic PR/issue labeling based on paths or content | `.github/labeler.yml`, label-sync config, auto-label workflows |
| 47 | **Multi-platform CI** | CI matrix covering multiple OS, arch, or runtime versions | `matrix:` in CI with `os: [ubuntu, macos, windows]` or multiple language versions |
| 48 | **Deployment automation** | Automated deployment pipeline | Deploy workflow triggered on merge/tag, staging + production environments in CI |
| 49 | **Automated code review checks** | Bot-driven review checks beyond CI | Danger.js config, review bot config, required review assignments, CODEOWNERS + required reviews |

---

## Pillar 4 · Policy & Governance

Rules, ownership, and constraints the agent must know about and respect.

| # | Feature | What to look for | Evidence |
|---|---------|------------------|----------|
| 50 | **Comprehensive .gitignore** | Covers secrets, build artifacts, IDE files, agent artifacts | `.gitignore` with entries for `.env`, `node_modules/`, build dirs, `.cursor/`, `.claude/` |
| 51 | **License** | Clear license at root | `LICENSE`, `MIT-LICENSE`, `COPYING`, `LICENSE.md` |
| 52 | **Code ownership** | File/directory ownership mapping | `CODEOWNERS`, `.github/CODEOWNERS`, docs describing area owners or maintainer teams |
| 53 | **Security policy** | How to report vulnerabilities | `SECURITY.md`, `.github/security.md`, security reporting instructions |
| 54 | **Code of conduct** | Community standards | `CODE_OF_CONDUCT.md`, conduct link in contributing guide |
| 55 | **AI usage policy** | Documented guidelines for AI/agent contributions | AI policy in AGENTS.md, CONTRIBUTING.md, or standalone doc; agent boundary definitions |
| 56 | **Secrets management** | Secrets handled via environment/vault, not hardcoded | References to `${{ secrets.* }}` in CI, vault config, `.env.example` without values, `git-secrets` |
| 57 | **Security scanning** | Automated vulnerability scanning in CI | `.github/workflows/codeql.yml`, Snyk config, `gosec` in CI, Trivy, Dependabot security alerts |
| 58 | **Git attributes** | Line endings, diff drivers, LFS, linguist overrides | `.gitattributes` with `text=auto`, `linguist-generated`, LFS tracking patterns |
| 59 | **Contributor agreement** | DCO sign-off or CLA process | DCO bot config, `Signed-off-by` requirement in contributing guide, CLA-assistant config |
| 60 | **Governance model** | Documented maintainer roles, decision-making process | `GOVERNANCE.md`, `MAINTAINERS.md`, governance section in docs, team/role descriptions |
| 61 | **CI workflow validation** | CI config itself is linted/validated | `actionlint` step in CI, `circleci config validate`, CI config schema validation |
| 62 | **Environment separation** | Distinct configs for dev/test/prod | `.env.test`, `.env.production`, environment-specific config directories, config per deploy target |

---

## Pillar 5 · Build & Dev Environment

Can the agent actually build, run, and iterate on the project?  Reproducibility
and speed matter — an agent that can't build the project can't do anything.

| # | Feature | What to look for | Evidence |
|---|---------|------------------|----------|
| 63 | **Dependency lockfile** | Pinned dependency versions for reproducible installs | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `uv.lock`, `Cargo.lock`, `go.sum`, `Gemfile.lock`, `poetry.lock` |
| 64 | **Single-command build** | One documented command to build the entire project | `make build`, `npm run build`, `cargo build` documented in README or agent file |
| 65 | **Single-command dev setup** | One command to bootstrap a working dev environment | `bin/setup`, `make dev`, `scripts/bootstrap.sh`, `just setup` |
| 66 | **Dev container** | Containerized dev environment definition | `.devcontainer/devcontainer.json`, `devcontainer.json` at root |
| 67 | **Containerized services** | Docker-based local development stack | `Dockerfile`, `docker-compose.yml`, `compose.yaml` with dev services |
| 68 | **Reproducible environment** | Declarative, reproducible dev environment | `flake.nix`, `shell.nix`, `devbox.json`, hermetic build definitions |
| 69 | **Tool version pinning** | Runtime/tool versions pinned to a file | `.tool-versions`, `mise.toml`, `.node-version`, `.python-version`, `.ruby-version`, `rust-toolchain.toml` |
| 70 | **Monorepo orchestration** | Tooling for multi-package repositories | Workspace config in `package.json`, `pnpm-workspace.yaml`, Cargo workspace, Go multi-module, Nx/Turborepo/Bazel config |
| 71 | **Build caching** | Caching for faster rebuilds | CI cache steps (`actions/cache`), Turborepo remote cache, ccache/sccache config, layer caching in Docker |
| 72 | **Cross-platform support** | Builds on multiple OS/arch | CI matrix with multiple OS entries, cross-compilation configs, multi-arch Docker builds |
| 73 | **Cloud dev environment** | Cloud-based workspace configuration | `.devcontainer/` with Codespaces features, `.gitpod.yml`, cloud workspace config |
| 74 | **Package manager configuration** | Custom registry, auth, resolution settings | `.npmrc`, `pip.conf`, `.cargo/config.toml`, registry overrides, resolution overrides |

---

## Summary

| Pillar | Features | What it answers |
|--------|----------|-----------------|
| Agent Instructions | 18 | Does the agent know what to do? |
| Feedback Loops | 16 | Does the agent know if it's right? |
| Workflows & Automation | 15 | Does the process support agent work? |
| Policy & Governance | 13 | Does the agent know the rules? |
| Build & Dev Environment | 12 | Can the agent build and run the project? |
| **Total** | **74** | |
