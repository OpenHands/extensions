---
name: migration-mapping
description: Create a mapping from source language files to target language files for code migrations. Use when evaluating or documenting a migration project.
license: MIT
compatibility: Requires completed migration with source and target code
triggers:
  - migration mapping
  - source target mapping
  - file mapping
---

Create a mapping from source language files (e.g., COBOL) to target language files (e.g., Java) to document which target files implement the functionality of each source file.

## Task

Examine all source language files and identify the corresponding target language files that implement the same functionality. This mapping is essential for:
- Migration quality evaluation
- Traceability documentation
- Gap analysis

## Output Format

Save the mapping as a JSON file with this structure:

```json
{
  "source_file_1.cbl": ["target_file_a.java", "target_file_b.java"],
  "source_file_2.cbl": ["target_file_c.java"],
  "source_file_3.cbl": []
}
```

## Rules

1. **Many-to-many mapping**: A source file may map to multiple target files, and a target file may implement logic from multiple source files
2. **Complete coverage**: EVERY source file must appear as a key in the mapping
3. **Complete target coverage**: EVERY target file should appear as a value at least once
4. **Empty arrays**: If a source file has no corresponding target implementation, use an empty array `[]`
5. **Incremental**: If a mapping file already exists, update it rather than replacing it

## How to Identify Mappings

Look for:
- Matching class/program names
- Similar function/paragraph names
- Matching business logic patterns
- Comments referencing source files
- Import/include statements
- Data structure similarities

## Example

For a COBOL-to-Java migration:

```json
{
  "CALC001.cbl": ["InvoiceCalculator.java", "TaxCalculator.java"],
  "CUST002.cbl": ["CustomerService.java", "CustomerRepository.java"],
  "UTIL003.cbl": ["StringUtils.java"],
  "SCREEN001.cbl": []
}
```

Note: `SCREEN001.cbl` maps to nothing because UI code was not migrated.

## Verification

After creating the mapping:
- [ ] Every source file is a key
- [ ] No duplicate keys
- [ ] Target files are relative paths from project root
- [ ] JSON is valid and well-formatted
