# Switchyard MCP Capabilities

Switchyard exposes a read-only MCP surface for runtime diagnostics and catalog
truth.

## Safe-first tools

- `switchyard.runtime.health`
- `switchyard.providers.list`
- `switchyard.provider.status`
- `switchyard.provider.probe`
- `switchyard.provider.support_bundle`
- `switchyard.catalog.surface_catalog`
- `switchyard.catalog.compat_target_catalog`
- `switchyard.catalog.builder_kit_catalog`
- `switchyard.catalog.skill_pack_catalog`
- `switchyard.catalog.host_playbook`

## Recommended first-use order

1. `switchyard.runtime.health`
2. `switchyard.providers.list`
3. `switchyard.provider.status`
4. `switchyard.provider.support_bundle`
5. `switchyard.catalog.host_playbook`

## Boundary

- good fit: runtime health, provider diagnostics, starter-pack routing, and
  read-only catalog inspection
- not a fit: runtime invoke, acquisition write, browser automation, or full
  host parity claims
