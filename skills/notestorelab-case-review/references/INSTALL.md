# Install And MCP Wiring

Use this reference when the agent or reviewer asks:

- how do I install this?
- what is the exact MCP command?
- what should I point my host at?

## Public package lane

The current shipped package lane is PyPI:

```bash
python -m pip install apple-notes-forensics==0.1.0.post1
```

If the host supports `uvx`, the shortest MCP launch path is:

```bash
uvx --from apple-notes-forensics==0.1.0.post1 \
  notes-recovery-mcp \
  --case-dir ./output/Notes_Forensics_<run_ts>
```
