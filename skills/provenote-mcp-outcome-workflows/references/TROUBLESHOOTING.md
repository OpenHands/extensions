# Provenote Troubleshooting

Use this page when the packet looks correct but the first real read-first
workflow still does not succeed.

## 1. The MCP server does not launch

Check these first:

- the local clone exists and the install steps from `INSTALL.md` finished
- the host config points at the right command, args, and working directory
- the environment has the expected dependencies available for `provenote-mcp`

If launch still fails, report it as a local install or config problem instead
of claiming the packet is attach-ready.

## 2. `draft.list`, `research_thread.list`, or `auditable_run.list` returns nothing

An empty result is not automatically a bug. Confirm:

- whether the workspace is actually populated yet
- whether the user expected a fresh workspace or an existing notebook
- whether the host is pointing at the intended notebook or data root

If the workspace is empty, say so clearly and stop after the read-first pass.

## 3. The first narrow mutation fails

Stay narrow and retry in this order:

1. rerun the three read-first list calls
2. pick exactly one target artifact
3. retry only one mutation such as `research_thread.to_draft` or `draft.verify`
4. if it still fails, report the exact artifact id and the failing step

Do not widen into multiple writes just to make the demo look busier.

## 4. The reviewer asks what success looks like

Point back to `DEMO.md` and verify these signals:

- the agent lists real drafts, research threads, or auditable runs
- the write action is tied to something that was just read
- the agent names which repo-owned artifact changed

## 5. Boundary reminder

This packet teaches a local, first-party Provenote MCP workflow. It does not
claim a hosted SaaS, a live marketplace listing, or a universal always-ready
workspace.
