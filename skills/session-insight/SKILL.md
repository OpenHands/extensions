---
name: session-insight
description: This skill should be used when the user asks for "/insight", a local usage report, session analytics, recurring failure analysis, workflow bottlenecks, or suggestions based on OpenHands conversation history.
triggers:
- /insight
---

# Session Insight

Generate an evidence-based, local-only report from saved OpenHands conversation data.

## Safety rules

- Read only conversation/session exports. Never inspect authentication, secret, token, key, cookie, or environment files.
- Keep all processing local. Do not upload session content or paste it into a network service.
- Report only patterns supported by counts and source filenames. Do not invent findings when input is absent or sparse.
- Never change skills, rules, configuration, or other user files without explicit confirmation after presenting the report.

## Supported inputs

The bundled reporter reads UTF-8 JSON and JSONL files. A JSON file may contain a list of events, a single event, or an object containing nested event/message/action arrays. A JSONL file contains one JSON value per line.

Search these local directories when they exist:

1. `<project>/.openhands/conversations/`
2. `<project>/.openhands/sessions/`
3. `~/.openhands/conversations/`
4. `~/.openhands/sessions/`

These locations are discovery candidates, not a promise that every OpenHands deployment persists history there. Agent Canvas and remote/cloud backends may keep history behind their API instead of local files. In that case, ask the user to export conversation data to a local JSON or JSONL file, then pass that file explicitly with `--input`. Do not search unrelated directories.

## Generate the report

Run from the installed skill directory, or replace `$SKILL_DIR` with its absolute path:

```bash
python3 "$SKILL_DIR/scripts/generate_insight_report.py" \
  --input .openhands/conversations \
  --output .openhands/usage-data/insight-report.html
```

Repeat `--input` for multiple files or directories. Without `--input`, the script checks only the four discovery candidates above. It recursively includes `.json` and `.jsonl` files while excluding credential-like filenames.

The command prints a machine-readable summary and writes one self-contained HTML file. If no supported session records are found, it exits with status 2, prints a plain explanation, and does not create a report.

## Review the evidence

1. Open `.openhands/usage-data/insight-report.html` locally.
2. Verify each finding against its evidence table: input files, record count, repeated action/tool names, and recurring failure categories.
3. Explain limitations, including malformed files, unknown schemas, and small samples.
4. Derive at most three concrete suggestions from the measured patterns. Examples:
   - repeated use of the same tool sequence -> propose a focused skill;
   - recurring command or validation failures -> propose a repository rule or preflight check;
   - repeated manual setup actions -> propose a documented configuration default.
5. Ask which single suggestion, if any, the user wants implemented. State the exact files that would change and wait for confirmation.

Do not treat a high count alone as proof of wasted work. Distinguish repeated successful actions from repeated failures, and preserve source references so the user can audit every conclusion.
