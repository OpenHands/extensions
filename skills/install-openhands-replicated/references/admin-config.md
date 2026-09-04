# Admin Console Configuration

This version was synchronized with the latest available official Admin Console documentation. Use that documentation as the field reference; this file defines the review and approval boundary.

Treat every save or deployment as a mutating operation that can restart components. Before approval, record:

- the target release and authoritative field reference;
- changed fields and why they are required;
- affected hostnames, callbacks, trust chains, or external systems;
- expected restarts and user impact;
- rollback boundary and post-save verification;
- the administrator who approves the exact operation.

## Domain, TLS, and Routing

Choose the documented hostname and routing mode for the installation. Preserve existing modes unless migration is the approved task. Record and validate the complete DNS, certificate, CORS, OAuth callback, and webhook callback set; do not infer it from an older runbook.

Keep certificate and key files outside repositories, do not print their contents, and validate them with `scripts/check_tls_files.sh`. Use the documented trusted-CA mechanism rather than disabling certificate verification.

## LLM Provider

Configure one administrator-managed provider for the baseline. Resolve provider, authentication, region, model identifier, and BYOK choices from the current documentation and provider API rather than copied examples. Verify the configured model appears through the supported model-discovery path and completes one minimal request before adding another provider.

## Sandbox and Organization Decisions

Derive isolation, routing, per-sandbox resources, lifecycle, and warm-capacity values from the approved plan and current sandbox documentation. Confirm the aggregate fits the host. Treat host mounts, device passthrough, extended retention, and weaker isolation as explicit risk decisions that require a documented need.

Record intended first-user, default-organization, membership, and personal-workspace behavior before deployment. Validate the resulting behavior with a clean first login; do not assume disabling an option reverses previously created state.

## Optional Settings

Defer SMTP, proxy, analytics, automations, plugins, and other optional settings until the baseline passes. For required proxies or private CAs, keep certificate verification enabled and use the documented trust configuration.


## Declarative KOTS Config

Use the Admin Console for the documented installation workflow. Use a KOTS `ConfigValues` merge patch only when a version-matched OpenHands Support procedure directs it and confirms the referenced keys:

```yaml
apiVersion: kots.io/v1beta1
kind: ConfigValues
spec:
  values:
    config_key:
      value: "new-value"
```

Treat ConfigValues files as potentially secret-bearing. Keep them outside repositories, restrict permissions, avoid shell tracing, and do not paste their contents into chat or tickets.

After confirming the Support procedure, preview the command first:

```bash
scripts/apply_kots_config.sh \
  --appslug openhands \
  --config-file ./config-values.patch.yaml \
  --current \
  --support-directed
```

After reviewing the preview and obtaining administrator approval, execute without deployment:

```bash
scripts/apply_kots_config.sh \
  --appslug openhands \
  --config-file ./config-values.patch.yaml \
  --current \
  --support-directed \
  --execute
```

Add `--deploy` only when an immediate rollout is approved. Verify the new sequence, rollout status, application readiness, storage guard, and affected user path.

## Secret Field Shape

Avoid exporting decrypted configuration unless a support or migration procedure requires it. When a version-matched procedure requires a decrypted export, preserve the original field shape for secret/file items and do not encode an already encoded KOTS value again.

A double-encoded GitHub App private key can cause key parsing failures in components that consume it. Correct the value through the supported configuration surface; do not extract or patch Kubernetes Secret values as an installation shortcut.

## Installer-Managed Secrets

Do not rotate installer-managed PostgreSQL, Redis, JWT, Keycloak, LiteLLM, sandbox, plugin-directory, or Automations secrets manually. Use a component-specific procedure from OpenHands Support. Changing encryption or salt keys can make previously stored provider credentials unreadable.
