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

The skill starts read-only. Infrastructure changes, installer execution, ConfigValues merges, deployments, provider application creation, DNS changes, restores, and cutovers require explicit approval for the exact operation.

Installer download URLs, license files, private keys, provider credentials, ConfigValues, and support bundles are treated as sensitive. The bundled YAML asset records only non-secret scope and validation status; it is not a headless deployment configuration.

## Current scope

This draft implements the PRD-137 first milestone: comprehensive preflight, provider setup guidance, guided ClickOps, post-install verification, and customer-ready IT requests.

Fresh installations use `Simple` hostname mode. In the AWS Terraform module, the matching value is `hostname_mode = "wildcard"`; Legacy is reserved for reproducing an existing Legacy installation.

A fully headless install remains conditional on a documented, release-specific installer schema and supported secret-input mechanism. The skill does not infer or invent those interfaces.

## Primary triggers

- `install OpenHands Enterprise`
- `set up OHE on a VM`
- `run an OHE install preflight`
- `configure the Replicated Admin Console`
- `prepare DNS and TLS for OpenHands Enterprise`
- `validate a Replicated Embedded Cluster installation`

## Official references

- [OpenHands Enterprise quick start](https://docs.openhands.dev/enterprise/quick-start)
- [Admin Console configuration](https://docs.openhands.dev/enterprise/vm-install/admin-console-configuration)
- [Replicated Embedded Cluster installation](https://docs.replicated.com/enterprise/installing-embedded)
- [Replicated Embedded Cluster requirements](https://docs.replicated.com/enterprise/installing-embedded-requirements)
