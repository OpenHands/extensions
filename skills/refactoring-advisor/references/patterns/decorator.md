# Decorator Pattern

Use when cross-cutting concerns (logging, caching, auth, retry, metrics) are tangled into core business logic, indicating the Divergent Change or Shotgun Surgery smells.

## When to Apply

- Logging, caching, authentication, or error handling is mixed into business methods
- The same cross-cutting concern is duplicated across multiple classes
- Adding a concern (e.g., metrics) requires modifying many service classes
- Core business logic is obscured by infrastructure concerns

## Structure

```
Client ---> Component (interface)
                |
        +-------+-------+
        |               |
ConcreteComponent   Decorator (implements Component, wraps Component)
                        |
                +-------+-------+
                |               |
          LoggingDecorator  CachingDecorator
```

## Before / After

### Python

```python
# BEFORE: cross-cutting concerns tangled in
class UserService:
    def get_user(self, user_id: str) -> User:
        logger.info(f"Getting user {user_id}")
        start = time.time()

        cached = self.cache.get(f"user:{user_id}")
        if cached:
            logger.info(f"Cache hit for user {user_id}")
            return cached

        try:
            user = self.repo.find(user_id)
            self.cache.set(f"user:{user_id}", user, ttl=300)
            duration = time.time() - start
            metrics.record("get_user_duration", duration)
            return user
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            raise

# AFTER: decorators separate concerns
class UserService:
    """Pure business logic only."""
    def __init__(self, repo: UserRepository):
        self.repo = repo

    def get_user(self, user_id: str) -> User:
        return self.repo.find(user_id)

class LoggingUserService:
    """Logging decorator."""
    def __init__(self, inner: UserService):
        self.inner = inner

    def get_user(self, user_id: str) -> User:
        logger.info(f"Getting user {user_id}")
        try:
            user = self.inner.get_user(user_id)
            logger.info(f"Got user {user_id}")
            return user
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            raise

class CachingUserService:
    """Caching decorator."""
    def __init__(self, inner: UserService, cache: Cache):
        self.inner = inner
        self.cache = cache

    def get_user(self, user_id: str) -> User:
        cached = self.cache.get(f"user:{user_id}")
        if cached:
            return cached
        user = self.inner.get_user(user_id)
        self.cache.set(f"user:{user_id}", user, ttl=300)
        return user

# Composition: CachingUserService(LoggingUserService(UserService(repo)))
```

### TypeScript

```typescript
// AFTER: decorator wrapping
interface UserService {
    getUser(userId: string): Promise<User>;
}

class CoreUserService implements UserService {
    constructor(private readonly repo: UserRepository) {}
    async getUser(userId: string): Promise<User> {
        return this.repo.find(userId);
    }
}

class LoggingUserService implements UserService {
    constructor(private readonly inner: UserService) {}
    async getUser(userId: string): Promise<User> {
        console.log(`Getting user ${userId}`);
        const user = await this.inner.getUser(userId);
        console.log(`Got user ${userId}`);
        return user;
    }
}

// Wire up: new LoggingUserService(new CoreUserService(repo))
```

## Key Considerations

- Each decorator must implement the same interface as the wrapped component
- Decorators are composable: stack them in any order
- Inject decorators via DI container (most frameworks support decorator registration)
- In Python, `functools.wraps` or class-based decorators both work; choose based on complexity
- For simple cases in Python, `@decorator` syntax may be more idiomatic than class-based decorators
- Do not over-decorate: if a concern applies to only one class, inline it
