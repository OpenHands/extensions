# OpenHands / OpenClaw Demo Walkthrough

This is the shortest concrete demo you can run to prove the skill is teaching a
real read-first Provenote workflow instead of only describing one.

## Demo prompt

Use Provenote to inspect the current notes workspace. Start with
`draft.list`, `research_thread.list`, and `auditable_run.list`. Summarize what
already exists. Then pick one narrow next step:

- if there is a promising research thread, run `research_thread.to_draft`
- if there is an unverified draft, run `draft.verify`

Finally, explain which repo-owned artifact changed and how the user can inspect
it.

## Expected tool sequence

1. `draft.list`
2. `research_thread.list`
3. `auditable_run.list`
4. one of:
   - `research_thread.to_draft`
   - `draft.verify`

## Visible success criteria

- the agent reports what drafts, threads, or runs already exist
- the write action is narrow and tied to something that was just read
- the agent points back to an inspectable draft or auditable-run artifact

## What the output should look like

You do not need byte-for-byte identical JSON, but the shape should feel like
the tested MCP outputs:

```json
[
  {
    "id": "draft:1",
    "notebook_id": "notebook:1",
    "status": "completed"
  }
]
```

```json
{
  "status": "verified"
}
```

That is the level of concreteness the demo should reach: list something real,
then mutate one real thing, then point back to the changed artifact.

## OpenClaw variant

Use the same prompt after loading the MCP config from
[OPENCLAW_MCP_CONFIG.json](OPENCLAW_MCP_CONFIG.json). The success criteria stay
the same: read first, mutate once, then point back to the changed artifact.
