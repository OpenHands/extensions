# GitHub issue triage

Prioritize open issues and establish acceptance criteria before marking them ready for development.

Schedule this automation independently and select its agent profile. The profile
chooses the model, tools, and GitHub credential; the PAT needs Issues write access
only. Explicit issue dependencies must be completed before development starts.
The agent checks repository guidance and adjacent code, preserves the author's
issue description, and maintains accepted criteria in one clearly marked section
at the end of the issue body. This lets repository readiness checks evaluate the
same source that developers and reviewers use. When a material design decision
remains unclear after repository research, the agent leaves the body unchanged,
asks focused follow-up questions in a marked comment, and withholds the readiness
label.

See [SKILL.md](SKILL.md) for configuration and the catalog bundle for its files.
