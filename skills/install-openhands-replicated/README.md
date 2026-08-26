# Install OpenHands Enterprise on Replicated

Guide a customer or field engineer through a supported OpenHands Enterprise VM installation delivered with Replicated Embedded Cluster.

## Use this skill for

- scoping AWS Terraform or manual VM installations;
- checking host resources, ports, DNS, TLS, outbound access, and LLM endpoints;
- preparing GitHub, GitLab, Bitbucket Data Center, or Azure DevOps authentication;
- guiding version-specific installer and Admin Console steps;
- validating login, LLM routing, conversations, repository access, integrations, and storage;
- drafting DNS, firewall, certificate, infrastructure, and access requests for IT teams.

## Safety model

> **Keep failed-install investigations read-only.** Do not change Kubernetes resources unless directed by OpenHands Support. Ad hoc `kubectl` changes can be overwritten during a deployment or upgrade and may leave the installation in an inconsistent state.

The skill starts with read-only planning and preflights. Infrastructure changes, installer execution, Admin Console saves, deployments, provider application creation, DNS changes, restores, and cutovers require explicit approval for the exact operation. KOTS ConfigValues changes require a version-matched OpenHands Support procedure in addition to administrator approval.

Installer download URLs, license files, private keys, provider credentials, ConfigValues, and support bundles are treated as sensitive. The bundled YAML asset records only non-secret scope and validation status; it is not a headless deployment configuration.

## Current scope

The skill covers sizing by peak concurrent sandboxes, host and network preflight, provider setup guidance, guided Admin Console configuration, post-install verification, and customer-ready IT requests.

Fresh installations use `Simple` hostname mode. In the AWS Terraform module, the matching default is `hostname_mode = "wildcard"`; Legacy is reserved for reproducing an existing Legacy installation. Ubuntu 24.04 LTS is recommended, and the default stronger sandbox isolation requires Linux kernel 6.3 or newer.

A fully headless install remains conditional on a documented, release-specific installer schema and supported secret-input mechanism. The skill does not infer or invent those interfaces.

## Primary triggers

- `install OpenHands Enterprise`
- `set up OHE on a VM`
- `run an OHE install preflight`
- `configure the Replicated Admin Console`
- `prepare DNS and TLS for OpenHands Enterprise`
- `validate a Replicated Embedded Cluster installation`

## Official references

- [OpenHands Enterprise Quick Start](https://docs.openhands.dev/enterprise/quick-start)
- [OpenHands Enterprise Sizing Guide](https://docs.openhands.dev/enterprise/sizing-guide)
- [Admin Console Configuration](https://docs.openhands.dev/enterprise/vm-install/admin-console-configuration)
- [Conversations and Sandboxes](https://docs.openhands.dev/enterprise/conversations-and-sandboxes)
- [Docker in the Agent Sandbox](https://docs.openhands.dev/enterprise/docker-in-sandbox)
- [Troubleshooting](https://docs.openhands.dev/enterprise/troubleshooting)
- [VM Log Collection](https://docs.openhands.dev/enterprise/vm-install/log-collection)
- [Replicated Embedded Cluster installation](https://docs.replicated.com/enterprise/installing-embedded)
- [Replicated Embedded Cluster requirements](https://docs.replicated.com/enterprise/installing-embedded-requirements)
