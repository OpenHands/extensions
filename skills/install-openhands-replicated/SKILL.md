---
name: install-openhands-replicated
description: This skill should be used when the user asks to "install OpenHands Enterprise", "set up OHE on a VM", "run an OHE install preflight", "configure the Replicated Admin Console", "prepare DNS and TLS for OpenHands Enterprise", or "validate a Replicated Embedded Cluster installation". It guides supported AWS Terraform or manual VM installations from scoping through end-to-end validation.
---

# Install OpenHands Enterprise on Replicated

Guide a customer or field engineer from installation scoping to a usable OpenHands Enterprise deployment. Treat a green Replicated deployment as an intermediate milestone; prove the user workflows that are in scope.

> **Failed-install troubleshooting must remain read-only**
>
> Keep your investigation read-only. Do not change Kubernetes resources unless directed by OpenHands Support. Ad hoc `kubectl` changes can be overwritten during a deployment or upgrade and may leave the installation in an inconsistent state.

## Documentation Source of Truth

This version was synchronized with the latest available official OpenHands Enterprise installation, sizing, Admin Console, sandbox, troubleshooting, and VM log-collection documentation. Before acting, use the linked official pages and the customer's installer dashboard as the source of truth for release-specific values and UI steps. This skill intentionally focuses on decisions, safety gates, reusable checks, and completion evidence rather than reproducing the documentation.

## Safety Contract

- Start with planning and read-only preflight checks. Do not create infrastructure, modify DNS or firewall rules, run the installer, save Admin Console configuration, or deploy a new sequence without explicit approval for that exact operation.
- Obtain the current installer command, license bundle, release channel, and target OHE version from the customer's installer dashboard. Treat download URLs, license files, tokens, private keys, and provider credentials as secrets. Never paste or log their values.
- State the command category, expected impact, prerequisites, rollback boundary, and verification plan before each mutating phase.
- Use the Admin Console for documented deployment settings and the V1 API for documented application settings. Use KOTS ConfigValues only under a version-matched OpenHands Support procedure.
- Do not patch or edit Kubernetes resources, restart workloads, query databases directly, or rotate installer-managed secrets unless OpenHands Support directs the specific operation and the administrator approves it.
- Do not bypass host preflights except under a version-matched procedure from OpenHands or Replicated Support.
- Keep temporary secret-bearing files permission-restricted and outside repositories. Remove them after the supported configuration surface has consumed them.
- Use supported defaults first. Add integrations and operational overrides only when they are explicit requirements.
- Stop when the installed version differs from the documentation or command help, storage safety is unclear, or the requested recovery path can destroy state.

## Installation Workflow

### 1. Establish the Contract

Record:

- OHE target release and installer/Embedded Cluster version shown by the dashboard;
- trial or rollout intent and expected peak concurrent sandboxes;
- AWS Terraform or manual VM path;
- base domain, DNS owner, TLS owner, and hostname mode;
- sandbox isolation mode and whether Docker-in-sandbox is required;
- LLM provider and authentication owner;
- Git provider and optional integrations;
- embedded or external PostgreSQL and backup expectations;
- change approver, maintenance window, and support contact.

Copy `assets/install-plan.yaml` outside the skill repository and populate only non-secret scope and validation state. Do not represent it as a deployable headless configuration file. Draft missing DNS, firewall, certificate, or access requests from `references/operator-requests.md` before changing infrastructure.

### 2. Provision or Inspect Infrastructure

Use the current Quick Start and Sizing Guide to size for **peak concurrent sandboxes**. Record the approved capacity, data-volume path, isolation choice, and growth owner in `assets/install-plan.yaml`; do not cache sizing tables in this skill.

For AWS, use the Terraform module linked from the current Quick Start and review the complete plan before applying. For a manual VM, verify the documented host, storage, port, and outbound requirements. Run the reusable read-only checks with the approved data capacity and isolation mode:

```bash
DATA_PATH=/path/to/data-volume \
MIN_DATA_DISK_GIB="${PLANNED_DATA_DISK_GIB:?set from approved sizing plan}" \
SANDBOX_ISOLATION=sysbox \
scripts/check_host_preflight.sh
scripts/check_dns.sh <base-domain> simple
scripts/check_tls_files.sh <base-domain> <certificate-bundle> <private-key> wildcard
scripts/check_outbound.sh <approved-llm-or-proxy-https-url>
```

Resolve failures before obtaining approval to run the installer. Read `references/install-flow.md` for the current requirements and phased checklist.

### 3. Review the Installer Operation

Use only commands copied from the customer's installer dashboard for the chosen release. Before execution:

1. Confirm the VM and base domain.
2. Confirm the installer-side instance name is not being confused with the cloud resource name.
3. Confirm the license and TLS file paths exist without printing their contents.
4. Confirm host, DNS, port, outbound, sizing, disk, and isolation preflights passed.
5. Explain that installation creates system services, Kubernetes state, storage, and an Admin Console.
6. Obtain explicit approval to run the exact dashboard-provided install command.

