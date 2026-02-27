---
name: migration-scoring
description: Evaluate code migration quality with coverage, correctness, and style scoring. Generates executive reports with actionable recommendations.
license: MIT
compatibility: Requires completed migration with source and target code, Python 3.13 with uv
triggers:
  - migration scoring
  - migration quality
  - migration evaluation
  - score migration
---

Comprehensive quality evaluation for code migration projects.

## Overview

This plugin evaluates completed migrations through multiple lenses:

1. **Mapping** — Document source-to-target file relationships
2. **Quality Scoring** — Measure coverage and correctness
3. **Style Scoring** — Evaluate code quality and conventions
4. **Reporting** — Generate executive summary with recommendations

## Prerequisites

- Completed migration with both source and target code present
- Python 3.13 with `uv`
- LLM API key (Anthropic or OpenAI)
- Optional: Custom style rubric file

## Quick Start

```bash
export LLM_API_KEY="your-api-key"
export LLM_MODEL="anthropic/claude-3-5-sonnet-20241022"

uv run python -m lc_sdk_examples.migration_scoring \
  --src-path /path/to/migration/project \
  --rubric-path /path/to/style_rubric.txt
```

## Workflow Phases

### Phase 1: Migration Mapping

See [skills/mapping/SKILL.md](skills/mapping/SKILL.md)

Creates a source→target file mapping:
- Identifies which target files implement each source file
- Supports many-to-many relationships
- Flags unmigrated source files

**Output:** `migration_mapping.json`

```json
{
  "CALC001.cbl": ["InvoiceCalculator.java", "TaxCalculator.java"],
  "CUST002.cbl": ["CustomerService.java"]
}
```

### Phase 2: Quality Scoring

See [skills/score-quality/SKILL.md](skills/score-quality/SKILL.md)

Scores each source file on:
- **Coverage (1-5)**: How much functionality was migrated
- **Correctness (1-5)**: How accurately behavior was preserved

**Output:** `migration_score.json`

```json
{
  "CALC001.cbl": {
    "coverage": 4,
    "correctness": 5,
    "justification": "All calculation logic migrated..."
  }
}
```

### Phase 3: Style Scoring

See [skills/score-style/SKILL.md](skills/score-style/SKILL.md)

Evaluates target code against style guidelines:
- Naming conventions
- Code organization
- Error handling
- Documentation
- Idiomaticity

**Output:** `style_score.json`

### Phase 4: Executive Report

See [skills/report/SKILL.md](skills/report/SKILL.md)

Generates a comprehensive report:
- Overall health assessment
- Score statistics and distribution
- Risk categorization (Green/Yellow/Red)
- Prioritized recommendations

**Output:** `final_report.md`

## Output Structure

```
your-project/
├── .lc-sdk/
│   ├── migration_mapping.json
│   ├── migration_score.json
│   ├── style_score.json
│   └── final_report.md
```

## Scoring Criteria

See [skills/score-quality/references/scoring-criteria.md](skills/score-quality/references/scoring-criteria.md) for the 1-5 scoring scales.

### Risk Categories

- **Green**: All scores ≥ 4
- **Yellow**: Any score 3-4
- **Red**: Any score < 3
