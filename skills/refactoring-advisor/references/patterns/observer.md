# Observer / Events Pattern

Use when side-effect chains and notification coupling indicate tight coupling between a publisher and its consumers, or when Shotgun Surgery smell arises from adding new reactions to existing events.

## When to Apply

- A method triggers multiple side effects (send email, update cache, log audit, notify webhook)
- Adding a new reaction requires modifying the source class
- Multiple classes need to respond to the same event
- Side effects are tangled into core business logic
- Circular dependencies arise from bidirectional notification needs

## Structure

```
Publisher ---> Event / Message
                  |
        +---------+---------+
        |         |         |
   ListenerA  ListenerB  ListenerC
```

## Before / After

### Java (Spring Events)

```java
// BEFORE: direct coupling to all side effects
public class OrderService {
    private final InventoryService inventory;
    private final EmailService email;
    private final AnalyticsService analytics;
    private final AuditLogger auditLogger;

    public void placeOrder(Order order) {
        orderRepo.save(order);
        inventory.decrementStock(order.getItems());
        email.sendConfirmation(order);
        analytics.trackPurchase(order);
        auditLogger.log("ORDER_PLACED", order.getId());
    }
}

// AFTER: event-based decoupling
public class OrderService {
    private final OrderRepository orderRepo;
    private final ApplicationEventPublisher events;

    public OrderService(OrderRepository orderRepo, ApplicationEventPublisher events) {
        this.orderRepo = orderRepo;
        this.events = events;
    }

    public void placeOrder(Order order) {
        orderRepo.save(order);
        events.publishEvent(new OrderPlacedEvent(order));
    }
}

// Listeners are independent, can be added without modifying OrderService
@Component
public class InventoryListener {
    @EventListener
    public void onOrderPlaced(OrderPlacedEvent event) {
        inventoryService.decrementStock(event.getOrder().getItems());
    }
}

@Component
public class OrderConfirmationEmailListener {
    @EventListener
    public void onOrderPlaced(OrderPlacedEvent event) {
        emailService.sendConfirmation(event.getOrder());
    }
}
```

### Python

```python
# AFTER: simple event bus
from dataclasses import dataclass
from typing import Callable

@dataclass
class OrderPlacedEvent:
    order: Order

class EventBus:
    def __init__(self):
        self._handlers: dict[type, list[Callable]] = {}

    def subscribe(self, event_type: type, handler: Callable):
        self._handlers.setdefault(event_type, []).append(handler)

    def publish(self, event):
        for handler in self._handlers.get(type(event), []):
            handler(event)

class OrderService:
    def __init__(self, repo: OrderRepository, events: EventBus):
        self.repo = repo
        self.events = events

    def place_order(self, order: Order):
        self.repo.save(order)
        self.events.publish(OrderPlacedEvent(order=order))
```

## Key Considerations

- Events decouple the publisher from consumers -- new listeners don't require source changes
- Use for side effects only; don't use events for core business flow (makes debugging harder)
- Event objects should be immutable data carriers
- Consider async events for non-critical side effects (email, analytics)
- Combine with DI: inject the event bus/publisher via constructor
- Useful for breaking circular dependencies: A publishes, B listens, no direct A->B dependency