Run the interactive installer in a real PTY. Stop rather than scripting around an unexpected password or terminal prompt. Do not claim a headless installation from the non-secret planning asset; require a documented release-specific schema and secret-input method before automating ClickOps.

### 4. Configure the Admin Console in Layers

Follow the target release's Admin Console documentation and configure only the baseline needed for validation:

1. domain and TLS;
2. one administrator-managed LLM provider;
3. database and sandbox settings sized from the approved plan;
4. required Git authentication;
5. deployment, first login, and organization behavior.

Before saving, review the intended values, expected restarts, rollback boundary, and verification plan, then obtain explicit approval. Treat populated screens as secret-bearing and defer optional integrations and advanced settings until the baseline passes. Use `references/admin-config.md` for the approval checklist and Support-only escape hatch, not as a substitute for the official field reference.

### 5. Prove the Core Product

On a fresh install, validate the baseline before adding optional configuration. Create one simple conversation through the UI or V1 API and confirm that its sandbox reaches `READY`. If the baseline is broken, report it as a platform or product issue rather than patching around it with infrastructure changes. Treat a fresh install that cannot start a sandbox as a bug, not a configuration task.

Do not declare completion from pod readiness alone. Verify:

- Admin Console and application TLS validate for the configured hostnames;
- deployment status is Ready and workloads have no new warning events;
- login works in a clean browser session;
- the first organization and bounded API key work;
- the configured model completes one tiny request;
- one no-repository conversation reaches `READY` and finishes with an expected marker;
- repository search and one repository-backed conversation work when a Git provider is in scope.

Run `scripts/preflight_storage_guard.sh <namespace>` before declaring the deployment durable. Record what the backup does and does not cover.

### 6. Add Optional Integrations

Validate integrations one at a time after core login, LLM, and conversation paths pass. Use `references/integrations.md` and the focused checklist scripts. Prove a real event or linked account; a reachable callback URL is not sufficient.

### 7. Produce the Handoff

Record:

```text
OHE release:
Embedded Cluster/installer version:
Infrastructure path and region/site:
Hostname mode and base domain:
Database and storage class:
Enabled integrations:
Preflight evidence:
Core smoke-test evidence:
Backup and restore boundary:
Known limitations:
Support-bundle command and approved support channel:
```

Exclude credentials, license contents, private keys, unredacted ConfigValues, and complete environment dumps.

## Support-Directed ConfigValues Gate

The current OpenHands installation workflow uses the Admin Console. Do not use `scripts/apply_kots_config.sh` unless a version-matched OpenHands Support procedure directs a KOTS ConfigValues change. The helper prints its command by default and requires both `--support-directed` and `--execute` before it can mutate configuration. Re-run workload, readiness, storage, and user-path verification after any approved deployment.

## Resources

- OpenHands Enterprise Quick Start: https://docs.openhands.dev/enterprise/quick-start
- OpenHands Enterprise Sizing Guide: https://docs.openhands.dev/enterprise/sizing-guide
- Admin Console Configuration: https://docs.openhands.dev/enterprise/vm-install/admin-console-configuration
- Conversations and Sandboxes: https://docs.openhands.dev/enterprise/conversations-and-sandboxes
- Docker in the Agent Sandbox: https://docs.openhands.dev/enterprise/docker-in-sandbox
- Troubleshooting: https://docs.openhands.dev/enterprise/troubleshooting
- VM Log Collection: https://docs.openhands.dev/enterprise/vm-install/log-collection
- `references/install-flow.md`: phase gates, approval checkpoints, support-bundle routing, and completion criteria.
- `references/admin-config.md`: Admin Console save checklist and Support-directed ConfigValues escape hatch.
- `references/integrations.md`: GitHub, GitLab, Bitbucket, Jira, Slack, analytics, and automation validation.
- `references/backup-and-durability.md`: persistence checks and recovery boundaries.
- `references/blue-green-reinstall.md`: separately approved rebuild and cutover workflow.
- `references/operator-requests.md`: customer-ready DNS, firewall, TLS, and access request templates.
- `references/git-provider-auth.md`: provider-specific application setup, approval, and validation routing.
- `assets/install-plan.yaml`: non-secret scoping and validation record; never use it as deployable ConfigValues.
- `scripts/check_host_preflight.sh`: read-only Linux, sizing, data-disk, isolation, and port checks.
- `scripts/check_dns.sh`: Simple or Legacy hostname resolution checks.
- `scripts/check_tls_files.sh`: certificate dates, key matching, SAN coverage, and trust-chain checks.
- `scripts/check_outbound.sh`: required outbound reachability checks.
- `scripts/summarize_terraform_outputs.sh`: allowlisted, non-sensitive Terraform output summary.
- `scripts/apply_kots_config.sh`: OpenHands Support-directed KOTS ConfigValues helper.
- `scripts/preflight_storage_guard.sh`: Postgres PVC, DiskPressure, host-space, and ClickHouse checks.
