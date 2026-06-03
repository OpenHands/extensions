---
name: mainframe-planning
description: Create a transformation guide for replacing mainframe-specific COBOL constructs with standard COBOL equivalents. Use when preparing COBOL code for local execution or migration.
license: MIT
compatibility: Requires knowledge of CICS/VSAM mainframe constructs
triggers:
  - mainframe planning
  - cics replacement
  - cobol transformation guide
  - mainframe dependency
---

Create a comprehensive transformation guide that maps each mainframe dependency to its standard COBOL replacement.

This guide is a prerequisite for the actual transformation — DO NOT modify any code, only create the guide.

## Output Format

Document each mainframe-specific construct with:

1. **Pattern**: The mainframe construct (e.g., `EXEC CICS READ FILE(...)`)
2. **Replacement**: The standard COBOL equivalent
3. **Error Handling**: How to replicate the mainframe's error behavior
   - Map CICS RESP/RESP2 codes to FILE STATUS equivalents
   - Specify which FILE STATUS values to check (e.g., 00=success, 23=not found, 35=file not exists)
4. **Resource Cleanup**: Any cleanup the replacement requires (CICS auto-manages resources; file I/O does not)
5. **Edge Cases**: Behavior differences between mainframe and standard COBOL

## Constructs to Address

### Data Operations (CICS/IMS/VSAM)

- READ, WRITE, REWRITE, DELETE operations
- STARTBR, READNEXT, READPREV (browse operations)
- CICS error handling: HANDLE CONDITION, RESP/RESP2 options
- VSAM → sequential or indexed file I/O

### UI/Terminal Operations (BMS maps, screens)

- SEND MAP, RECEIVE MAP → these can be MOCKED or stubbed
- Screen I/O is not needed for business logic validation
- Document how to replace with simple ACCEPT/DISPLAY or test harness stubs
- Focus on preserving the data flow, not the UI interaction

### Other Mainframe Constructs

- Mainframe data types (COMP-3 packed decimal, etc.)
- JCL-embedded constructs
- IMS calls (if present)

## Critical Requirements

- Every CICS command that can fail MUST have an error handling replacement documented
- UI operations should be clearly marked as "mock/stub" so the agent doesn't get stuck on them
- Prefer: file-based I/O over mainframe I/O, standard data types over mainframe types

## Common Mappings Reference

### FILE STATUS Codes

| Code | Meaning | CICS Equivalent |
|------|---------|-----------------|
| 00 | Success | Normal completion |
| 23 | Record not found | NOTFND condition |
| 35 | File does not exist | NOTOPEN condition |
| 22 | Duplicate key | DUPREC condition |
| 3x | I/O errors | Various IOERR conditions |

### CICS to Standard COBOL

| CICS Command | Standard COBOL |
|--------------|----------------|
| `EXEC CICS READ FILE(...)` | `READ filename INTO...` |
| `EXEC CICS WRITE FILE(...)` | `WRITE record-name FROM...` |
| `EXEC CICS REWRITE FILE(...)` | `REWRITE record-name FROM...` |
| `EXEC CICS DELETE FILE(...)` | `DELETE filename RECORD` |
| `EXEC CICS STARTBR FILE(...)` | `START filename KEY...` |
| `EXEC CICS READNEXT FILE(...)` | `READ filename NEXT INTO...` |
