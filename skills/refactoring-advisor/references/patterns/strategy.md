# Strategy Pattern

Use when conditional behavior selection (long if/else chains, switches by type) indicates the Switch Statements smell or when algorithms need to be interchangeable.

## When to Apply

- Same switch/if-else on a type code appears in multiple places
- Adding a new variant requires modifying existing code (violates Open/Closed)
- Algorithm selection is determined at runtime
- Different behaviors share the same interface but differ in implementation

## Structure

```
Context ---> Strategy (interface)
                |
        +-------+-------+
        |       |       |
    StrategyA StrategyB StrategyC
```

## Before / After

### Java

```java
// BEFORE: switch on type
public class ShippingCalculator {
    public double calculate(Order order) {
        switch (order.getShippingType()) {
            case STANDARD:
                return order.getWeight() * 1.5;
            case EXPRESS:
                return order.getWeight() * 3.0 + 5.0;
            case OVERNIGHT:
                return order.getWeight() * 5.0 + 15.0;
            default:
                throw new IllegalArgumentException("Unknown type");
        }
    }
}

// AFTER: Strategy pattern
public interface ShippingStrategy {
    double calculate(Order order);
}

public class StandardShipping implements ShippingStrategy {
    public double calculate(Order order) { return order.getWeight() * 1.5; }
}

public class ExpressShipping implements ShippingStrategy {
    public double calculate(Order order) { return order.getWeight() * 3.0 + 5.0; }
}

public class ShippingCalculator {
    private final ShippingStrategy strategy;

    public ShippingCalculator(ShippingStrategy strategy) {
        this.strategy = strategy;  // injected!
    }

    public double calculate(Order order) {
        return strategy.calculate(order);
    }
}
```

### Python

```python
# BEFORE: if/elif chain
def calculate_discount(customer_type: str, total: float) -> float:
    if customer_type == "premium":
        return total * 0.2
    elif customer_type == "business":
        return total * 0.15
    elif customer_type == "regular":
        return total * 0.05
    else:
        return 0

# AFTER: Strategy via Protocol (or callable)
from typing import Protocol

class DiscountStrategy(Protocol):
    def calculate(self, total: float) -> float: ...

class PremiumDiscount:
    def calculate(self, total: float) -> float:
        return total * 0.2

class BusinessDiscount:
    def calculate(self, total: float) -> float:
        return total * 0.15

# Or simply use functions (more Pythonic for simple strategies):
DISCOUNT_STRATEGIES = {
    "premium": lambda total: total * 0.2,
    "business": lambda total: total * 0.15,
    "regular": lambda total: total * 0.05,
}
```

### TypeScript

```typescript
// BEFORE: switch statement
function formatOutput(data: Data, format: string): string {
    switch (format) {
        case "json": return JSON.stringify(data);
        case "csv": return convertToCsv(data);
        case "xml": return convertToXml(data);
        default: throw new Error(`Unknown format: ${format}`);
    }
}

// AFTER: Strategy via interface
interface OutputFormatter {
    format(data: Data): string;
}

class JsonFormatter implements OutputFormatter {
    format(data: Data): string { return JSON.stringify(data); }
}

class CsvFormatter implements OutputFormatter {
    format(data: Data): string { return convertToCsv(data); }
}

// Usage with DI
class ReportService {
    constructor(private readonly formatter: OutputFormatter) {}

    generateReport(data: Data): string {
        return this.formatter.format(data);
    }
}
```

## Combination with DI

Strategy pattern pairs naturally with dependency injection:
1. Define the strategy interface
2. Implement concrete strategies
3. Inject the appropriate strategy via constructor
4. Register strategy selection in DI container or factory

This eliminates both the switch statement AND the hardcoded dependency.
