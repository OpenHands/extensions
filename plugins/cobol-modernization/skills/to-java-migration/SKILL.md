---
name: to-java-migration
description: Migrate COBOL code to idiomatic Java, preserving business logic while following Java best practices. Use for COBOL modernization projects.
license: MIT
compatibility: Requires Java 11+, Maven or Gradle
triggers:
  - cobol to java
  - cobol migration
  - cobol modernization
  - migrate cobol
---

Migrate COBOL code to idiomatic Java, preserving all business logic.

## Code Style Requirements

Write idiomatic Java, NOT literal COBOL translations:
- Use Java conventions: camelCase names, standard collections (List, Map)
- Use Java standard library instead of rolling your own
- No god classes — split into cohesive, single-responsibility classes
- No TODO comments or stub implementations — fully implement everything

## Robustness Requirements

- Validate inputs at method entry (null checks, range validation)
- Use try-catch for all I/O and external operations
- Use try-with-resources for files, streams, connections
- Handle errors gracefully with meaningful messages

## Configuration Requirements

- No hardcoded file paths or credentials — use environment variables
- No magic numbers — use named constants
- Make limits and timeouts configurable

## Documentation Requirements

- Add COBOL references: `// COBOL equivalent: BNK1CRA.cbl 145-167`
- Document assumptions made during conversion
- Add Javadoc to public methods

## Testing Requirements

If test fixtures exist (see `cobol-build-setup` skill):
- Create a JUnit test class for each migrated program
- Load inputs from fixtures, assert output matches expected (golden) output
- All tests must pass before migration is complete

## References

- See [references/cobol-to-java-example.md](references/cobol-to-java-example.md) for a complete transformation example
- See [references/datatype-mappings.md](references/datatype-mappings.md) for COBOL→Java type mappings

## Done When

✓ Code compiles without errors
✓ All JUnit tests pass (Java output matches COBOL golden output)
✓ No TODO or stub implementations remain
✓ COBOL references documented in comments
