# Install Flow

Use this checklist for a new OpenHands Enterprise VM installation delivered through Replicated Embedded Cluster. This version was synchronized with the latest available official Enterprise documentation, but the target release documentation and customer's installer dashboard remain authoritative.

## Phase 1: Scope and Approval

Capture before changing infrastructure:

- target OHE release and installer/Embedded Cluster version;
- trial or rollout intent and expected peak concurrent sandboxes;
- AWS Terraform or manual VM path;
- base domain, DNS owner, hostname mode, and TLS owner;
- sandbox isolation mode and whether Docker-in-sandbox is required;
- LLM provider and authentication owner;
- Git provider and optional integrations;
- embedded or external PostgreSQL;
- backup, recovery, and maintenance-window expectations;
- named approver for infrastructure, installer, DNS, and application changes.

Keep installer URLs, license files, private keys, and credentials out of tickets, chat, shell history, and repositories.

## Phase 2: Infrastructure Requirements

Use the current Quick Start, Sizing Guide, and installer host requirements. Record the approved peak concurrent sandboxes, capacity, data path, isolation mode, ports, outbound endpoints, and growth owner in the non-secret install plan.

Run the read-only checks on the target VM:

```bash
DATA_PATH=/path/to/data-volume \
MIN_DATA_DISK_GIB="${PLANNED_DATA_DISK_GIB:?set from approved sizing plan}" \
SANDBOX_ISOLATION=sysbox \
scripts/check_host_preflight.sh
scripts/check_outbound.sh <approved-llm-or-proxy-https-url>
```

Pass every required customer-approved endpoint to the outbound checker. Rely on the installer preflight for checks this helper cannot safely perform, including storage latency; do not bypass a failure.

For AWS, use the Terraform module linked from the current Quick Start. Review `terraform plan` before approval and use the allowlisted output helper after apply:

```bash
scripts/summarize_terraform_outputs.sh <terraform-directory>
```

Do not print complete Terraform outputs because they can contain sensitive values or local key paths.

## Phase 3: DNS and TLS

Select the hostname and routing mode from the current Admin Console documentation. Preserve an existing installation's mode unless migration is the approved task, and record the complete hostname, callback, DNS, certificate, and trust requirements before requesting changes.

Run the matching checks:

```bash
scripts/check_dns.sh <base-domain> simple
scripts/check_tls_files.sh <base-domain> <certificate-bundle> <private-key> wildcard
```

Use `legacy` only for a confirmed Legacy installation. For Manual hostnames or path-based routing, validate the complete documented host and SAN set rather than assuming wildcard coverage.

## Phase 4: Outbound Preflight

Build the endpoint list from the current installation documentation and the selected providers, then run the checks from the target VM. Resolve DNS, timeout, proxy, or firewall failures before running the installer; an authentication or method error can still prove network reachability.

## Phase 5: Installer

Use the customer's installer dashboard for the target release. Review the exact download, license, TLS, and install commands without exposing sensitive values; explain the impact and rollback boundary; obtain explicit approval; then run the dashboard-provided installer in a real interactive PTY. Stop on unexpected prompts or version differences rather than inventing flags or workarounds.

If installation did not complete, collect a support bundle with the original installer from its extracted directory:

```bash
sudo ./openhands support-bundle
```

After installation, use the installed application binary:

```bash
sudo /var/lib/embedded-cluster/bin/openhands support-bundle
```

Treat the bundle as sensitive. Open a support ticket through the approved portal and attach the archive, or mention a **Send bundle to vendor** upload. Do not change Kubernetes resources while investigating unless directed by OpenHands Support.

## Headless and Declarative Boundary

Do not claim a fully headless installation unless the target OHE release exposes a documented installer flag, configuration schema, and supported secret-input mechanism. The current customer-safe default is:

- use the installer dashboard for version-specific download and license commands;
- run the interactive installer in a real PTY;
- complete required Admin Console steps with guided ClickOps;
- use KOTS ConfigValues only under a version-matched OpenHands Support procedure;
- keep `assets/install-plan.yaml` as a non-secret planning record, not deployment input.

When headless installation is required, collect the target binary's `install --help`, the release-specific schema, secret-injection method, and rollback procedure from official documentation or OpenHands Support before implementation.

## Phase 6: Admin Console Configuration

Follow the target release's Admin Console field reference. Configure the minimum baseline in layers: domain and TLS, one LLM provider, database and sandbox settings, required Git authentication, deployment, then first login and organization behavior. Review impact and obtain approval before each save or deployment. Defer optional configuration until core validation passes.

## Phase 7: Core Validation

Minimum done state:

- `https://admin.<base-domain>:30000` and `https://app.<base-domain>` present valid TLS;
- app readiness succeeds;
- login works in a clean browser session;
- first organization and bounded API key work;
- one tiny model request succeeds;
- one no-repository conversation completes with an expected marker;
- repository search and a repository-backed conversation work when a Git provider is in scope;
- storage guard passes;
- no new warning events appear during the smoke tests.

Add optional integrations only after these checks pass.

## Phase 8: Handoff

Provide versions, topology, hostnames, enabled features, smoke-test evidence, backup boundaries, known limitations, and the approved support path. Exclude secrets and customer data. Use `operator-requests.md` for unresolved DNS, firewall, TLS, and access requests.

## Official References

- OpenHands Enterprise Quick Start: https://docs.openhands.dev/enterprise/quick-start
- OpenHands Enterprise Sizing Guide: https://docs.openhands.dev/enterprise/sizing-guide
- Admin Console Configuration: https://docs.openhands.dev/enterprise/vm-install/admin-console-configuration
- Conversations and Sandboxes: https://docs.openhands.dev/enterprise/conversations-and-sandboxes
- Docker in the Agent Sandbox: https://docs.openhands.dev/enterprise/docker-in-sandbox
- Troubleshooting: https://docs.openhands.dev/enterprise/troubleshooting
- VM Log Collection: https://docs.openhands.dev/enterprise/vm-install/log-collection
- Replicated Embedded Cluster installation: https://docs.replicated.com/enterprise/installing-embedded
- Replicated requirements: https://docs.replicated.com/enterprise/installing-embedded-requirements
