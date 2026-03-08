---
name: add-javadoc
description: Add comprehensive JavaDoc documentation to Java classes and methods. Use when documenting Java code, adding API documentation, or improving code documentation.
license: MIT
compatibility: Requires Java source files
triggers:
  - javadoc
  - java documentation
  - document java
---

Add comprehensive JavaDoc documentation to all public classes and methods.

## Class-Level Documentation

For each public class:
- Add class-level JavaDoc describing the purpose and responsibility of the class
- Include `@author` tag if appropriate

## Method-Level Documentation

For each public method:
- Add method-level JavaDoc describing what the method does
- Include `@param` tags for all parameters with clear descriptions
- Include `@return` tag describing the return value
- Include `@throws` tags for any checked exceptions

## Style Guidelines

- First sentence should be a concise summary
- Use HTML tags sparingly (prefer plain text)
- Document preconditions and postconditions when relevant
- Include code examples with `{@code ...}` for complex methods

See [references/example.md](references/example.md) for before/after examples.
