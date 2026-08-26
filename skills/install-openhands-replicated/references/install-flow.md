# Install Flow

Use this checklist for a new OpenHands Enterprise VM installation delivered through Replicated Embedded Cluster. Confirm current values against the target OHE release and the customer's installer dashboard.

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

Size a rollout by expected **peak concurrent sandboxes**. One user can run multiple sandboxes, so user count is only a rough estimate. The current Quick Start trial baseline comfortably supports about 15 concurrent sandboxes:

| Resource | Trial baseline |
| --- | --- |
| CPU | 16 vCPUs |
| Memory | 64 GB |
| Disk | 200 GB |
| Disk P99 write latency | 10 ms maximum |
| Architecture | Linux x86-64 |
| Init system | systemd |
| Access | root or sudo |

Use the Sizing Guide for a larger rollout. Its current 15-sandbox starting recommendation is a 16 vCPU / 64 GiB VM with a 1 TiB SSD data disk. Put application data on a separate expandable volume, not the boot disk. Record the planned peak, per-sandbox resource overrides, data path, starting capacity, and growth owner.

Ubuntu 24.04 LTS is recommended. The default stronger sandbox isolation, required for Docker-in-sandbox, needs Linux kernel 6.3 or newer. If Docker-in-sandbox is not required, the standard isolation runtime avoids the Sysbox kernel requirement.

Inbound TCP ports:

```text
80 443 30000
```

Local ports that must be available before installation:

```text
2379 7443 9099 10248 10257 10259
```

Run on the target VM:

```bash
DATA_PATH=/path/to/data-volume \
MIN_DATA_DISK_GIB="${PLANNED_DATA_DISK_GIB:?set from approved sizing plan}" \
SANDBOX_ISOLATION=sysbox \
scripts/check_host_preflight.sh
scripts/check_outbound.sh <approved-llm-or-proxy-https-url>
```

Pass each customer-approved LLM, cloud-model, or corporate gateway HTTPS endpoint required by the selected authentication mode.

The host script cannot prove P99 storage latency without a write benchmark. Rely on the installer host preflight for the final latency check. Do not bypass a failed latency preflight; increase disk IOPS/throughput or use faster storage.

For AWS Terraform, use the current module linked by the OpenHands Enterprise quick start. On a fresh installation, explicitly set `hostname_mode = "wildcard"`, which is the Terraform name for Admin Console `Simple` mode. Reserve `hostname_mode = "legacy"` for reproducing an existing Legacy installation.

Review `terraform plan` before requesting approval for `apply`. Confirm a fresh Simple-mode plan provisions `*.<base-domain>` and does not provision `auth.app.<base-domain>` or `*.runtime.<base-domain>`. Use the allowlisted output helper after apply:

```bash
scripts/summarize_terraform_outputs.sh <terraform-directory>
```

Do not print the full Terraform output set because it can include sensitive values or local key paths.

## Phase 3: DNS and TLS

The current default is `Simple` hostname mode. A wildcard DNS record and certificate for `*.<base-domain>` cover:

```text
admin.<base-domain>
app.<base-domain>
auth.<base-domain>
analytics.<base-domain>
llm-proxy.<base-domain>
runtime-api.<base-domain>
<id>-runtime.<base-domain>
```

Validate the wildcard route with a synthetic runtime name:

```bash
scripts/check_dns.sh <base-domain> simple
```

Older installations can use `Legacy` hostnames such as `auth.app.<base-domain>` and `<id>.runtime.<base-domain>`. Do not migrate an existing installation's hostname mode during unrelated work. For a confirmed Legacy installation, run:

```bash
scripts/check_dns.sh <base-domain> legacy
```

Use a publicly trusted wildcard certificate whenever possible. Self-signed certificates are not supported for the OpenHands application. A private CA requires every browser, OAuth provider, and webhook sender to trust the chain.

If wildcard certificates are unavailable, select path-based sandbox routing and obtain the complete SAN set documented for the target release.

## Phase 4: Outbound Preflight

Run outbound checks from the target VM. Required destinations currently include Replicated control-plane endpoints, OpenHands image/chart/update endpoints, GitHub, Traefik charts, Docker Hub, GHCR, and each endpoint required by the selected LLM provider or corporate gateway.

Treat HTTP responses such as 301, 401, 403, or 405 as reachable. Treat HTTP `000` as a DNS, timeout, proxy, or firewall failure.

Resolve all preflight failures before running the installer.

## Phase 5: Installer

Obtain the version-specific commands from the customer's installer dashboard. The normal sequence is:

1. register or sign in to the installer dashboard;
2. name the instance and select **Outbound requests allowed** for Network Availability;
3. select the OHE version;
4. download the installation assets with the dashboard-provided command;
5. extract the assets, including the license file;
6. review the exact install command and TLS paths;
7. obtain explicit approval;
8. run the install command in a real interactive PTY.

A representative command shape is:

```bash
sudo ./openhands install --license <license-file> \
  --tls-cert <certificate-file> \
  --tls-key <private-key-file>
```

Do not substitute a representative command for the dashboard-provided command. Do not expose the dashboard download URL or license contents.

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

Open `https://admin.<base-domain>:30000` when TLS was supplied during installation, or `http://<vm-ip>:30000` when it was omitted. In the latter case, upload the Admin Console certificate before configuring OpenHands. For a single-node deployment, continue past the add-node screen.

Configure in layers:

1. `Simple (default)` hostname mode and base domain;
2. certificate, private key, and optional additional trusted CA;
3. one administrator-managed LLM provider and exact model IDs;
4. bundled or prepared external PostgreSQL;
5. sandbox isolation, routing, resources, and lifecycle settings;
6. GitHub App authentication when GitHub is selected;
7. core application deployment;
8. first login and default organization behavior;
9. optional integrations, SMTP, proxy, analytics, automations, plugins, and advanced options.

Wait for deployment status to reach Ready and inspect resource details before moving to user-path validation.

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
