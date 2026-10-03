---
name: discover-vulnerabilities
description: Proactively scan codebases to discover security vulnerabilities before they're exploited. Combines static analysis, dependency scanning, and pattern matching to find security issues.
triggers:
- /discover-vulns
- /find-vulnerabilities
- /vuln-scan
---

# Discover Vulnerabilities

Proactively identify security vulnerabilities in your codebase.

## Process

1. **Dependency scan**: Check for known CVEs in dependencies
2. **Static analysis**: Identify vulnerable code patterns
3. **Secret detection**: Find exposed credentials and API keys
4. **Configuration audit**: Check for insecure settings
5. **Report findings**: Prioritize by severity and exploitability

## Vulnerability Categories

### Dependency Vulnerabilities
- Known CVEs in direct dependencies
- Transitive dependency vulnerabilities
- Outdated packages with security fixes

### Code Vulnerabilities
- Injection flaws (SQL, command, LDAP)
- Cross-site scripting (XSS)
- Insecure deserialization
- Server-side request forgery (SSRF)

### Secrets and Credentials
- Hardcoded passwords and API keys
- Exposed tokens in code or configs
- Credentials in version control history

### Configuration Issues
- Default credentials
- Debug mode in production
- Permissive CORS policies
- Missing security headers

## Output Format

For each vulnerability found:
1. **Severity**: Critical, High, Medium, Low
2. **CVE/CWE**: If applicable
3. **Location**: File and line number
4. **Description**: What the vulnerability is
5. **Exploitation**: How it could be exploited
6. **Remediation**: How to fix it
