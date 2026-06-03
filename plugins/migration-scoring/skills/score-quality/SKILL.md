---
name: score-quality
description: Score code migration quality based on coverage and correctness. Evaluates how well target code represents source functionality.
license: MIT
compatibility: Requires completed migration with source and target code
triggers:
  - migration quality
  - migration score
  - coverage score
  - correctness score
---

Evaluate migration quality by scoring coverage and correctness for each source-target file pair.

**Prerequisite**: A migration mapping file must exist (see `migration-mapping` skill).

See [references/scoring-criteria.md](references/scoring-criteria.md) for the 1-5 scoring scales.

## Output Format

Save scores as a JSON file:

```json
{
  "source_file_1.cbl": {
    "coverage": 4,
    "correctness": 5,
    "justification": "All calculation logic migrated. Tax rounding matches COBOL behavior."
  }
}
```

## Evaluation Process

For each source file and its mapped target files:

1. **Identify key functionality** in the source
   - Business logic, data operations, control flow, error handling

2. **Check coverage** in the target
   - Is each function/paragraph represented?
   - Are all data fields and code paths covered?

3. **Verify correctness**
   - Do calculations produce the same results?
   - Are edge cases handled the same way?

4. **Document justification**
   - Specific functionality present/missing
   - Known discrepancies

## Incremental Scoring

If a score file already exists, update it with new scores rather than replacing it entirely.
