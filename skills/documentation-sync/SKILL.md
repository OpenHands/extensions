---
name: documentation-sync
description: Check that documentation stays in sync with code changes during PR review. Identifies relevant docs (README, API docs, guides, comments), detects drift from code changes, and suggests specific edits. Use alongside /codereview when PRs modify behavior that should be reflected in documentation.
triggers:
- /documentation-sync
- /docs-sync
---

# Documentation Sync Review

Ensure documentation stays accurate when code changes. This skill supplements code review by checking that relevant documentation reflects the PR's changes.

## Workflow

### 1. Identify Documentation Sources

Scan the repository for documentation that may need updates:

**Primary targets:**
- `README.md`, `README.rst` (root and subdirectories)
- `docs/` directory (guides, tutorials, API references)
- `CHANGELOG.md`, `HISTORY.md`
- Inline docstrings and JSDoc/TSDoc comments in changed files
- `CONTRIBUTING.md`, `DEVELOPMENT.md`
- OpenAPI/Swagger specs (`openapi.yaml`, `swagger.json`)
- Man pages, CLI `--help` text

**Secondary targets:**
- Wiki links referenced in code
- Example files in `examples/` that demonstrate changed functionality
- Configuration file comments

### 2. Analyze Code Changes

For each changed file in the PR diff, identify:

1. **Public API changes**: New/modified/removed functions, classes, methods, CLI commands
2. **Configuration changes**: New env vars, config options, feature flags
3. **Behavioral changes**: Modified defaults, changed error messages, new validation rules
4. **Dependency changes**: Added/removed/updated packages that affect usage

### 3. Cross-Reference Documentation

For each identified change, check if corresponding documentation exists and is accurate:

| Change Type | Documentation to Check |
|-------------|----------------------|
| New function/method | Docstring present? API docs updated? |
| Changed function signature | Docstring params match? Examples still valid? |
| New CLI command/flag | README usage section? Man page? `--help` text? |
| New config option | Configuration docs? Environment variable list? |
| Changed default value | Docs mention old default? Examples affected? |
| Removed functionality | Deprecation noted? Migration guide needed? |
| New dependency | Installation docs updated? Requirements listed? |

### 4. Generate Feedback

For each documentation gap found, provide actionable feedback:

**Format:**
```
[path/to/doc.md, Section: "Installation"] 📄 Documentation: The PR adds a new `--verbose` flag to the CLI, but the usage section doesn't mention it.

Suggested addition after line 45:
> ### Verbose Mode
> Use `--verbose` or `-v` to enable detailed output:
> ```bash
> mycli process --verbose input.txt
> ```
```

## Priority Labels for Documentation Issues

| Label | When to Use |
|-------|-------------|
| 🔴 **Critical** | Public API undocumented, breaking change not noted, security-relevant behavior undocumented |
| 🟠 **Important** | New feature missing from README, CLI help text outdated, example code broken |
| 🟡 **Suggestion** | Docstring could be clearer, example could be added, typo in existing docs |
| 🟢 **Nit** | Minor wording improvements, formatting suggestions |

## What NOT to Flag

- Documentation style preferences (leave to doc linters)
- Docs for internal/private APIs unless they're already documented
- Missing docs for trivial changes (typo fixes, refactors with no behavior change)
- Comprehensive documentation rewrites for small changes

## Example Review Comment

```
🟠 Important: This PR adds a `timeout` parameter to `fetch_data()` but the docstring 
wasn't updated.

The function signature changed from:
  def fetch_data(url: str) -> dict:
to:
  def fetch_data(url: str, timeout: int = 30) -> dict:

Suggested docstring update:
```suggestion
def fetch_data(url: str, timeout: int = 30) -> dict:
    """Fetch data from the given URL.
    
    Args:
        url: The endpoint to fetch from.
        timeout: Request timeout in seconds. Defaults to 30.
    
    Returns:
        The parsed JSON response as a dictionary.
    """
```
```

## Integration with PR Review

When used with `/codereview`, focus on documentation gaps that complement the code review:

1. Code review catches bugs and style issues
2. Documentation sync catches docs/code drift

Keep documentation feedback in a separate section or clearly labeled so authors can address code and docs issues independently.
