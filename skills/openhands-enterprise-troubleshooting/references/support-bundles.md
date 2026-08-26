# OHE Support Bundle Workflow

Start with a support bundle. It is the fastest way to give OpenHands Support a snapshot of the installation, and the customer does not need to investigate the problem before opening a support ticket.

## Generate the Bundle

### Replicated VM: Admin Console

Use the Admin Console when it is available:

1. Open `https://admin.<your-base-domain>:30000`.
2. Select **Troubleshoot**.
3. Select **Analyze** and wait for it to finish.
4. Select **Download bundle**.

If **Send bundle to vendor** is available, the customer can upload it directly for inspection. Sending a bundle does not open a support ticket; the customer must still open a ticket and mention the upload.

### Replicated VM: Command Line

When the Admin Console is unavailable, connect to a controller VM and run:

```bash
sudo /var/lib/embedded-cluster/bin/openhands support-bundle
```

If installation did not complete, run the original installer from the directory where it was extracted:

```bash
sudo ./openhands support-bundle
```

### Kubernetes: Helm

From a workstation with `kubectl` access, run:

```bash
kubectl support-bundle --load-cluster-specs --namespace openhands
```

If the `support-bundle` CLI is unavailable, stop and follow the Kubernetes installation guide. Do not substitute an invented command or assume that the plugin is installed merely because `kubectl` is available.

Official references:

- https://docs.openhands.dev/enterprise/troubleshooting
- https://docs.openhands.dev/enterprise/k8s-install/installation#step-5-validate-the-installation

## Open a Support Ticket

Attach the generated archive through the OpenHands Support Portal provided during Enterprise onboarding. If **Send bundle to vendor** was used, mention that upload in the ticket. Include:

- when the problem occurred, including the time zone;
- the affected user or conversation ID, when applicable;
- expected and actual behavior;
- recent upgrades or configuration changes;
- reproduction steps.

If the Support Portal is unavailable, contact the customer's OpenHands representative.


## Handle the Bundle Safely

Treat the archive as potentially sensitive. It can contain:

- hostnames, IP addresses, and resource names;
- configuration metadata;
- application and infrastructure logs;
- repository identifiers, usernames, prompts, request metadata, or customer payloads written to logs;
- Secret names and key names, even when values are excluded.

Before sharing:

1. Confirm the destination is an approved support channel.
2. Avoid attaching the bundle to a public issue or public chat.
3. Do not extract and paste the entire archive into a conversation.
4. Review unexpected custom collectors before upload when policy requires it.
5. Never add private keys, tokens, passwords, browser cookies, or separate secret files to the archive.
6. Preserve the original archive for integrity; create a redacted copy only when organizational policy requires redaction.

## Triage Order

Bundle layouts vary by release. Start with discovery rather than assuming exact paths:

```bash
find BUNDLE_DIRECTORY -maxdepth 3 -type f | sort | sed -n '1,240p'
```

Then inspect in this order:

1. Analyzer output such as `analysis.json` or preflight results.
2. Node conditions, disk and memory evidence, events, and pod status.
3. Current workload images and rollout state.
4. Logs for the service on the failing path and the reported time window.
5. Ingress, certificate metadata, and DNS collectors for public-access failures.
6. PVCs and stateful workload status for database or storage failures.
7. Application-specific evidence such as runtime-api, OpenHands, integrations, automation, LiteLLM, and Keycloak logs.

Common OHE bundle paths can include:

```text
analysis.json
cluster-resources/
cluster-resources/pods/logs/openhands/
app/openhands/logs/
app/openhands-runtime-api/logs/
```

Absence of a path is not proof that a service is absent; collector layouts changed across OHE releases.

## Interpret High-Signal Evidence

### Runtime startup

Strong evidence that a runtime started:

- runtime workload exists;
- container reached `Running` and Ready;
- logs report server initialization complete;
- readiness checks return `200`.

If those pass, investigate OpenHands routing, conversation identifiers, or warm-runtime selection rather than labeling the incident a sandbox boot failure.

### Rollout skew

Compare:

- requested runtime image;
- warm runtime image;
- current runtime-api and OpenHands images;
- current and target OHE releases.

A mismatch can force cold starts or create incompatible behavior after an incomplete rollout.

### Authentication

Separate:

- Replicated Admin Console authentication;
- OpenHands/Keycloak user authentication;
- OpenHands API-key authentication;
- Git provider authorization.

Similar browser symptoms can have different owners and data stores.

### Provider failures

Distinguish intermittent timeouts from consistent `401` or `403` responses. A provider timeout can be secondary when the core runtime or application path is already failing.

### Storage

Identify the largest consumer and whether stateful data is persistent. Diagnostic logs can cause disk pressure even when user-facing application tables are small. Do not infer that ClickHouse diagnostic-table size represents LLM token volume.

## Compare with a Known-Good Bundle

When possible, compare the same product release and installation type. Compare the exact failing path rather than total archive size:

- images and versions;
- workload readiness and restart counts;
- events around the same action;
- endpoint status;
- log markers before and after the failure;
- ingress and certificate metadata;
- PVC and storage class configuration.

A warning present in both failing and healthy bundles is less likely to be causal.

## Bundle-Based Handoff

Summarize findings without copying unnecessary raw data:

```text
Bundle generated: <timestamp>
OHE release: <version>
Embedded Cluster: <version>
Reported failure window: <timestamp and timezone>

Likely root cause:
<one paragraph>

Primary evidence:
- <bundle path>: <observation>
- <bundle path>: <observation>

Secondary findings:
- <finding and why it is not primary>

Ruled out:
- <alternative and evidence>

Recommended next step:
<action, owner, risk, and approval required>
```

Reference bundle-relative file paths and timestamps. Do not include credentials, complete environment dumps, or customer payloads.
