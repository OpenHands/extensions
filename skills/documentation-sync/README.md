# Documentation Sync Skill

Check that documentation stays in sync with code changes during PR review.

## Usage

Trigger the skill with `/documentation-sync` or `/docs-sync` to review documentation alignment with code changes.

## What It Checks

- **README files** - Root and subdirectory READMEs describing changed functionality
- **API documentation** - Docstrings, JSDoc/TSDoc for modified public APIs
- **Configuration docs** - Documentation for new options, environment variables
- **CLI help text** - Usage information for command changes
- **OpenAPI/Swagger specs** - API contract documentation
- **Changelogs** - CHANGELOG.md, HISTORY.md entries

## Example

```
/documentation-sync

Review this PR and check that documentation reflects the code changes.
```

The skill will identify documentation gaps and suggest specific edits with priority labels.
