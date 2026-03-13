---
name: code-implementation
description: Implement code changes with focus and discipline. Use when making the actual code edits to fix a bug or implement a feature. Emphasizes minimal changes, focused modifications, and clean implementation.
---

# Code Implementation

Implement code changes with precision and minimal scope.

## Principles

### 1. Minimal Changes

Make the smallest possible change that fixes the issue:
- Don't refactor unrelated code
- Don't fix other bugs you notice
- Don't add extra features
- Focus solely on the issue at hand

### 2. Focused Modifications

Edit only the files necessary for the fix:
- Primary fix location
- Related code that must change to support the fix
- Tests (if required by project)

### 3. Clean Implementation

Write code that matches the project's style:
- Follow existing code conventions
- Match indentation and formatting
- Use similar patterns to surrounding code
- Add comments only where needed

## Implementation Process

### 1. Open the Target File

Navigate to the exact location identified in your analysis:
```bash
# View the file first
cat -n path/to/file.py

# Then edit
# Use your file editing tools
```

### 2. Make the Change

Implement the fix according to your plan:
- Follow the solution approach from fix analysis
- Make surgical edits to the specific lines
- Don't modify more than necessary

### 3. Verify Syntax

Check that your changes are syntactically correct:
- For Python: `python -m py_compile file.py`
- For other languages: use appropriate syntax checkers
- Ensure no import errors or typos

## Example

**Before:**
```python
def parse_date(date_string):
    return datetime.strptime(date_string, "%m/%d/%Y")
```

**After (minimal fix):**
```python
def parse_date(date_string):
    try:
        return datetime.strptime(date_string, "%m/%d/%Y")
    except ValueError:
        return datetime.fromisoformat(date_string)
```

## What NOT to Do

- ❌ Don't refactor unrelated code "while you're at it"
- ❌ Don't fix additional bugs you notice
- ❌ Don't add extra error handling beyond what's needed
- ❌ Don't change formatting of untouched code
- ❌ Don't add features not mentioned in the issue
