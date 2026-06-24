# /security-review

Perform a security-focused review of code.

## Usage

```
/security-review
/security-review <file-or-directory>
/security-review --focus <auth|input|data|api>
```

## Examples

```
/security-review
```
Reviews the entire codebase for security issues.

```
/security-review src/api/auth/
```
Focuses security review on authentication code.

```
/security-review --focus input
```
Specifically checks for input validation vulnerabilities.
