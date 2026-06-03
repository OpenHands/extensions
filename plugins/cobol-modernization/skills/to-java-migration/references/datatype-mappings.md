# COBOL to Java Data Type Mappings

| COBOL | Java | Notes |
|-------|------|-------|
| `PIC 9(n)V99` | `BigDecimal` | Decimal with implied decimal point |
| `PIC X(n)` | `String` | Alphanumeric |
| `PIC 9(n)` | `int` or `long` | Use `long` for n > 9 |
| `COMP-3` (packed decimal) | `BigDecimal` | Preserve precision |
| `OCCURS n TIMES` | `List<T>` or array | Prefer `List` for flexibility |

## Control Flow Mappings

| COBOL | Java |
|-------|------|
| `PERFORM` | method call |
| `EVALUATE/WHEN` | `switch` |
| `IF/ELSE` | `if/else` |
| `PERFORM UNTIL` | `while` loop |
| `PERFORM VARYING` | `for` loop |
