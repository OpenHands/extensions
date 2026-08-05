# OpenHands Enterprise Troubleshooting

An agent-runnable skill for diagnosing OpenHands Enterprise installations delivered through Replicated Embedded Cluster. It provides version-aware, read-only-first checks, guarded recovery guidance, support bundle triage, and escalation handoffs.

## Safety Model

- Discover the installed OHE, Embedded Cluster, Kubernetes, namespace, and workload topology before targeting resources.
- Keep the initial diagnostic pass read-only.
- Never print or decode credentials or complete Kubernetes Secret values.
- Treat support bundles as potentially sensitive and share them only through approved channels.
- Require explicit approval, backup checks, impact disclosure, and a recovery path before mutating an installation.
- Prefer supported Replicated and KOTS workflows over direct Kubernetes changes that reconciliation can overwrite.

## What This Skill Does

### Triage and Diagnosis

- Separates host, cluster, ingress, authentication, runtime, integration, LLM, automation, and product health.
- Checks sandbox startup, certificates, Keycloak login, Git providers, LiteLLM, Admin Console access, upgrades, and resource exhaustion.
- Uses bounded, targeted diagnostic commands and interprets evidence without exposing credentials.

### Guarded Recovery

- States the likely root cause, exact operation, impact, backup prerequisites, and verification steps.
- Requires explicit approval before restarts, configuration changes, credential rotation, rollback, cleanup, or node operations.
- Stops and escalates when persistence, database safety, or version-specific behavior is unclear.

### Support Bundle Triage

- Uses the supported application-installer command when available.
- Handles bundles as sensitive artifacts.
- Prioritizes analyzer results, workload state, events, images, bounded logs, ingress, certificates, and storage evidence.
- Compares failing evidence with a known-good path when possible.

### Escalation Handoff

- Produces a concise support-ready summary with versions, impact, evidence, checks, approved changes, ruled-out causes, and one recommended next step.
- Excludes secrets, customer data, complete environment dumps, and unnecessary log volume.

## Common Issues Covered

- Sandbox or runtime startup failures
- Git provider authorization and webhook failures
- Certificate expiration, trust, chain, and hostname errors
- LiteLLM and upstream model connectivity failures
- Keycloak and OpenHands login issues
- Replicated Admin Console access problems
- Upgrade or migration failures
- OOM, DiskPressure, PVC, and diagnostic-log growth

## Usage

The skill activates for requests such as:

- "Troubleshoot OpenHands Enterprise"
- "OpenHands is not working"
- "A sandbox failed to start"
- "The Replicated Admin Console is unavailable"
- "The certificate expired"
- "The LLM connection failed"
- "Analyze this OHE support bundle"

## Files

- `SKILL.md`: core safety model and diagnostic workflow.
- `references/diagnostics.md`: version-aware read-only commands and interpretation.
- `references/support-bundles.md`: supported collection, privacy handling, triage, and comparison.

## For Contributors

Convert field incidents into generic symptom, evidence, and recovery patterns. Validate commands against supported OHE and Embedded Cluster releases, keep diagnostics read-only by default, and exclude customer-specific names, domains, IDs, credentials, private paths, and one-off patches.
