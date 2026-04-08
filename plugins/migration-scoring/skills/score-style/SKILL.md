---
name: score-style
description: Score migrated code against style guidelines and best practices. Evaluates code quality independent of functional correctness.
license: MIT
compatibility: Requires target code to evaluate
triggers:
  - style score
  - code quality score
  - style evaluation
---

Evaluate migrated code against style guidelines and best practices.

This skill scores code quality aspects that are independent of functional correctness — focusing on readability, maintainability, and adherence to conventions.

## Default Scoring Criteria

Unless a custom rubric is provided, score on these attributes (1-5 scale):

### Naming Conventions (1-5)
- 1: Inconsistent or meaningless names
- 3: Mostly follows conventions, some issues
- 5: Clear, consistent, idiomatic names

### Code Organization (1-5)
- 1: Monolithic, hard to navigate
- 3: Some structure, could be cleaner
- 5: Well-organized, logical structure

### Error Handling (1-5)
- 1: Missing or swallowed exceptions
- 3: Basic error handling present
- 5: Comprehensive, appropriate error handling

### Documentation (1-5)
- 1: No documentation
- 3: Some documentation, inconsistent
- 5: Thorough, helpful documentation

### Idiomaticity (1-5)
- 1: Non-idiomatic, smells like translated code
- 3: Mostly idiomatic, some foreign patterns
- 5: Fully idiomatic, natural code

## Output Format

Save scores as a JSON file:

```json
{
  "target_file_a.java": {
    "naming_conventions": 4,
    "code_organization": 3,
    "error_handling": 5,
    "documentation": 4,
    "idiomaticity": 4,
    "justification": "Good naming and error handling. Some methods could be extracted for better organization."
  }
}
```

## Custom Rubric

If a custom rubric is provided, use its attributes and scoring criteria instead of the defaults. The rubric should define:
- Attribute names
- Score meanings for each level (1-5)
- Examples of good/bad code for each attribute

## Evaluation Guidelines

### What to Look For

**Positive indicators:**
- Consistent naming (camelCase for Java, snake_case for Python)
- Appropriate class/method sizes
- Single responsibility principle followed
- Meaningful comments (not obvious ones)
- Standard library usage over custom implementations
- Defensive programming practices

**Negative indicators:**
- Literal translations (COBOL-style Java)
- God classes or methods
- Magic numbers
- Excessive comments or no comments
- Reinvented wheels
- Swallowed exceptions
- Hardcoded values

### Language-Specific Considerations

**Java:**
- Streams vs. for loops (both acceptable, but be consistent)
- Optional vs. null checks
- Record types for data classes
- Builder pattern for complex objects

**Python:**
- Type hints
- List comprehensions
- Context managers
- Pythonic idioms

## Incremental Scoring

If a score file already exists, update it with new scores rather than replacing it entirely.
