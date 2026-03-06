# Factory and Builder Patterns

## Factory Pattern

Use when object construction is complex, scattered across the codebase, or requires runtime decisions.

### When to Apply

- Object creation logic is duplicated in multiple places
- Construction requires runtime information to decide which implementation to use
- A class needs to create collaborators but shouldn't know their concrete types
- Complex constructor calls with many parameters are repeated

### Before / After

```java
// BEFORE: scattered, duplicated construction
public class NotificationService {
    public void notify(User user, String message) {
        if (user.getPreference() == PreferenceType.EMAIL) {
            SmtpClient client = new SmtpClient("smtp.example.com", 587);
            client.setCredentials(config.getEmailUser(), config.getEmailPass());
            EmailNotification notification = new EmailNotification(client);
            notification.send(user.getEmail(), message);
        } else if (user.getPreference() == PreferenceType.SMS) {
            TwilioClient client = new TwilioClient(config.getTwilioSid(), config.getTwilioToken());
            SmsNotification notification = new SmsNotification(client);
            notification.send(user.getPhone(), message);
        }
        // ... repeated elsewhere in the codebase
    }
}

// AFTER: factory encapsulates creation
public interface NotificationSender {
    void send(User user, String message);
}

public interface NotificationSenderFactory {
    NotificationSender create(PreferenceType type);
}

public class DefaultNotificationSenderFactory implements NotificationSenderFactory {
    private final AppConfig config;

    public DefaultNotificationSenderFactory(AppConfig config) {
        this.config = config;
    }

    public NotificationSender create(PreferenceType type) {
        return switch (type) {
            case EMAIL -> new EmailNotificationSender(
                new SmtpClient(config.getSmtpHost(), config.getSmtpPort()));
            case SMS -> new SmsNotificationSender(
                new TwilioClient(config.getTwilioSid(), config.getTwilioToken()));
        };
    }
}

// Usage: inject factory, not concrete senders
public class NotificationService {
    private final NotificationSenderFactory factory;

    public NotificationService(NotificationSenderFactory factory) {
        this.factory = factory;
    }

    public void notify(User user, String message) {
        factory.create(user.getPreference()).send(user, message);
    }
}
```

### Key Considerations

- Inject factories via constructor -- factories themselves are dependencies
- Factory methods keep the switch in one place (vs. scattered throughout codebase)
- Use when the concrete type depends on runtime data; use plain DI when it's known at startup

---

## Builder Pattern

Use when object construction involves many optional parameters, specific ordering, or step-by-step assembly.

### When to Apply

- Constructors have 5+ parameters, many of which are optional
- Object construction requires a specific sequence of steps
- The same construction process should create different representations
- Temporal coupling exists between initialization steps

### Before / After

```typescript
// BEFORE: constructor with many params, some optional
const query = new SearchQuery(
    "typescript",          // term
    ["title", "body"],     // fields
    10,                    // limit
    0,                     // offset
    "relevance",           // sort
    true,                  // highlight
    undefined,             // filter -- what does undefined mean here?
    "2024-01-01",          // dateFrom
    undefined,             // dateTo
);

// AFTER: builder for clarity
const query = new SearchQueryBuilder("typescript")
    .searchFields(["title", "body"])
    .limit(10)
    .sortBy("relevance")
    .highlight()
    .dateFrom("2024-01-01")
    .build();
```

```python
# Python alternative: use dataclass with defaults (more idiomatic)
@dataclass
class SearchQuery:
    term: str
    fields: list[str] = field(default_factory=lambda: ["title"])
    limit: int = 10
    offset: int = 0
    sort: str = "relevance"
    highlight: bool = False
    date_from: str | None = None
    date_to: str | None = None
```

### Key Considerations

- In Python, prefer `@dataclass` with defaults over Builder pattern for simple cases
- In Java, Lombok's `@Builder` or records with builder reduce boilerplate
- Builder solves temporal coupling: `build()` validates that all required steps were completed
- Builder is for value objects / configuration; do not confuse with Factory (which creates service objects)
