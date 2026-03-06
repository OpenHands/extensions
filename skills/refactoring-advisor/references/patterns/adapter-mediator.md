# Adapter and Mediator Patterns

## Adapter Pattern

Use when bridging incompatible interfaces between modules, wrapping third-party libraries, or isolating external API dependencies.

### When to Apply

- Code depends directly on a third-party library's types and methods
- Two modules need to interact but have incompatible interfaces
- Migrating from one implementation to another (e.g., switching payment providers)
- External API responses need transformation to fit domain models

### Before / After

```typescript
// BEFORE: direct coupling to third-party
class OrderService {
    async processPayment(order: Order): Promise<void> {
        const stripe = new Stripe(process.env.STRIPE_KEY);
        const charge = await stripe.charges.create({
            amount: order.total * 100,
            currency: 'usd',
            source: order.paymentToken,
        });
        if (charge.status !== 'succeeded') {
            throw new Error('Payment failed');
        }
    }
}

// AFTER: adapter isolates the third-party dependency
interface PaymentProcessor {
    charge(amount: number, token: string): Promise<PaymentResult>;
}

class StripeAdapter implements PaymentProcessor {
    constructor(private readonly stripe: Stripe) {}

    async charge(amount: number, token: string): Promise<PaymentResult> {
        const charge = await this.stripe.charges.create({
            amount: amount * 100,
            currency: 'usd',
            source: token,
        });
        return { success: charge.status === 'succeeded', id: charge.id };
    }
}

class OrderService {
    constructor(private readonly payment: PaymentProcessor) {}

    async processPayment(order: Order): Promise<void> {
        const result = await this.payment.charge(order.total, order.paymentToken);
        if (!result.success) throw new Error('Payment failed');
    }
}
```

### Key Considerations

- The adapter owns the translation between domain types and external types
- The domain interface (e.g., `PaymentProcessor`) is defined by the consumer, not the adapter
- Adapters make it trivial to swap implementations (testing, migration)
- Combine with constructor injection: inject the adapter as the interface implementation

---

## Mediator Pattern

Use when many-to-many communication between objects creates a web of dependencies, or when Inappropriate Intimacy exists across multiple collaborators.

### When to Apply

- Multiple objects communicate directly with each other (N-to-N coupling)
- Adding a new participant requires modifying many existing participants
- Complex coordination logic is scattered across multiple classes
- UI components or services that all reference each other

### Before / After

```python
# BEFORE: components coupled to each other
class ChatRoom:
    def __init__(self):
        self.users: list[User] = []

class User:
    def __init__(self, name: str, room: ChatRoom):
        self.name = name
        self.room = room
        self.contacts: list[User] = []  # direct references to other users

    def send(self, message: str, to: User):
        to.receive(message, self)  # direct coupling

    def receive(self, message: str, from_user: 'User'):
        print(f"{self.name} received from {from_user.name}: {message}")

# AFTER: mediator centralizes communication
class ChatMediator:
    def __init__(self):
        self._users: dict[str, User] = {}

    def register(self, user: 'User'):
        self._users[user.name] = user

    def send(self, message: str, from_user: str, to_user: str):
        if to_user in self._users:
            self._users[to_user].receive(message, from_user)

class User:
    def __init__(self, name: str, mediator: ChatMediator):
        self.name = name
        self.mediator = mediator  # only knows the mediator
        mediator.register(self)

    def send(self, message: str, to: str):
        self.mediator.send(message, self.name, to)

    def receive(self, message: str, from_name: str):
        print(f"{self.name} received from {from_name}: {message}")
```

### Key Considerations

- Mediator reduces N-to-N coupling to N-to-1 (each participant only knows the mediator)
- Be careful not to create a god mediator -- keep mediation logic focused
- Inject the mediator via constructor (combine with DI)
- Consider events/observer pattern for simpler cases where full mediation isn't needed
- Common in UI frameworks (form validation, component coordination)
