# Operator Request Templates

Use these templates to request prerequisites without asking recipients to send credentials in email or chat. Replace placeholders and remove sections that do not apply.

## DNS and TLS Request

```text
Subject: DNS and TLS prerequisites for OpenHands Enterprise

Please create a wildcard DNS record for *.<base-domain> that resolves to <target IP or load balancer>.

The default Simple hostname layout uses:
- admin.<base-domain>
- app.<base-domain>
- auth.<base-domain>
- analytics.<base-domain>
- llm-proxy.<base-domain>
- runtime-api.<base-domain>
- <id>-runtime.<base-domain>

Please provide a publicly trusted wildcard certificate for *.<base-domain>, including the complete intermediate chain. Store the certificate and matching private key in the approved secret-transfer system; do not send the private key by email or chat.

Owner for DNS validation: <name/team>
Owner for certificate transfer: <name/team>
Required by: <date/time/timezone>
```

## Firewall and Proxy Request

```text
Subject: Network prerequisites for OpenHands Enterprise VM

Target VM or security group: <identifier>

Allow inbound TCP:
- 80
- 443
- 30000, restricted to approved administrator CIDRs where possible

Keep these local TCP ports available on the VM before installation:
- 2379
- 7443
- 9099
- 10248
- 10257
- 10259

Allow outbound HTTPS to the destinations listed in the current OpenHands Enterprise quick start, including Replicated control-plane endpoints, OpenHands image/chart/update endpoints, GitHub, Traefik charts, Docker Hub, and GHCR.

If TLS inspection or an HTTP proxy is required, provide the proxy URL and CA certificate through the approved configuration channel. Do not disable TLS verification.

Owner for validation: <name/team>
Required by: <date/time/timezone>
```

## Infrastructure Request

```text
Subject: VM prerequisites for OpenHands Enterprise

Expected peak concurrent sandboxes: <count>
Sandbox isolation: <approved-mode>
Docker-in-sandbox required: <yes-or-no>
Sizing Guide reviewed on: <date>

Please provide a dedicated Linux x86-64 VM that meets the attached approved sizing plan and current OpenHands Enterprise host requirements:
- vCPUs: <approved-count>
- memory: <approved-GiB>
- boot disk: <approved-GiB>
- separate expandable data disk: <approved-GiB>
- data mount path: <approved-path>
- storage latency/IOPS/throughput: <approved-values>
- operating system and kernel: <approved-values-for-isolation-mode>
- systemd
- root or sudo access for the installation operator

Please identify:
- VM hostname and environment
- cloud region or datacenter
- operating system and kernel version
- boot disk and data disk sizes
- storage class/type and provisioned IOPS/throughput
- data-volume growth owner
- administrator access method
- backup/snapshot owner

Do not include passwords, SSH private keys, or cloud credentials in the response.
```

## Access and Ownership Request

```text
Subject: Administrative access needed for OpenHands Enterprise setup

Please identify an authorized owner for each required surface:
- OpenHands installer dashboard and license
- VM sudo access
- DNS
- TLS certificate transfer
- LLM provider
- Git provider application
- optional Slack/Jira/Bitbucket/Azure DevOps administration
- database and backup operations

Use approved secret-management and transfer systems for all credentials. The installation record will contain only owner names, resource identifiers, and validation results.
```
