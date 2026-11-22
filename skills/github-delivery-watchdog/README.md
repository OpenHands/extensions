# GitHub delivery watchdog

Periodically check pull requests and merge only current heads with independent review, tests, and passing CI.

Run this independently from issue triage, implementation, and review. Configure
a repository-scoped fine-grained PAT by its saved secret name. The watchdog uses
Actions and commit statuses and sends a conditional merge request for the exact
accepted head. It does not create an agent or change application code.

See [SKILL.md](SKILL.md) for permissions, acceptance gates, and configuration.
