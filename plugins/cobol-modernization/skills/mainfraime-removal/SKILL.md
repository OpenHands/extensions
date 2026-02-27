---
name: mainframe-removal
description: Apply mainframe dependency transformations to COBOL code using a pre-generated transformation guide. Converts CICS/VSAM constructs to standard COBOL.
license: MIT
compatibility: Requires GnuCOBOL (cobc) for verification
triggers:
  - remove mainframe
  - cobol transformation
  - cics removal
  - standard cobol
---

Apply the transformations from a transformation guide to convert mainframe-specific COBOL to standard COBOL.

**Prerequisite**: A transformation guide must exist (see `cobol-mainframe-planning` skill).

## Transformation Requirements

### Data Operations

- Replace each CICS/VSAM construct with its standard COBOL equivalent per the plan
- Add FILE STATUS checks after EVERY file operation:
  - Check for success (00) before proceeding
  - Handle "not found" (23) distinctly from I/O errors (3x)
  - Handle "file not exists" (35) at OPEN time
- Add explicit CLOSE statements in all code paths (including error paths)

### UI/Terminal Operations (BMS maps, SEND/RECEIVE)

- Replace with simple stubs or ACCEPT/DISPLAY statements
- Do NOT spend time replicating screen layouts
- Focus on preserving data flow, not UI fidelity

### Error Handling

- Replace CICS RESP/RESP2 checks with equivalent FILE STATUS logic
- Replace HANDLE CONDITION with explicit status checking after operations
- Ensure error paths don't leave files open

See [references/cics-transformation-examples.md](references/cics-transformation-examples.md) for before/after code examples.

## Verification

After transformation:
- Code MUST compile without errors
- Test with valid input → should execute core business logic
- Test with missing/invalid files → should fail gracefully, not crash

## Preserve

- All original business logic
- Data transformations and calculations
- Validation rules

## Checklist

- [ ] All EXEC CICS commands replaced
- [ ] FILE STATUS declared for all files
- [ ] FILE STATUS checked after every I/O operation
- [ ] CLOSE statements in all code paths
- [ ] Code compiles successfully
- [ ] Basic test execution passes
