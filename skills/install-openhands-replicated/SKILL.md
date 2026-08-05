---
name: install-openhands-replicated
description: This skill should be used when the user asks to "install OpenHands Enterprise", "set up OHE on a VM", "run an OHE install preflight", "configure the Replicated Admin Console", "prepare DNS and TLS for OpenHands Enterprise", or "validate a Replicated Embedded Cluster installation". It guides supported AWS Terraform or manual VM installations from scoping through end-to-end validation.
---

# Install OpenHands Enterprise on Replicated

Guide a customer or field engineer from installation scoping to a usable OpenHands Enterprise deployment. Treat a green Replicated deployment as an intermediate milestone; prove the user workflows that are in scope.

## Safety Contract

- Start with planning and read-only preflight checks. Do not create infrastructure, modify DNS or firewall rules, run the installer, deploy ConfigValues, restart workloads, or rotate credentials without explicit approval for that exact operation.
- Obtain the current installer command, license bundle, release channel, and target OHE version from the customer's installer dashboard. Treat download URLs, license files, tokens, private keys, and provider credentials as secrets. Never paste or log their values.
- State the command category, expected impact, prerequisites, rollback boundary, and verification plan before each mutating phase.
- Prefer supported Replicated and KOTS surfaces. Do not use direct Kubernetes patches as installation steps. Do not bypass host preflights except under a version-matched procedure from OpenHands or Replicated Support.
- Keep temporary secret-bearing files permission-restricted and outside repositories. Remove them after the supported configuration surface has consumed them.
- Use supported defaults first. Add integrations and operational overrides only when they are explicit requirements.
- Stop when the installed version differs from the documentation or command help, storage safety is unclear, or the requested recovery path can destroy state.

## Installation Workflow

### 1. Establish the Contract

Record:

- OHE target release and installer/Embedded Cluster version shown by the dashboard;
- AWS Terraform or manual VM path;
- base domain, DNS owner, TLS owner, and hostname mode;
- LLM provider and authentication owner;
- Git provider and optional integrations;
- embedded or external PostgreSQL and backup expectations;
- change approver, maintenance window, and support contact.

Copy `assets/install-plan.yaml` outside the skill repository and populate only non-secret scope and validation state. Do not represent it as a deployable headless configuration file. Draft missing DNS, firewall, certificate, or access requests from `references/operator-requests.md` before changing infrastructure.

### 2. Provision or Inspect Infrastructure

Use the current OpenHands AWS Terraform module when AWS Terraform is selected. For a manual VM, require the documented CPU, memory, disk, latency, OS, systemd, root access, inbound ports, local ports, and outbound destinations.

Run read-only preflights on the target VM:

```bash
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
4. Confirm host, DNS, port, and outbound preflights passed.
5. Explain that installation creates system services, Kubernetes state, storage, and an Admin Console.
6. Obtain explicit approval to run the exact dashboard-provided install command.

Run the interactive installer in a real PTY. Stop rather than scripting around an unexpected password or terminal prompt. Do not claim a headless installation from the non-secret planning asset; require a documented release-specific schema and secret-input method before automating ClickOps.

### 4. Configure the Admin Console in Layers

Use the current `Simple` hostname mode unless the customer requires manual hostnames. Configure and validate one layer at a time:

1. domain and publicly trusted TLS;
2. one LLM provider;
3. database choice and storage durability;
4. core application deployment;
5. first login and organization;
6. Git provider authentication using `references/git-provider-auth.md`;
7. optional integrations, analytics, automations, and advanced settings.

Read `references/admin-config.md` before applying settings. Treat ConfigValues files as potentially secret-bearing. Preview helper operations before execution.

### 5. Prove the Core Product

Do not declare completion from pod readiness alone. Verify:

- Admin Console and application TLS validate for the configured hostnames;
- deployment status is Ready and workloads have no new warning events;
- login works in a clean browser session;
- the first organization and bounded API key work;
- the configured model completes one tiny request;
- one no-repository conversation finishes with an expected marker;
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

## Mutating Helper Gate

Use `scripts/apply_kots_config.sh` in preview mode first:

```bash
scripts/apply_kots_config.sh \
  --appslug openhands \
  --config-file ./config-values.patch.yaml \
  --current
```

After reviewing impact and obtaining explicit approval, add `--execute`; add `--deploy` only when an immediate deployment is approved. Re-run workload, readiness, storage, and user-path verification after deployment.

## Resources

- `references/install-flow.md`: current VM requirements, hostname layouts, installer sequence, and completion criteria.
- `references/admin-config.md`: TLS, LLM, database, sandbox, proxy, and guarded ConfigValues guidance.
- `references/integrations.md`: GitHub, GitLab, Bitbucket, Jira, Slack, analytics, and automation validation.
- `references/backup-and-durability.md`: persistence checks and recovery boundaries.
- `references/blue-green-reinstall.md`: separately approved rebuild and cutover workflow.
- `references/operator-requests.md`: customer-ready DNS, firewall, TLS, and access request templates.
- `references/git-provider-auth.md`: provider-specific application setup, approval, and validation routing.
- `assets/install-plan.yaml`: non-secret scoping and validation record; never use it as deployable ConfigValues.
- `scripts/check_host_preflight.sh`: read-only Linux host and port checks.
- `scripts/check_dns.sh`: Simple or Legacy hostname resolution checks.
- `scripts/check_tls_files.sh`: certificate dates, key matching, SAN coverage, and trust-chain checks.
- `scripts/check_outbound.sh`: required outbound reachability checks.
- `scripts/summarize_terraform_outputs.sh`: allowlisted, non-sensitive Terraform output summary.
- `scripts/apply_kots_config.sh`: preview-first KOTS ConfigValues helper.
- `scripts/preflight_storage_guard.sh`: Postgres PVC, DiskPressure, host-space, and ClickHouse checks.
