# COBOL to Java Transformation Example

## COBOL (Before)

```cobol
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CALC-TAX.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01 WS-SUBTOTAL    PIC 9(7)V99.
       01 WS-TAX-RATE    PIC V999 VALUE 0.085.
       01 WS-TAX-AMOUNT  PIC 9(7)V99.

       PROCEDURE DIVISION.
           MULTIPLY WS-SUBTOTAL BY WS-TAX-RATE
               GIVING WS-TAX-AMOUNT.
           STOP RUN.
```

## Java (After)

```java
/**
 * Tax calculation service.
 * COBOL equivalent: CALC-TAX.cbl
 */
public class TaxCalculator {
    private static final BigDecimal DEFAULT_TAX_RATE = new BigDecimal("0.085");

    private final BigDecimal taxRate;

    public TaxCalculator() {
        this(DEFAULT_TAX_RATE);
    }

    public TaxCalculator(BigDecimal taxRate) {
        this.taxRate = Objects.requireNonNull(taxRate, "Tax rate cannot be null");
    }

    /**
     * Calculate tax for a given subtotal.
     * COBOL equivalent: CALC-TAX.cbl lines 10-12
     *
     * @param subtotal The pre-tax amount
     * @return The calculated tax amount
     * @throws IllegalArgumentException if subtotal is null or negative
     */
    public BigDecimal calculateTax(BigDecimal subtotal) {
        if (subtotal == null) {
            throw new IllegalArgumentException("Subtotal cannot be null");
        }
        if (subtotal.compareTo(BigDecimal.ZERO) < 0) {
            throw new IllegalArgumentException("Subtotal cannot be negative");
        }
        return subtotal.multiply(taxRate).setScale(2, RoundingMode.HALF_UP);
    }
}
```
