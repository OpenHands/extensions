# NoteStore Lab MCP Capabilities

This packet expects the local MCP surface to expose a bounded case-review lane.

## Read-mostly review surfaces

- `list_case_roots`
- `inspect_case_manifest`
- `select_case_evidence`
- `inspect_case_artifact`
- `ask_case`

## Bounded workflows

- `run_verify`
- `run_report`
- `build_timeline`
- `public_safe_export`

## Best default order

1. list or choose one explicit case root
2. inspect the manifest
3. inspect derived artifacts
4. ask one bounded question
5. export only when the operator needs a shareable bundle
