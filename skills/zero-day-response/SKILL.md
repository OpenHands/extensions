---
name: zero-day-response
description: Rapidly respond to zero-day vulnerabilities by assessing exposure, implementing mitigations, and applying patches. Designed for urgent security incidents.
triggers:
- /zero-day
- /cve-response
- /urgent-vuln
---

# Zero-Day Response

Rapidly assess and respond to critical security vulnerabilities.

## Process

1. **Assess exposure**: Determine if and how your codebase is affected
2. **Evaluate impact**: Understand the severity and attack vectors
3. **Implement mitigations**: Apply immediate protective measures
4. **Apply patches**: Update vulnerable components
5. **Verify fix**: Confirm the vulnerability is addressed

## Response Steps

### 1. Exposure Assessment
- Search codebase for affected libraries/components
- Check dependency tree for transitive vulnerabilities
- Identify affected code paths and entry points
- Determine if vulnerable code is reachable

### 2. Impact Analysis
- Review CVE details and CVSS score
- Understand exploitation requirements
- Assess data/systems at risk
- Check for known exploits in the wild

### 3. Immediate Mitigations
- Disable affected functionality if critical
- Add input validation or sanitization
- Implement WAF rules or network controls
- Enable additional logging/monitoring

### 4. Patch Application
- Update to patched version if available
- Apply vendor-provided workarounds
- Implement code-level fixes if no patch exists
- Update all affected environments

### 5. Verification
- Confirm patch addresses the vulnerability
- Test that functionality still works
- Verify mitigations are effective
- Document response actions taken

## Output Format

Provide:
1. **Exposure status**: Affected / Not affected / Unknown
2. **Risk assessment**: Critical / High / Medium / Low
3. **Affected components**: List of vulnerable dependencies/code
4. **Recommended actions**: Prioritized response steps
5. **Timeline**: Urgency of each action
