# Facade Pattern

Use when an orchestrator coordinates too many subsystems, or when clients must interact with a complex subsystem through a simplified interface.

## When to Apply

- A class or method coordinates 5+ collaborators in a complex sequence
- Client code must call multiple subsystem classes in a specific order
- Subsystem complexity should be hidden behind a simplified API
- Multiple clients duplicate the same orchestration logic

## Structure

```
Client ---> Facade
              |
    +---------+---------+
    |         |         |
SubsystemA SubsystemB SubsystemC
```

## Before / After

### Java

```java
// BEFORE: client orchestrates everything
public class CheckoutController {
    public void checkout(Cart cart) {
        InventoryService inventory = new InventoryService();
        PricingEngine pricing = new PricingEngine();
        TaxCalculator tax = new TaxCalculator();
        PaymentProcessor payment = new PaymentProcessor();
        ShippingService shipping = new ShippingService();
        NotificationService notifications = new NotificationService();

        inventory.reserve(cart.getItems());
        double subtotal = pricing.calculate(cart);
        double taxAmount = tax.calculate(subtotal, cart.getAddress());
        double total = subtotal + taxAmount;
        payment.charge(cart.getPaymentMethod(), total);
        shipping.schedule(cart.getItems(), cart.getAddress());
        notifications.sendConfirmation(cart.getCustomer(), total);
    }
}

// AFTER: Facade hides orchestration
public class CheckoutFacade {
    private final InventoryService inventory;
    private final PricingEngine pricing;
    private final TaxCalculator tax;
    private final PaymentProcessor payment;
    private final ShippingService shipping;
    private final NotificationService notifications;

    // Constructor injection for all dependencies
    public CheckoutFacade(
            InventoryService inventory, PricingEngine pricing,
            TaxCalculator tax, PaymentProcessor payment,
            ShippingService shipping, NotificationService notifications) {
        this.inventory = inventory;
        this.pricing = pricing;
        this.tax = tax;
        this.payment = payment;
        this.shipping = shipping;
        this.notifications = notifications;
    }

    public void checkout(Cart cart) {
        inventory.reserve(cart.getItems());
        double total = calculateTotal(cart);
        payment.charge(cart.getPaymentMethod(), total);
        shipping.schedule(cart.getItems(), cart.getAddress());
        notifications.sendConfirmation(cart.getCustomer(), total);
    }

    private double calculateTotal(Cart cart) {
        double subtotal = pricing.calculate(cart);
        return subtotal + tax.calculate(subtotal, cart.getAddress());
    }
}
```

## Key Considerations

- The facade itself should be thin -- orchestration only, no business logic
- Each subsystem behind the facade should be independently testable
- Inject all subsystem dependencies via constructor (combine with DI)
- A facade with too many dependencies (>6-7) may indicate the orchestration itself needs decomposition
- Do not use facade to hide a god class -- extract the responsibilities first, then add facade if needed
