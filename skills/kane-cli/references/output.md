# Kane CLI output with `--agent`

With `--agent`, `kane-cli run` prints one JSON object per line on stdout. Ignore fields and event types you do not recognize, since new ones can be added.

## Events

- The first line is `{"type":"stream_start", ...}` with `cli_version` and `surface`.
- Progress events have `step`, `status` (`running`, then `done` or `failed`) and `remark` (what the agent did or why a step failed). They have no `type` field.
- Typed events have a `type` field, for example `warning`, `error`, `bifurcation`, `child_agent_start` and `child_agent_end`.
- The last event is `{"type":"run_end", ...}`. Stop reading when you see it.
- If the run could not start, for example when not signed in, there is no `run_end` event and the reason is on stderr.

```text
for each line:
  if obj.type == "run_end" -> final result, stop
  else if obj.type exists  -> typed event
  else if obj.step exists  -> progress event
```

## `run_end` fields

| Field | Meaning |
|-------|---------|
| `status` | `passed` or `failed` |
| `one_liner` | Short summary for display |
| `summary` | What the agent did |
| `reason` | Why the run stopped |
| `final_state` | Values stored by the objective ("store ... as 'name'") |
| `credits_consumed` | Credits the run used, when reported |
| `session_dir` | Session folder; the sealed `.evidence` pack is under `evidence/` |
| `test_url` | Link to the run in TestMu AI, when the upload succeeded |

The evidence path is printed on stderr, not as an event: `evidence: view locally with kane-cli evidence serve <path>`.

## Example: keep only the result

```bash
kane-cli run "Go to https://example.com and verify the page title is 'Example Domain'" \
  --agent --headless --timeout 120 > run.ndjson
code=$?
tail -n 1 run.ndjson
echo "exit code: $code"
```
