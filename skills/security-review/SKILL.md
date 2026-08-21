---
name: security-review
description: Perform security-focused code review to identify vulnerabilities, insecure patterns, and security best practice violations. Covers OWASP Top 10, authentication, authorization, data protection, and secure coding practices.
triggers:
- /security-review
- /pentest
---

# Security Review

Conduct thorough security analysis of code to identify vulnerabilities and security risks.

## Process

1. **Threat modeling**: Identify attack surfaces and potential threat vectors
2. **Code analysis**: Review for common vulnerability patterns
3. **Configuration review**: Check for insecure defaults and misconfigurations
4. **Dependency audit**: Identify vulnerable dependencies
5. **Report findings**: Provide actionable remediation guidance

## Security Checks

### Input Validation
- SQL injection vulnerabilities
- Cross-site scripting (XSS)
- Command injection
- Path traversal
- XML external entity (XXE) attacks

### Authentication & Authorization
- Weak authentication mechanisms
- Missing or improper authorization checks
- Session management issues
- Insecure password handling

### Data Protection
- Sensitive data exposure
- Insufficient encryption
- Insecure data storage
- PII/PHI handling issues

### API Security
- Broken access control
- Mass assignment vulnerabilities
- Rate limiting gaps
- Improper error handling

### Infrastructure
- Insecure configurations
- Missing security headers
- TLS/SSL issues
- Container security

## Output Format

Provide findings with:
1. **Severity**: Critical, High, Medium, Low, Informational
2. **Location**: File, line, and code snippet
3. **Description**: Clear explanation of the vulnerability
4. **Impact**: Potential consequences if exploited
5. **Remediation**: Specific fix with code examples
6. **References**: CWE, OWASP, or other relevant standards
