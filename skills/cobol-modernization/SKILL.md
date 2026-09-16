---
name: cobol-modernization
description: Understand, document, and modernize legacy COBOL systems. Analyzes COBOL code, extracts business logic, generates documentation, and assists with migration to modern languages.
triggers:
- /modernize-cobol
- /cobol-to-java
- /analyze-cobol
---

# COBOL Modernization

Understand and modernize legacy COBOL systems while preserving critical business logic.

## Process

1. **Analyze**: Parse COBOL code structure, copybooks, and data divisions
2. **Document**: Generate documentation for undocumented programs
3. **Extract logic**: Identify and document business rules
4. **Plan migration**: Create modernization roadmap
5. **Transform**: Convert to modern languages when ready

## Analysis Capabilities

### Code Structure
- Program divisions (IDENTIFICATION, ENVIRONMENT, DATA, PROCEDURE)
- Paragraph and section organization
- PERFORM and GO TO flow analysis
- Copybook dependencies

### Data Analysis
- File descriptions (FD) and record layouts
- Working storage analysis
- Data flow through programs
- Implicit data transformations

### Business Logic
- Conditional logic extraction
- Calculation rules
- Validation rules
- Reporting logic

## Documentation Generation

Generate comprehensive documentation including:
- Program overview and purpose
- Input/output file descriptions
- Data dictionary from copybooks
- Business rule catalog
- Call graphs and dependencies
- Flowcharts for complex logic

## Migration Paths

### COBOL to Java
- Map COBOL data types to Java classes
- Convert PERFORM loops to methods
- Handle decimal arithmetic (BigDecimal)
- Preserve file I/O semantics

### COBOL to Python
- Simplify data structures
- Convert to modern file handling
- Maintain calculation precision

### Incremental Modernization
- Wrap COBOL in API layer
- Strangler fig pattern
- Gradual replacement of modules

## Example Usage

```
/analyze-cobol

Analyze PAYROLL.cbl and its copybooks:
- Document the program structure
- Extract all business rules
- Identify dependencies
- Create data dictionary
```

```
/cobol-to-java PAYROLL.cbl

Convert the payroll calculation module to Java:
- Preserve all business logic
- Create equivalent data classes
- Add unit tests for validation
```

## Best Practices

- Always validate transformations against original behavior
- Preserve comments and documentation
- Maintain audit trail of changes
- Test with production-like data
- Involve domain experts in validation
