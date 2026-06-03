---
name: cobol-modernization
description: End-to-end COBOL to Java migration workflow. Handles build setup, mainframe dependency removal, and code migration with test validation.
license: MIT
compatibility: Requires GnuCOBOL, Java 11+, Maven/Gradle, Python 3.13 with uv
triggers:
  - cobol modernization
  - cobol to java
  - cobol migration
  - mainframe migration
---

End-to-end workflow for migrating COBOL codebases to Java.

## Overview

This plugin orchestrates a multi-phase COBOL modernization project:

1. **Build Setup** — Configure compilation for both COBOL and Java, create test fixtures
2. **Mainframe Planning** — Document transformations needed to remove mainframe dependencies
3. **Mainframe Removal** — Convert CICS/VSAM code to standard COBOL
4. **Java Migration** — Translate standardized COBOL to idiomatic Java

## Prerequisites

- GnuCOBOL compiler (`cobc`)
- Java 11+ with Maven or Gradle
- Python 3.13 with `uv`
- LLM API key (Anthropic or OpenAI)

## Quick Start

```bash
export LLM_API_KEY="your-api-key"
export LLM_MODEL="anthropic/claude-3-5-sonnet-20241022"

uv run python -m lc_sdk_examples.cobol_modernization --src-path /path/to/cobol/project
```

## Workflow Phases

### Phase 1: Build Setup

See [../build-setup/SKILL.md](../build-setup/SKILL.md)

Creates the foundation for the migration:
- COBOL compilation environment (GnuCOBOL)
- Java project structure (Maven/Gradle + JUnit 5)
- Test fixtures with golden outputs from COBOL execution

**Outputs:**
- `build_notes.md` — Build instructions
- `test-fixtures/` — Input/output test data
- `test_manifest.json` — Test case mapping

### Phase 2: Mainframe Planning

See [../mainframe-planning/SKILL.md](../mainframe-planning/SKILL.md)

Creates a transformation guide without modifying code:
- Maps CICS/VSAM constructs to standard COBOL equivalents
- Documents error handling replacements
- Identifies UI operations to stub

**Output:**
- `mainframe_dependency_removal_plan.md`

### Phase 3: Mainframe Removal

See [../mainfraime-removal/SKILL.md](../mainfraime-removal/SKILL.md)

Applies the transformation guide:
- Replaces EXEC CICS commands with file I/O
- Adds FILE STATUS checking
- Stubs BMS/screen operations

**Verification:**
- Code compiles with GnuCOBOL
- Runs with test fixtures

### Phase 4: Java Migration

See [../to-java-migration/SKILL.md](../to-java-migration/SKILL.md)

Translates to idiomatic Java:
- Proper Java conventions (not literal translations)
- JUnit tests using golden outputs
- COBOL references in comments

**Done when:**
- All code compiles
- All JUnit tests pass
- No TODOs or stubs remain

## Output Structure

```
your-project/
├── .lc-sdk/
│   ├── initial_batch_graph.json
│   ├── fixed_batch_graph.json
│   └── mainframe_dependency_removal_plan.md
├── test-fixtures/
│   ├── inputs/
│   └── expected_outputs/
├── test_manifest.json
├── src/main/java/
└── src/test/java/
```

## Troubleshooting

See [../../references/troubleshooting.md](../../references/troubleshooting.md) for common issues and solutions.
