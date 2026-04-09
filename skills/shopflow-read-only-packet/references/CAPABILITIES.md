# Shopflow MCP Capabilities

Shopflow exposes a read-only packet surface for integration and distribution
truth.

## Safe-first packets and tools

- `get_integration_surface`
- `get_runtime_seam`
- `get_submission_readiness`
- `get_public_distribution_bundle`

## Recommended first-use order

1. `get_integration_surface`
2. `get_submission_readiness`
3. `get_public_distribution_bundle`
4. `get_runtime_seam`

## Boundary

- good fit: packet review, submission readiness, runtime seam, and distribution
  truth
- not a fit: claiming live store listing, public HTTP transport, or hosted
  runtime
