# OpenHands Enterprise Troubleshooting

An agent-runnable skill for diagnosing OpenHands Enterprise Replicated VM and Helm installations. It starts with support bundles, keeps Kubernetes investigation read-only, documents continuous VM log collection, and produces support-ready handoffs.

## Critical Safety Rule

> Keep your investigation read-only. Do not change Kubernetes resources unless directed by OpenHands Support. Ad hoc `kubectl` changes can be overwritten during a deployment or upgrade and may leave the installation in an inconsistent state.

## Safety Model

- Start with a support bundle; customers do not need to investigate before opening a support ticket.
- Discover the installed OHE, Embedded Cluster, Kubernetes, namespace, and workload topology before targeting resources.
- Never print or decode credentials or complete Kubernetes Secret values.
- Treat support bundles as potentially sensitive and share them only through approved channels.
- When OpenHands Support directs a change, require explicit administrator approval, backup checks, impact disclosure, and a recovery path first.
- Prefer the Admin Console, Helm values, and documented OpenHands or Replicated procedures over direct Kubernetes changes.

## What This Skill Does

### Triage and Diagnosis

- Separates host, cluster, ingress, authentication, runtime, integration, LLM, automation, and product health.
- Checks sandbox startup, certificates, Keycloak login, Git providers, LiteLLM, Admin Console access, upgrades, and resource exhaustion.
- Uses bounded, targeted diagnostic commands and interprets evidence without exposing credentials.

### Support-Directed Recovery

- Does not change Kubernetes resources unless directed by OpenHands Support.
- States the likely root cause, exact operation, impact, backup prerequisites, recovery path, and verification steps.
- Requires explicit administrator approval for the specific support-directed operation.
- Stops and escalates when persistence, database safety, or version-specific behavior is unclear.

### Support Bundle Triage

- Starts with the Admin Console, then uses the documented VM or Helm command when needed.
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
- "Send OHE VM logs to our observability platform"

## Files

- `SKILL.md`: core safety model and diagnostic workflow.
- `references/diagnostics.md`: version-aware read-only commands and interpretation.
- `references/support-bundles.md`: documented collection, privacy handling, ticket handoff, triage, and comparison.
- `references/log-collection.md`: continuous VM log locations, retention limits, and observability-agent guidance.

## For Contributors

Convert field incidents into generic symptom, evidence, and recovery patterns. Validate commands against supported OHE and Embedded Cluster releases, keep diagnostics read-only by default, and exclude customer-specific names, domains, IDs, credentials, private paths, and one-off patches.
