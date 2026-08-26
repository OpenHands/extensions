# Admin Console Configuration

Use the Admin Console for supported settings. Treat a saved configuration as a mutating operation that can restart components. Review the intended values, impact, and verification plan before selecting Deploy.

## Domain and TLS

Keep `Simple (default)` hostname mode for new installations unless DNS or network policy requires a custom hostname for every service. The AWS Terraform module calls Simple `hostname_mode = "wildcard"`; keep the Terraform and Admin Console choices aligned. Use `Manual` for custom hostnames, and do not select `Legacy` merely because an older runbook or copied Terraform directory contains nested hostnames.

In Simple mode, all service names sit directly under the base domain:

```text
admin.<base-domain>
app.<base-domain>
auth.<base-domain>
analytics.<base-domain>
llm-proxy.<base-domain>
runtime-api.<base-domain>
<id>-runtime.<base-domain>
```

Keep existing Legacy installations on their current layout unless hostname migration is the approved change. Legacy layouts can include `auth.app.<base-domain>` and `<id>.runtime.<base-domain>`.

For Manual mode, record the application, analytics, authentication, LLM proxy, Runtime API, and runtime base hostnames. Provision DNS, certificates, OAuth callbacks, and webhook callbacks for the complete set. `Additional Permitted CORS Origins` must contain browser origins with scheme and host only, without a path or trailing slash.

Use a publicly trusted wildcard certificate for customer-facing installations whenever possible. Include intermediate certificates and verify that the private key matches the server certificate without printing either value.

Self-signed certificates are not supported for the OpenHands application. Use `Additional Trusted CA Certificates` for a private CA or TLS-inspecting proxy, but every external OAuth and webhook provider that calls OpenHands must also trust that CA.

If certificates are not passed during installation, use the Admin Console certificate upload flow. Store local certificate and key files outside repositories with restrictive permissions and remove temporary copies after use.

## Runtime Routing

Subdomain routing in Simple mode requires wildcard coverage for `*.<base-domain>`. If wildcard certificates are unavailable, use the target release's supported path-based routing mode and provision the complete SAN set from its documentation.

## LLM Provider

Configure one working administrator-managed provider first. Current documented choices include Anthropic, OpenAI, Google, DeepSeek, Mistral AI, Azure, Groq, OpenRouter, AWS Bedrock, and custom/local LLMs. Use exact provider model identifiers; prefix custom OpenAI-compatible model names with `openai/`. Enable BYOK only when users should be allowed to add their own provider credentials.

For Bedrock, verify:

- AWS auth mode is correct: access key/secret or EC2 instance profile.
- Region has access to the chosen model.
- Model ID is the exact Bedrock or inference-profile ID exposed by AWS.
- LiteLLM model alias is visible through `/v1/models`.

For current Bedrock model IDs, query AWS rather than relying on stale notes:

```bash
aws bedrock list-foundation-models --region <region>
```

If OpenHands profiles use the internal proxy, model names should normally look like:

```text
litellm_proxy/<alias-or-bedrock-model-id>
```

and the base URL should be:

```text
http://openhands-litellm:4000
```

## Sandbox Settings

Current settings include:

- sandbox isolation and routing mode;
- idle time before an inactive conversation pauses;
- deletion time before a paused conversation and its storage are permanently deleted;
- persistent and ephemeral storage size per sandbox;
- memory and CPU requests and limits;
- warm runtime count;
- additional host path mounts in `host_path:container_path[:ro|rw]` form;
- optional `/dev/kvm` passthrough when the node exposes KVM.

Interpretation:

- The default stronger isolation requires Linux kernel 6.3 or newer and supports Docker-in-sandbox; standard isolation does not support Docker-in-sandbox.
- A single running session is capped at 12 hours even when it is active. It is then force-paused, and resuming starts a new 12-hour window.
- A longer deletion time helps users resume old conversations, but it keeps runtime storage around longer.
- A warm runtime can improve start latency, but it must match the environment needed by the conversation. If a warm runtime lacks required secrets/env vars, the request may cold-start anyway.
- Resource requests are scheduling reservations. Multiply per-sandbox requests by expected peak concurrent sandboxes and leave capacity for platform services.
- Host mounts and KVM expand sandbox access to host resources. Enable them only for a reviewed requirement.

## Default Organization

Decide whether the first signed-in user should create and own a default organization, whether later signed-in users should join it automatically, and whether personal workspaces should be hidden. These options are additive: disabling them later does not delete organizations, remove members, or delete hidden personal data.

## SMTP and Proxy

Configure SMTP only when budget alerts or administrator notifications are required. Match implicit SSL and STARTTLS to the mail server rather than enabling both by assumption.

When outbound traffic uses a corporate proxy, configure `HTTP_PROXY`, `HTTPS_PROXY`, and any additional `NO_PROXY` hosts through the Admin Console. Keep SSL verification enabled and add the proxy CA under `Additional Trusted CA Certificates` instead of disabling certificate verification.


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
