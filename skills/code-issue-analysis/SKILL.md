---
name: code-issue-analysis
description: Analyze bug reports and feature requests to understand code issues. Use when starting work on a bug fix or feature implementation to parse issue descriptions, identify technical details, extract requirements, and clarify the problem statement. Essential first step before making code changes.
---

# Code Issue Analysis

Systematically analyze bug reports and feature requests to extract actionable requirements and technical details.

## Reading and Clarifying the Problem

When presented with an issue description, follow this structured analysis:

### 1. Extract Code and Config Snippets

If the issue contains code or configuration examples:
- Identify coding conventions and best practices demonstrated
- Note file structures and naming patterns
- Recognize configuration patterns and standards

### 2. Identify Technical Details

Highlight and document:
- **Error messages**: Exact text of exceptions, warnings, or error output
- **Method names**: Functions, classes, or methods mentioned
- **Variable names**: Specific identifiers referenced
- **File names**: Paths and filenames involved
- **Stack traces**: Full stack trace information if provided
- **Technical keywords**: Domain-specific terminology

### 3. Clarify the Problem Statement

Rewrite the issue in clear, unambiguous terms:
- What is the current behavior?
- What is the expected behavior?
- What is the gap between them?
- Under what conditions does the issue occur?

### 4. Extract Reproduction Steps

Document the sequence to reproduce the issue:
1. Preconditions (environment, data, configuration)
2. Actions to take
3. Expected outcome
4. Actual outcome

If reproduction steps aren't explicit, infer them from the description.

### 5. Identify Testing and Fix Considerations

Note any best practices mentioned for:
- How to test the issue
- Requirements for a valid fix
- Backward compatibility needs
- Edge cases to consider
- Performance implications

## Output

Produce a clear analysis containing:
- **Problem summary**: One-paragraph clear statement
- **Technical details**: Bulleted list of methods, files, errors
- **Reproduction steps**: Numbered sequence
- **Testing requirements**: Constraints and considerations for validation
