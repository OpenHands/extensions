# /modernize-cobol

Analyze and modernize COBOL programs.

## Usage

```
/modernize-cobol <file.cbl>
/analyze-cobol <file.cbl>
/cobol-to-java <file.cbl>
```

## Examples

```
/analyze-cobol PAYROLL.cbl
```
Analyzes the program and generates documentation.

```
/cobol-to-java PAYROLL.cbl
```
Converts the COBOL program to equivalent Java code.

```
/modernize-cobol --extract-rules BILLING.cbl
```
Extracts and documents all business rules from the program.
