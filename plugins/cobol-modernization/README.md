# COBOL Modernization Plugin

End-to-end COBOL to Java migration workflow using OpenHands agents. This plugin orchestrates the complete modernization process from legacy COBOL codebases to modern Java applications, handling build setup, mainframe dependency removal, and code migration with test validation.

## Quick Start

```bash
export LLM_API_KEY="your-api-key"
export LLM_MODEL="anthropic/claude-3-5-sonnet-20241022"

uv run python -m lc_sdk_examples.cobol_modernization --src-path /path/to/cobol/project
```

## Features

- **Multi-Phase Migration** — Structured workflow from COBOL to Java in four phases
- **Build Environment Setup** — Configures both GnuCOBOL and Java compilation
- **Mainframe Independence** — Removes CICS/VSAM dependencies before migration
- **Test-Driven Migration** — Creates test fixtures from COBOL execution for Java validation
- **Idiomatic Java Output** — Produces proper Java conventions, not literal translations

## Prerequisites

- GnuCOBOL compiler (`cobc`)
- Java 11+ with Maven or Gradle
- Python 3.13 with `uv`
- LLM API key

## Plugin Contents

```
plugins/cobol-modernization/
├── README.md                              # This file
├── references/                            # Reference documentation
│   └── troubleshooting.md                 # Common issues and solutions
└── skills/                                # Workflow phase skills
    ├── build-setup/                       # Phase 1: Build environment
    │   └── SKILL.md
    ├── cobol-modernization-overview/      # Plugin overview
    │   └── SKILL.md
    ├── mainframe-planning/                # Phase 2: Transformation planning
    │   └── SKILL.md
    ├── mainfraime-removal/                # Phase 3: Mainframe dependency removal
    │   ├── SKILL.md
    │   └── references/
    │       └── cics-transformation-examples.md
    └── to-java-migration/                 # Phase 4: Java migration
        ├── SKILL.md
        └── references/
            ├── cobol-to-java-example.md
            └── datatype-mappings.md
```

## Workflow Phases

### Phase 1: Build Setup

Creates the foundation for the migration:

- COBOL compilation environment using GnuCOBOL
- Java project structure with Maven/Gradle and JUnit 5
- Test fixtures with golden outputs from COBOL execution

**Outputs:**
- `build_notes.md` — Build instructions
- `test-fixtures/` — Input/output test data
- `test_manifest.json` — Test case mapping

### Phase 2: Mainframe Planning

Creates a transformation guide without modifying code:

- Maps CICS/VSAM constructs to standard COBOL equivalents
- Documents error handling replacements
- Identifies UI operations to stub

**Output:** `mainframe_dependency_removal_plan.md`

### Phase 3: Mainframe Removal

Applies the transformation guide:

- Replaces `EXEC CICS` commands with file I/O
- Adds `FILE STATUS` checking
- Stubs BMS/screen operations

**Verification:**
- Code compiles with GnuCOBOL
- Runs with test fixtures

### Phase 4: Java Migration

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

## Usage

### Running the Migration

1. **Prepare your COBOL project**: Ensure all source files are accessible
2. **Set environment variables**:
   ```bash
   export LLM_API_KEY="your-api-key"
   export LLM_MODEL="anthropic/claude-3-5-sonnet-20241022"
   ```
3. **Run the migration**:
   ```bash
   uv run python -m lc_sdk_examples.cobol_modernization --src-path /path/to/cobol/project
   ```
4. **Review outputs**: Check generated Java code and run tests

### Phase-by-Phase Execution

You can also run individual phases by using the specific skill definitions:

- See [skills/build-setup/SKILL.md](skills/build-setup/SKILL.md) for build setup only
- See [skills/mainframe-planning/SKILL.md](skills/mainframe-planning/SKILL.md) for planning
- See [skills/mainfraime-removal/SKILL.md](skills/mainfraime-removal/SKILL.md) for mainframe removal
- See [skills/to-java-migration/SKILL.md](skills/to-java-migration/SKILL.md) for Java translation

## Troubleshooting

### GnuCOBOL Not Found

```bash
# Install on Debian/Ubuntu
sudo apt-get install gnucobol

# Install on macOS
brew install gnucobol
```

### COBOL Compilation Errors

1. Check that all copybooks are in the include path
2. Verify file encoding (COBOL often uses EBCDIC)
3. See [references/troubleshooting.md](references/troubleshooting.md) for common issues

### Java Tests Failing

1. Compare test outputs with golden outputs in `test-fixtures/`
2. Check for numeric precision differences (COBOL vs Java)
3. Verify date/time handling conversions

### Mainframe Dependencies Remaining

1. Review `mainframe_dependency_removal_plan.md`
2. Check for indirect CICS calls through subroutines
3. Verify all VSAM file accesses are converted

## Supported COBOL Features

- Standard COBOL-85 and COBOL-2002 syntax
- CICS command-level programs
- VSAM file operations
- Common mainframe utilities (SORT, IDCAMS)
- COPY/COPYBOOK statements
- Nested programs and subprograms

## Limitations

- Does not support assembler programs called from COBOL
- IMS/DB2 support is limited
- Screen handling (BMS) is stubbed, not fully migrated
- Some proprietary extensions may require manual intervention

## Related Resources

- **Blog Post**: [COBOL to Java Refactoring with OpenHands](https://openhands.dev/blog/20251218-cobol-to-java-refactoring) — Detailed walkthrough of the migration process

## Contributing

See the main [extensions repository](https://github.com/OpenHands/extensions) for contribution guidelines.

## License

This plugin is part of the OpenHands extensions repository. See [LICENSE](../../LICENSE) for details.
