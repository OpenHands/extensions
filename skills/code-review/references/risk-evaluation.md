# Risk and Safety Evaluation

Assess the overall risk level of the PR and classify it as one of:
- 🟢 **Low Risk** — Safe for autonomous merge. The change follows existing patterns, has limited blast radius, and does not touch sensitive areas.
- 🟡 **Medium Risk** — Merge with caution. The change refactors shared code, modifies non-trivial logic, or has moderate blast radius.
- 🔴 **High Risk** — Needs human reviewer attention. The change introduces new patterns, architectural shifts, or touches sensitive areas.

## Risk Factors

Evaluate risk based on these factors:
- **Pattern conformance**: Does the change follow existing code patterns and conventions, or does it introduce new patterns or architectural shifts?
- **Security sensitivity**: Does it touch authentication, authorization, cryptography, secrets handling, or permission logic?
- **Infrastructure dependencies**: Does it introduce new external services, databases, message queues, or third-party integrations?
- **Blast radius**: Is the change isolated to a single module, or does it affect widely imported shared code, public APIs, or core system behavior?
- **Core system impact**: Does it modify agent orchestration, LLM prompt construction, data pipeline logic, or other foundational system behavior?

## Escalation Guidance

When risk is 🔴 **High**:
- State clearly why the PR is flagged as high-risk.
- Identify what specific aspects need human judgment (e.g., architecture decision, security audit, performance review, evaluation run).
- Recommend **not auto-merging** and request human reviewer or architect attention.

When risk is 🟡 **Medium**:
- Note the risk factors that elevate it above low-risk.
- Suggest specific areas a reviewer should focus on.

## Repo-Specific Risk Rules

If the repository defines custom risk criteria in its `AGENTS.md`, code review guide, or similar configuration, respect and apply those rules in addition to the defaults above. For example, a repo may designate certain directories (e.g., `src/core/`) or file patterns as always high-risk.

## Output Format

Always include the Risk and Safety Evaluation as the final section of your review, even when no other issues are found. Use this format:

```
[Overall PR] ⚠️ Risk Assessment: 🟢 LOW / 🟡 MEDIUM / 🔴 HIGH
Brief explanation of the risk classification and key factors considered.
If HIGH: **Recommendation**: Do not auto-merge. Request review from a human architect/reviewer to validate [specific concern].
```
