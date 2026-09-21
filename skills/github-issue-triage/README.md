# GitHub issue triage

Prioritize open issues and establish acceptance criteria before marking them ready for development.

Schedule this automation independently and select its agent profile. The profile
chooses the model, tools, and GitHub credential; the PAT needs Issues write access
only. Explicit issue dependencies must be completed before development starts.
The agent checks repository guidance and adjacent code, replaces stale automated
triage output with one clearly marked comment, and applies `ready-for-dev` only
after the criteria cover the relevant behavior and validation boundaries. When a
material design decision remains unclear after repository research, it asks
focused follow-up questions and withholds the readiness label.

See [SKILL.md](SKILL.md) for configuration and the catalog bundle for its files.
