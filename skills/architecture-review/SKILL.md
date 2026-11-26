---
name: architecture-review
description: Review system architecture for scalability, maintainability, and best practices. Analyzes code structure, dependencies, data flow, and provides recommendations for improvements.
triggers:
- /architecture-review
- /arch-review
---

# Architecture Review

Evaluate system architecture and provide actionable recommendations for improvement.

## Process

1. **Map the system**: Understand components, dependencies, and data flow
2. **Identify patterns**: Recognize architectural patterns and anti-patterns
3. **Assess qualities**: Evaluate scalability, maintainability, testability, security
4. **Provide recommendations**: Suggest concrete improvements with trade-offs

## Review Areas

### Code Organization
- Module boundaries and cohesion
- Dependency direction and coupling
- Layer separation (presentation, business, data)
- Package structure and naming

### Scalability
- Horizontal vs vertical scaling considerations
- Stateless design patterns
- Caching strategies
- Database design and query patterns

### Maintainability
- Code complexity and readability
- Technical debt hotspots
- Test coverage and testability
- Documentation completeness

### Security Architecture
- Authentication and authorization patterns
- Data protection and encryption
- Network security boundaries
- Secret management

### Operational Concerns
- Observability (logging, metrics, tracing)
- Error handling and resilience
- Deployment and rollback strategies
- Configuration management

## Output Format

Provide:
1. **Architecture diagram** (if helpful)
2. **Strengths**: What the architecture does well
3. **Concerns**: Issues that should be addressed
4. **Recommendations**: Prioritized list of improvements with effort estimates
