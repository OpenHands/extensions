# OpenHands / OpenClaw Demo Walkthrough

This is the shortest concrete demo you can run to prove the skill is doing real
work instead of just existing as prose.

## Demo prompt

Use Prompt Switchboard to compare this rewrite request across the ready ChatGPT
and Gemini tabs:

> Rewrite the following onboarding email so it sounds warmer and 30% shorter.

Start with `prompt_switchboard.bridge_status` and
`prompt_switchboard.check_readiness`. If both tabs are ready, run
`prompt_switchboard.compare`. After the compare turn lands, use
`prompt_switchboard.analyze_compare` to summarize the biggest wording
differences and recommend which answer is better for a friendly product update.

## Expected tool sequence

1. `prompt_switchboard.bridge_status`
2. `prompt_switchboard.check_readiness`
3. `prompt_switchboard.compare`
4. `prompt_switchboard.analyze_compare`

## Visible success criteria

- the agent names which tabs are ready instead of guessing
- the compare step creates a real turn/session artifact
- the analysis step refers back to the compare output instead of inventing text

## What the output should look like

You do not need byte-for-byte identical JSON, but the shape should feel like
this:

- readiness output names which models are ready or blocked
- compare output yields a session/turn pair the host can inspect later
- analysis output cites the compare turn instead of free-writing from memory

Example compare-oriented fields to expect:

```text
sessionId: session-1
turnId: turn-1
requestedModels: [ChatGPT, Gemini]
```

## OpenClaw variant

Use the same prompt after loading the MCP config from
[OPENCLAW_MCP_CONFIG.json](OPENCLAW_MCP_CONFIG.json). The success criteria stay
the same: bridge, readiness, compare, then analysis.
