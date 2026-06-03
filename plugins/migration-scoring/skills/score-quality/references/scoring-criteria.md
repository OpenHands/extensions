# Migration Quality Scoring Criteria

## Coverage Scale (1-5)

| Score | Description |
|-------|-------------|
| 1 | Very low coverage — most functionality missing |
| 2 | Low coverage — significant functionality missing |
| 3 | Moderate coverage — some functionality missing |
| 4 | High coverage — minor functionality missing |
| 5 | Very high coverage — all functionality present |

## Correctness Scale (1-5)

| Score | Description |
|-------|-------------|
| 1 | Very low correctness — many inaccuracies |
| 2 | Low correctness — significant inaccuracies |
| 3 | Moderate correctness — some inaccuracies |
| 4 | High correctness — minor inaccuracies |
| 5 | Very high correctness — accurate representation |

## Common Issues to Flag

- Missing error handling
- Hardcoded values that were configurable
- Lost precision in numeric conversions
- Missing validation rules
- Incomplete data transformations
- UI logic that wasn't migrated (acceptable if documented)
