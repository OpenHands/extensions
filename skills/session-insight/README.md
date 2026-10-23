# Session Insight

`/insight` creates a local, self-contained HTML report from OpenHands conversation or session exports. It summarizes recurring failures, repeated actions, and the exact local files supporting each finding without rendering message bodies or credential values.

The reporter accepts JSON and JSONL files directly and can scan documented `.openhands/conversations` and `.openhands/sessions` directories when present. Remote and cloud deployments should export their conversation data to a local file first.

No data is uploaded. The skill only proposes environment improvements and requires explicit confirmation before changing a skill, rule, or configuration file.
