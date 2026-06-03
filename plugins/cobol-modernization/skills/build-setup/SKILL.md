---
name: build-setup
description: Set up build environment and test fixtures for COBOL-to-Java migrations. Creates compilation infrastructure for both languages and generates golden test data.
license: MIT
compatibility: Requires GnuCOBOL (cobc), Java 11+, Maven or Gradle
triggers:
  - cobol build
  - cobol test fixtures
  - migration build setup
  - gnucobol
---

Set up a build environment and create test fixtures for validating COBOL-to-Java migrations.

To install GnuCOBOL, run: `./scripts/install-gnucobol.sh`

## Phase 1: Build Setup

### COBOL Build

- Find a way to compile and run the COBOL code (e.g., GnuCOBOL)
- Verify at least one program compiles and executes
- Note any dependencies or setup required

### Java Build

- Initialize a Java project alongside the COBOL code (Maven or Gradle)
- Set up standard directory structure: `src/main/java`, `src/test/java`
- Include JUnit 5 as a test dependency
- Verify the project builds (even if empty)

## Phase 2: Test Fixture Generation

For each major COBOL program:

### Create Synthetic Test Inputs

- Save to: `test-fixtures/inputs/{PROGRAM_NAME}/`
- Create 3-5 test cases per program covering:
  - Normal/happy path (valid, typical data)
  - Edge cases (empty input, maximum values, boundary conditions)
  - Error cases (invalid formats, missing required fields)

### Generate Golden Outputs

- Run each COBOL program with each test input
- Save COBOL output to: `test-fixtures/expected_outputs/{PROGRAM_NAME}/`
- These become the "golden" outputs that Java must match

### Create Test Manifest

Save to `test_manifest.json`:

```json
{
  "PROGRAM1": {
    "description": "Brief description of what this program does",
    "test_cases": [
      {
        "name": "normal_invoice",
        "input": "inputs/PROGRAM1/test_001.dat",
        "expected": "expected_outputs/PROGRAM1/test_001.out",
        "description": "Happy path"
      }
    ]
  }
}
```

## Deliverables

1. **build_notes.md** — Build instructions for COBOL and Java
2. **test-fixtures/** — Directory with `inputs/` and `expected_outputs/`
3. **test_manifest.json** — JSON manifest of all test cases

## Priority

Focus on programs with core business logic (transactions, calculations, data processing). UI-heavy programs (menu screens, reports) are lower priority.
