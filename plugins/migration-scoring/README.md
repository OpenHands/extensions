# Migration Scoring Plugin

Quality evaluation for code migration projects using OpenHands agents. This plugin scores completed migrations across multiple dimensions including coverage, correctness, and code style, generating executive reports with actionable recommendations.

## Quick Start

```bash
export LLM_API_KEY="your-api-key"
export LLM_MODEL="anthropic/claude-3-5-sonnet-20241022"

uv run python -m lc_sdk_examples.migration_scoring \
  --src-path /path/to/migration/project \
  --rubric-path /path/to/style_rubric.txt
```

## Features

- **Multi-Dimensional Scoring** — Evaluates coverage, correctness, and style separately
- **Source-to-Target Mapping** — Documents relationships between source and migrated files
- **Executive Reporting** — Generates summary reports with risk categorization
- **Custom Style Rubrics** — Supports project-specific style guidelines
- **Actionable Recommendations** — Prioritized list of improvements

## Prerequisites

- Completed migration with both source and target code present
- Python 3.13 with `uv`
- LLM API key (Anthropic or OpenAI)
- Optional: Custom style rubric file

## Plugin Contents

```
plugins/migration-scoring/
├── README.md                              # This file
└── skills/                                # Workflow phase skills
    ├── migration-scoring-overview/        # Plugin overview
    │   └── SKILL.md
    ├── migration-mapping/                 # Phase 1: Source-to-target mapping
    │   └── SKILL.md
    ├── score-quality/                     # Phase 2: Coverage and correctness
    │   ├── SKILL.md
    │   └── references/
    │       └── scoring-criteria.md
    ├── score-style/                       # Phase 3: Code style evaluation
    │   └── SKILL.md
    └── migration-report/                  # Phase 4: Executive report
        └── SKILL.md
```

## Workflow Phases

### Phase 1: Migration Mapping

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

Evaluates target code against style guidelines:

- Naming conventions
- Code organization
- Error handling
- Documentation
- Idiomaticity

**Output:** `style_score.json`

### Phase 4: Executive Report

Generates a detailed report:

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

## Usage

### Running the Evaluation

1. **Ensure migration is complete**: Both source and target code should be present
2. **Set environment variables**:
   ```bash
   export LLM_API_KEY="your-api-key"
   export LLM_MODEL="anthropic/claude-3-5-sonnet-20241022"
   ```
3. **Run the scoring**:
   ```bash
   uv run python -m lc_sdk_examples.migration_scoring \
     --src-path /path/to/migration/project \
     --rubric-path /path/to/style_rubric.txt
   ```
4. **Review the report**: Check `final_report.md` for results and recommendations

### Using a Custom Style Rubric

Create a text file with your style guidelines:

```text
# Style Rubric for Java Migration

## Naming Conventions
- Use camelCase for methods and variables
- Use PascalCase for classes
- Avoid Hungarian notation

## Code Organization
- One public class per file
- Group related methods together
- Maximum 500 lines per class

## Error Handling
- Use specific exception types
- Include meaningful error messages
- Log exceptions appropriately
```

Then pass it using `--rubric-path`:

```bash
uv run python -m lc_sdk_examples.migration_scoring \
  --src-path /path/to/project \
  --rubric-path ./my_style_rubric.txt
```

## Scoring Criteria

### Coverage Score (1-5)

| Score | Description |
|-------|-------------|
| 5 | 100% of source functionality migrated |
| 4 | 90%+ migrated, minor features missing |
| 3 | 70-90% migrated, some features missing |
| 2 | 50-70% migrated, significant gaps |
| 1 | Less than 50% migrated |

### Correctness Score (1-5)

| Score | Description |
|-------|-------------|
| 5 | Behavior exactly matches source |
| 4 | Minor edge case differences |
| 3 | Some behavioral differences |
| 2 | Significant behavioral changes |
| 1 | Major functionality broken |

### Risk Categories

- **Green**: All scores ≥ 4 — Migration is production-ready
- **Yellow**: Any score 3-4 — Needs review before production
- **Red**: Any score < 3 — Significant work required

## Troubleshooting

### Mapping Not Found

1. Verify directory structure matches expected layout
2. Check file extensions are recognized
3. Ensure source and target directories are accessible

### Low Coverage Scores

1. Review unmigrated files in the mapping
2. Check for split functionality across multiple target files
3. Verify all helper/utility functions are included

### Style Score Issues

1. Check that rubric file is valid
2. Verify target code files are readable
3. Review specific style violations in `style_score.json`

### Report Generation Fails

1. Ensure all previous phases completed successfully
2. Check that score JSON files are valid
3. Verify sufficient disk space for output

## Integration with COBOL Modernization

This plugin works seamlessly with the [COBOL Modernization Plugin](../cobol-modernization/README.md):

```bash
# First, run the migration
uv run python -m lc_sdk_examples.cobol_modernization --src-path /path/to/cobol

# Then, score the results
uv run python -m lc_sdk_examples.migration_scoring --src-path /path/to/cobol
```

## Contributing

See the main [extensions repository](https://github.com/OpenHands/extensions) for contribution guidelines.

## License

This plugin is part of the OpenHands extensions repository. See [LICENSE](../../LICENSE) for details.
