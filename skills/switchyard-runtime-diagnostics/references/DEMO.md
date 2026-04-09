# Switchyard MCP First-Success Demo

This is the shortest diagnostic loop that proves the packet is real.

## Demo prompt

Use Switchyard to diagnose whether one provider is actually ready. Start with
`switchyard.runtime.health`, list the available providers, then inspect one
provider with `switchyard.provider.status` and
`switchyard.provider.support_bundle`. Finish by telling me whether the next
blocker is internal or external.

## Expected tool sequence

1. `switchyard.runtime.health`
2. `switchyard.providers.list`
3. `switchyard.provider.status`
4. `switchyard.provider.support_bundle`

## Visible success criteria

- the MCP server launches from the provided config
- the runtime health call returns a real response
- the provider status and support bundle point to a concrete blocker
- the answer stays read-only and truthful
