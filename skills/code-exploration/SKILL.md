---
name: code-exploration
description: Navigate and understand unfamiliar codebases to locate relevant code. Use when you need to find files, methods, or classes related to a bug or feature, search for error messages, or understand code structure before making changes.
---

# Code Exploration

Systematically explore a codebase to find relevant files and understand the code structure.

## Finding Related Files

Use targeted search strategies to locate relevant code:

### 1. Grep for Keywords

Search for relevant identifiers:
```bash
grep -r "method_name" .
grep -r "ClassName" .
grep -r "error message text" .
```

**Search for:**
- Method names mentioned in the issue
- Class names
- Error messages
- Keywords from the problem description
- File names or paths mentioned

### 2. Identify All Related Files

Create a comprehensive list:
- Files containing the methods/classes mentioned
- Test files for those components
- Configuration files that might affect behavior
- Documentation files explaining the feature

### 3. Analyze Code Structure

For each relevant file:
- Read the implementation
- Understand dependencies and imports
- Note related methods and classes
- Identify potential fix locations

## Proposing Fix Locations

### 1. List Candidate Locations

Propose specific files and methods where the fix might belong:
- Primary location (most likely)
- Secondary locations (less likely but possible)
- Related areas that might need updates

### 2. Explain Your Reasoning

For each candidate location:
- Why this location is relevant
- What code would need to change
- How it connects to the issue
- Potential side effects

### 3. Select the Most Likely Location

Based on your analysis, choose the primary fix location and explain why it's the best choice.

## Best Practices

- Use `grep` with appropriate flags (`-r` for recursive, `-i` for case-insensitive)
- Search the entire codebase, not just obvious locations
- Look at test files to understand expected behavior
- Check recent commits that touched related code (`git log --follow <file>`)
- Consider both direct and indirect relationships
