---
name: openhands-enterprise-troubleshooting
description: This skill should be used when a user asks to "troubleshoot OpenHands Enterprise", reports that "OpenHands is not working", "a sandbox failed to start", "login is broken", "the certificate expired", "the LLM connection failed", "the Replicated Admin Console is unavailable", "an OHE upgrade failed", asks to analyze an OpenHands Enterprise support bundle, needs VM log collection guidance for a Replicated installation, or is troubleshooting a Helm installation.
---

# OpenHands Enterprise Troubleshooting

Diagnose OpenHands Enterprise installations delivered through Replicated Embedded Cluster or Helm. Use evidence to identify the failing layer and produce a support-ready handoff.

> **Critical safety rule**
>
> Keep your investigation read-only. Do not change Kubernetes resources unless directed by OpenHands Support. Ad hoc `kubectl` changes can be overwritten during a deployment or upgrade and may leave the installation in an inconsistent state.

## Safety Rules

1. Do not restart workloads, edit or patch resources, change ConfigValues, rotate credentials, delete resources, truncate tables, roll back releases, reset nodes, or reinstall the application during investigation.
2. If OpenHands Support directs a change, establish backup and storage safety, disclose the impact, obtain the administrator's explicit approval, and define recovery and verification steps first.
3. Never print, decode, or request private keys, API keys, passwords, access tokens, complete Kubernetes Secret values, or unredacted environment-variable dumps.
4. Inspect Secret names and key names only. Ask the administrator to validate a credential through the product UI or provider API without sharing its value.
5. Treat support bundles as potentially sensitive. Obtain approval before uploading a bundle and use the approved support channel.
6. Prefer the Admin Console, Helm values, and documented OpenHands or Replicated procedures. Never improvise direct Kubernetes changes.
7. Stop and escalate when the safe path is unclear, the database or storage layer is at risk, or a command differs from the installed version's help output.

## Diagnostic Workflow

### 1. Start With a Support Bundle

A support bundle is the fastest way to give OpenHands Support a snapshot of the installation. The customer does not need to investigate before opening a support ticket.

For a Replicated VM, prefer **Troubleshoot > Analyze > Download bundle** in the Admin Console. If the console is unavailable, use the documented VM command. For Helm, use the documented Kubernetes command. Read `references/support-bundles.md` for the exact commands, safe handling, ticket details, and triage order.

For continuous retention in the customer's observability platform, read `references/log-collection.md`. VM logs are retained only briefly, and sandbox logs are deleted when their conversations are cleaned up.

### 2. Establish Installation Context

Collect these facts before interpreting symptoms:

- OpenHands Enterprise release shown by KOTS or Helm.
- Embedded Cluster installer and Kubernetes versions, when applicable.
- Installation type: Replicated VM or Helm.
- Application namespace; normally `openhands`, but verify it.
- Failure start time, affected users, exact error, URL, conversation or automation ID, and recent install or upgrade activity.

Do not confuse the installer component version with the deployed OHE application release. Read `references/diagnostics.md#version-and-topology` and record both when applicable.

### 3. Separate Health Layers

Check each layer independently:

1. Host and node health: disk, memory, pressure conditions, and system services.
2. Embedded Cluster and Admin Console health, for Replicated VM installations.
3. Kubernetes workload readiness and recent events.
4. Public DNS, TLS, ingress, and application readiness.
5. Authentication and Keycloak.
6. Runtime API and sandbox lifecycle.
7. Git provider integration.
8. LiteLLM and upstream model access.
9. Automation or other optional services.

A successful `/ready` response proves only basic application readiness. It does not prove login, repository access, model inference, automation routing, or runtime startup.

### 4. Match the Symptom to a Focused Path

- Sandbox startup or conversation timeout: inspect runtime-api, runtime workloads, image pulls, PVCs, and capacity.
- Login or OAuth failure: inspect OpenHands and Keycloak readiness, database health, callback routing, and browser session behavior.
- GitHub or GitLab failure: inspect `openhands-integrations` and validate access with a credential already held by the administrator; never extract a provider token from Kubernetes.
- Certificate failure: verify public trust, hostname, SANs, chain, and expiration. Distinguish the Admin Console certificate from application ingress certificates.
- LLM failure: inspect OpenHands and LiteLLM logs, model aliases, endpoint reachability, and provider-side authorization without exposing credentials.
- Admin Console failure: inspect the host, `kotsadm`, Embedded Cluster services, and port `30000` separately from the OpenHands application.
- Upgrade failure: record current and target releases, preflight results, failed jobs, workload images, and storage safety. Do not improvise a rollback.
- OOM or disk pressure: identify the resource consumer and persistent-data risk before restarting anything.

Use only the read-only commands and interpretation guidance in `references/diagnostics.md`.

### 5. Apply Support-Directed Recovery Only After Approval

Before proposing a change, state:

- likely root cause and evidence;
- exact operation;
- expected impact and downtime;
- rollback or recovery path;
- whether the change is durable through KOTS reconciliation and upgrades;
- backup or snapshot prerequisites;
- verification steps.

Proceed only when OpenHands Support has directed the change and the administrator has explicitly approved the specific operation. Avoid combining an incident fix with unrelated cleanup or configuration changes.

### 6. Verify the Real User Path

After an approved recovery:

- confirm workload readiness and absence of new warning events;
- check public TLS and the relevant health endpoint;
- exercise the exact failing path with the administrator;
- for runtime or LLM incidents, create one bounded test conversation;
- for provider incidents, test one repository operation;
- for automation incidents, dispatch one bounded test event or run;
- record the versions and commands used.

Metadata or readiness checks alone are not proof that the user workflow is restored.

## Escalation Handoff

Produce this structure when the issue is unresolved or requires a product change:

```text
Issue: <one-line summary>
Impact: <users and workflows affected>
Started: <timestamp and timezone>
Versions: OHE <release>; Embedded Cluster <version>; Kubernetes <version>

Likely failing layer:
<host, cluster, ingress, auth, runtime, integration, LLM, automation, or product>

Evidence:
- <timestamp, resource or bundle path, observation>
- <expected versus actual behavior>

Checks completed:
- <read-only check and result>

Changes attempted:
- <approved change, result, and rollback status>

Ruled out:
- <alternative cause and evidence>

Recommended next step:
<one concrete action, owner, risk, and required approval>

Attachments:
- <support bundle or redacted excerpts through the approved channel>
```

Exclude secrets, customer data, full environment dumps, and unnecessary log volume.

## References

- `references/diagnostics.md`: version-aware, read-only checks for common OHE failure modes.
- `references/support-bundles.md`: documented collection, privacy handling, ticket handoff, bundle triage, and comparison workflow.
- `references/log-collection.md`: continuous VM log collection and retention guidance.
- OpenHands Enterprise troubleshooting: https://docs.openhands.dev/enterprise/troubleshooting
- OpenHands Enterprise VM log collection: https://docs.openhands.dev/enterprise/vm-install/log-collection
- Replicated Embedded Cluster v2 troubleshooting: https://docs.replicated.com/embedded-cluster/v2/embedded-troubleshooting

## Maintenance

Validate commands against the currently supported OHE and Embedded Cluster releases before publishing changes. Convert field incidents into generic symptom, evidence, and recovery patterns; keep customer names, credentials, domains, internal IDs, and environment-specific patches in private overlays.
