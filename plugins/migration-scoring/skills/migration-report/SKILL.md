---
name: migration-report
description: Generate a comprehensive migration report summarizing quality scores and providing recommendations. Use after scoring a migration project.
license: MIT
compatibility: Requires migration_score.json and style_score.json files
triggers:
  - migration report
  - migration summary
  - quality report
---

Generate a comprehensive migration report that summarizes scores and provides actionable insights.

**Prerequisites**: Migration quality scores and style scores must exist (see `migration-score-quality` and `migration-score-style` skills).

## Report Structure

### 1. Executive Summary

- Overall migration health (High/Medium/Low confidence)
- Key statistics: total files, average scores, score distribution
- One-paragraph assessment for stakeholders

### 2. Score Overview

#### Coverage Statistics
- Average coverage score
- Files with coverage < 3 (needs attention)
- Files with coverage = 5 (complete)

#### Correctness Statistics
- Average correctness score
- Files with correctness < 3 (needs attention)
- Files with correctness = 5 (verified)

#### Style Statistics
- Average style score per attribute
- Common style issues identified

### 3. Risk Assessment

Categorize files into:
- **Green**: Coverage ≥ 4, Correctness ≥ 4, Style ≥ 4
- **Yellow**: Any score between 3-4
- **Red**: Any score < 3

### 4. Notable Findings

#### Strengths
- What was migrated well
- Good patterns to replicate

#### Weaknesses
- Common issues across files
- Patterns to avoid

### 5. Recommendations

Prioritized action items:
1. **Critical** — Files with scores < 3
2. **Important** — Files with scores 3-4
3. **Nice to have** — Style improvements for green files

### 6. Detailed Scores

Include the raw scores for reference (or link to score files).

## Output Format

Generate the report as a Markdown file:

```markdown
# Migration Quality Report

**Generated**: 2024-01-15
**Project**: Customer Management System
**Source**: COBOL (45 files)
**Target**: Java (62 files)

## Executive Summary

Migration is at **MEDIUM confidence** with average coverage of 4.2/5 and 
correctness of 4.0/5. Three files require immediate attention due to 
incomplete business logic migration.

## Score Overview

### Coverage
- Average: 4.2/5
- Complete (5): 28 files (62%)
- Needs attention (<3): 3 files (7%)

...
```

## Tone and Audience

- Write for technical stakeholders (architects, tech leads)
- Be specific about issues (cite file names, line numbers if relevant)
- Provide actionable recommendations, not vague suggestions
- Acknowledge good work, not just problems

## Data Sources

Read scores from:
- `migration_score.json` — Coverage and correctness scores
- `style_score.json` — Style evaluation scores
- `migration_mapping.json` — File mapping (for counts)

## Example Recommendations

**Good:**
> "CALC001.java has coverage 2/5 because batch processing logic in 
> CALC001.cbl lines 150-200 was not migrated. Implement the 
> `processBatch()` method to match COBOL paragraph PROCESS-BATCH."

**Bad:**
> "Some files need more work."
