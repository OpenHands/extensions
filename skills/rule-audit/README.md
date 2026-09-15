# rule-audit

Static analyzer for AI system prompts — sentence splitting, modal-verb regexes,
and hand-curated keyword clusters. Runs locally, makes no network calls, calls
no model, and is deterministic. Think `bandit` or `semgrep`, but for prompts.

Source: https://github.com/hermes-labs-ai/rule-audit

Use this skill when a user asks to audit, lint, review, or check a named
system prompt / agent instruction file for internal conflicts (contradictions,
coverage gaps, priority ambiguities, meta-paradoxes, absoluteness issues).

See `SKILL.md` for the exact adapter invocation and scope/false-positive
guidance.
