# Dependency Injection Patterns

DI is the default decoupling technique. Always evaluate DI applicability first for every coupling-related finding.

## Core Principle

Classes should receive their collaborators, not create them. This makes dependencies explicit, enables testing with substitutes, and allows runtime flexibility.

## When DI Is Appropriate

- A class creates its own collaborators via `new` / direct instantiation
- Testing requires replacing real dependencies with test doubles
- Multiple implementations of the same contract exist or are anticipated
- A class is tightly coupled to infrastructure (database, HTTP, filesystem)
- A singleton or global is accessed from business logic
- A static service call hides a dependency

## When DI Is Not Appropriate

- The dependency is a pure utility with no side effects (string formatting, math)
- The coupling is within a single value object or entity's internal logic
- The overhead of abstraction exceeds the benefit (simple scripts, glue code)
- The language idiom favors a different approach (Python module-level functions for stateless operations)
- The "dependency" is a data structure, not a service

## Constructor Injection (Recommended Default)

Dependencies provided through the constructor -- explicit, required, immutable.

### Java (Spring)

```java
// BEFORE: tight coupling
public class OrderService {
    private final PaymentGateway gateway = new StripeGateway();
    private final OrderRepository repo = new JpaOrderRepository();
    private final EmailSender emailSender = new SmtpEmailSender();

    public void processOrder(Order order) {
        gateway.charge(order.getTotal());
        repo.save(order);
        emailSender.send(order.getConfirmation());
    }
}

// AFTER: constructor injection
public class OrderService {
    private final PaymentGateway gateway;
    private final OrderRepository repo;
    private final EmailSender emailSender;

    public OrderService(PaymentGateway gateway, OrderRepository repo, EmailSender emailSender) {
        this.gateway = gateway;
        this.repo = repo;
        this.emailSender = emailSender;
    }

    public void processOrder(Order order) {
        gateway.charge(order.getTotal());
        repo.save(order);
        emailSender.send(order.getConfirmation());
    }
}

// Registration
@Configuration
public class AppConfig {
    @Bean
    public PaymentGateway paymentGateway() { return new StripeGateway(); }
    @Bean
    public OrderRepository orderRepository() { return new JpaOrderRepository(); }
}
```

### Python

```python
# BEFORE: tight coupling
class OrderService:
    def __init__(self):
        self.gateway = StripeGateway()
        self.repo = SqlOrderRepository()

    def process_order(self, order):
        self.gateway.charge(order.total)
        self.repo.save(order)

# AFTER: constructor injection with protocols
from typing import Protocol

class PaymentGateway(Protocol):
    def charge(self, amount: Decimal) -> None: ...

class OrderRepository(Protocol):
    def save(self, order: Order) -> None: ...

class OrderService:
    def __init__(self, gateway: PaymentGateway, repo: OrderRepository):
        self.gateway = gateway
        self.repo = repo

    def process_order(self, order):
        self.gateway.charge(order.total)
        self.repo.save(order)
```

### TypeScript

```typescript
// BEFORE: tight coupling
class OrderService {
    private gateway = new StripeGateway();
    private repo = new SqlOrderRepository();

    async processOrder(order: Order): Promise<void> {
        await this.gateway.charge(order.total);
        await this.repo.save(order);
    }
}

// AFTER: constructor injection
interface PaymentGateway {
    charge(amount: number): Promise<void>;
}

interface OrderRepository {
    save(order: Order): Promise<void>;
}

class OrderService {
    constructor(
        private readonly gateway: PaymentGateway,
        private readonly repo: OrderRepository,
    ) {}

    async processOrder(order: Order): Promise<void> {
        await this.gateway.charge(order.total);
        await this.repo.save(order);
    }
}
```

### C# (Microsoft DI)

```csharp
// BEFORE: tight coupling
public class OrderService
{
    private readonly PaymentGateway _gateway = new StripeGateway();
    private readonly OrderRepository _repo = new SqlOrderRepository();
}

// AFTER: constructor injection with interface
public class OrderService
{
    private readonly IPaymentGateway _gateway;
    private readonly IOrderRepository _repo;

    public OrderService(IPaymentGateway gateway, IOrderRepository repo)
    {
        _gateway = gateway;
        _repo = repo;
    }
}

// Registration in Program.cs
services.AddScoped<IPaymentGateway, StripeGateway>();
services.AddScoped<IOrderRepository, SqlOrderRepository>();
services.AddScoped<OrderService>();
```

### Go

```go
// BEFORE: tight coupling
type OrderService struct{}

func (s *OrderService) ProcessOrder(order Order) error {
    db := sql.Open("postgres", connectionString)
    // use db directly
}

// AFTER: constructor injection via interface
type PaymentGateway interface {
    Charge(amount float64) error
}

type OrderRepository interface {
    Save(order Order) error
}

type OrderService struct {
    gateway PaymentGateway
    repo    OrderRepository
}

func NewOrderService(gw PaymentGateway, repo OrderRepository) *OrderService {
    return &OrderService{gateway: gw, repo: repo}
}
```

## Method Injection

For dependencies that vary per call rather than per instance.

```python
# Use when the dependency is only needed for one method
class ReportGenerator:
    def generate(self, data: list, formatter: ReportFormatter) -> str:
        return formatter.format(data)
```

## Factory Pattern

For dependencies that require runtime information to construct.

```java
public interface NotificationSenderFactory {
    NotificationSender create(NotificationType type);
}

public class OrderService {
    private final NotificationSenderFactory senderFactory;

    public OrderService(NotificationSenderFactory senderFactory) {
        this.senderFactory = senderFactory;
    }

    public void processOrder(Order order) {
        NotificationSender sender = senderFactory.create(order.getNotificationType());
        sender.send(order.getConfirmation());
    }
}
```

## Anti-Patterns to Flag

### Service Locator
Hides dependencies behind a global registry. Makes testing harder and dependencies invisible.
```java
// BAD
public class OrderService {
    public void process(Order order) {
        PaymentGateway gw = ServiceLocator.resolve(PaymentGateway.class);
    }
}
// RECOMMEND: Replace with constructor injection
```

### Singleton Overuse
Global mutable state disguised as a design pattern. Causes hidden coupling and test pollution.
```python
# BAD
class DatabaseConnection:
    _instance = None
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

# RECOMMEND: Constructor injection of a shared instance managed by DI container
```

### Ambient Context
Static properties providing dependencies implicitly.
```csharp
// BAD
var now = DateTime.Now;  // untestable
var user = HttpContext.Current.User;  // hidden dependency

// RECOMMEND: Inject IClock, IHttpContextAccessor
```

### Property Injection (Avoid)
Dependencies set via setters allow partially constructed objects.
```java
// BAD - object can be used before dependencies are set
service.setGateway(gateway);
service.setRepo(repo);

// RECOMMEND: Constructor injection -- all deps required at construction time
```
