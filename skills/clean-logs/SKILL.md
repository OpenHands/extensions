---
name: clean-logs
description: Analyze and improve application logging by removing noise, standardizing formats, adding structured context, and ensuring appropriate log levels.
triggers:
- /clean-logs
- /improve-logging
---

# Clean Up Logs

Improve application logging for better observability and debugging.

## Process

1. **Audit current logging**: Review existing log statements
2. **Identify issues**: Find noise, missing context, incorrect levels
3. **Standardize**: Apply consistent formatting and structure
4. **Add context**: Include relevant debugging information
5. **Remove noise**: Eliminate unnecessary or redundant logs

## Common Issues

### Log Level Problems
- Debug logs in production code paths
- Errors logged as warnings (or vice versa)
- Info logs that should be debug
- Missing error logs for failure cases

### Missing Context
- Logs without request/correlation IDs
- Error logs without stack traces
- Missing user or session context
- No timing information for slow operations

### Noise and Redundancy
- Excessive logging in hot paths
- Duplicate log messages
- Logging sensitive data (PII, credentials)
- Logs that don't aid debugging

### Format Issues
- Inconsistent log formats
- Unstructured logs that are hard to parse
- Missing timestamps
- Non-standard field names

## Best Practices

- Use structured logging (JSON format)
- Include correlation IDs for request tracing
- Log at appropriate levels (ERROR, WARN, INFO, DEBUG)
- Redact sensitive information
- Include relevant context (user, request, operation)
- Make logs grep-able and queryable
