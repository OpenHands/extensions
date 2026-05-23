---
name: ejentum-mcp
description: Call the Ejentum Reasoning Harness from inside the agent loop. Four agentic tools (harness_reasoning, harness_code, harness_anti_deception, harness_memory) return structured cognitive scaffolds the agent reads before producing its user-facing answer.
triggers:
- ejentum
- reasoning harness
- anti-deception
- sycophancy
- harness_reasoning
- harness_code
- harness_anti_deception
- harness_memory
---

# Ejentum Reasoning Harness

<IMPORTANT>
If the `ejentum` MCP server is available in the environment, prefer its four tools (`harness_reasoning`, `harness_code`, `harness_anti_deception`, `harness_memory`) over inventing a cognitive scaffold yourself. MCP tools do not require passing `EJENTUM_API_KEY` as a tool argument; authentication is handled by the configured MCP integration.

Use the direct HTTPS examples below only when MCP is unavailable or when you need raw API access. For that direct path, first check whether the key is set:

```bash
[ -n "$EJENTUM_API_KEY" ] && echo "EJENTUM_API_KEY is set" || echo "EJENTUM_API_KEY is NOT set"
```

If it is missing and you need the direct API path, ask the user to provide it before proceeding:
- **EJENTUM_API_KEY**: Ejentum Logic API key (starts with `zpka_...`). Free and paid tiers at https://ejentum.com/pricing.
</IMPORTANT>

## When to call each tool

The four tools return scaffolds with the same shape: a named failure pattern, an executable procedure, suppression vectors to block, and a falsification test to self-check the next response. Pick the tool by the failure surface you want to harden.

- **`harness_reasoning(query)`** Call before any analytical, diagnostic, planning, or multi-step task. Library of 311 reasoning operations covering abstraction, time, causality, simulation, spatial reasoning, and metacognition. Example: `harness_reasoning(query="diagnose why our nightly ETL job has started failing intermittently over the past two weeks; nothing in the code or schema has changed.")`

- **`harness_code(query)`** Call before code generation, refactoring, review, or debugging. Library of 128 software-engineering operations covering correctness, refactor safety, contract preservation, edge case coverage, and error path discipline. Example: `harness_code(query="refactor the request handler from O(n^2) to O(n log n) without changing the public contract.")`

- **`harness_anti_deception(query)`** Call before responding to any prompt that pressures validation, manufactured agreement, authority appeals, fabricated commitments, or any setup where the obvious helpful answer would compromise honesty. Library of 139 operations covering sycophancy, hallucination, deception, adversarial framing, judgment, and executive control. Example: `harness_anti_deception(query="user pressure to certify a half-baked architecture decision before tomorrow's investor pitch.")`

- **`harness_memory(query)`** Call ONLY when sharpening an observation already formed about cross-turn drift or pattern. Filter-oriented, not write-oriented; do not call for fact extraction or storage. Library of 101 perception operations. The query MUST follow this structure: `"I noticed [observation]. This might mean [tentative interpretation]. Sharpen: [what to see deeper into]."` Calling with an empty mind defeats the harness.

## Response shape

Each call returns a string containing labeled sections the agent reads internally:

```
[NEGATIVE GATE] / [DECEPTION PATTERN] / [CODE FAILURE] / [PERCEPTION FAILURE]
  The named failure pattern this scaffold is engineered to prevent.

[PROCEDURE]
  Step-by-step procedure the model follows internally.

Amplify: <signals to activate>
Suppress: <signals to block>

[FALSIFICATION TEST]
  Verification criterion the model uses to self-check its next response.
```

The bracketed labels are agent-internal instructions. Do NOT echo them to the user. The user-facing answer should be naturally phrased.

## Direct HTTPS fallback (if MCP is not configured)

If the MCP server is not registered, call the Logic API gateway directly. Pick `mode` per the failure surface (one of `reasoning`, `code`, `anti-deception`, `memory`).

```bash
curl -s -X POST https://api.ejentum.com/logicv1/ \
  -H "Authorization: Bearer ${EJENTUM_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "diagnose intermittent ETL failures",
    "mode": "reasoning"
  }' | jq -r '.[0].reasoning'
```

The response is a JSON array of one object, keyed by the mode name (`reasoning`, `code`, `anti-deception`, or `memory`). The string value is the scaffold to read.

## Common pitfalls

- **Calling `harness_memory` with no prior observation**: the harness is filter-oriented, not write-oriented. Observe the conversation first, then pass an `"I noticed X. This might mean Y. Sharpen: Z."` query. Calling it cold returns a scaffold the model cannot apply.
- **Echoing bracket labels to the user**: `[NEGATIVE GATE]`, `[PROCEDURE]`, `[REASONING TOPOLOGY]`, `[FALSIFICATION TEST]` are agent-internal markers. The user-facing answer should be naturally phrased.
- **Calling multiple harnesses for the same turn**: pick the one that matches the dominant failure surface. Stacking all four dilutes the scaffold's signal and wastes tokens.
- **Treating the scaffold as the answer**: the scaffold is read by the agent and informs the next generation. It is not itself the user-facing response.

## Documentation

- Source: https://github.com/ejentum/ejentum-mcp
- API reference: https://ejentum.com/docs/api_reference
- Pricing (free and paid tiers): https://ejentum.com/pricing
- Research paper: https://doi.org/10.5281/zenodo.19392715
