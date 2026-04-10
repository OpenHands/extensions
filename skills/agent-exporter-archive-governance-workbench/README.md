# agent-exporter Archive Governance Workbench

This skill helps OpenHands attach the local `agent-exporter` stdio bridge from a repo checkout and use the archive, retrieval, and governance workflow without pretending there is a hosted platform.

## What this skill does

- attaches the local stdio bridge
- publishes a local archive shell for a workspace
- runs semantic or hybrid retrieval and saves local reports
- reads governance evidence, policy packs, and baseline history

## Product truth

- `agent-exporter` is a local-first archive and governance workbench
- the current primary surface is still `CLI-first`
- this OpenHands skill is a secondary public lane, not the flagship packet
- the bridge exposes read-mostly archive, retrieval, and governance tools
- browser pages organize proof; they do not execute retrieval

## First-success path

1. Wire the local stdio bridge from a repo checkout.
2. Call `integration_evidence_policy_list` first.
3. If the workspace already has transcript HTML receipts, call `publish_archive_index` on that workspace.
4. Move to retrieval or evidence comparison only after the bridge works.

## Good fit

- local archive workspaces
- transcript browsing and report workflows
- governance evidence and baseline review
- hosts that can launch a local stdio server

## Must not claim

- no hosted archive platform
- no listed-live status for this skill without fresh host read-back
- no full-CLI MCP parity
- no change to the flagship `CLI-first` product story

## Public proof links

- Landing: https://xiaojiou176-open.github.io/agent-exporter/
- Archive shell proof: https://xiaojiou176-open.github.io/agent-exporter/archive-shell-proof.html
- Repo map: https://xiaojiou176-open.github.io/agent-exporter/repo-map/
- Releases: https://github.com/xiaojiou176-open/agent-exporter/releases
