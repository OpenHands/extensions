---
name: triage-incidents
description: Quickly investigate and triage production incidents by analyzing logs, metrics, and traces. Identifies root causes, suggests fixes, and helps coordinate incident response.
triggers:
- /triage-incident
- /incident
- /investigate
---

# Triage Incidents

Rapidly investigate production incidents to identify root causes and restore service.

## Process

1. **Gather context**: Collect error logs, metrics, recent changes
2. **Identify symptoms**: Understand what's failing and how
3. **Trace root cause**: Follow the error chain to the source
4. **Propose fix**: Suggest immediate remediation
5. **Document findings**: Create incident report

## Investigation Steps

### 1. Initial Assessment
- What is the impact? (users affected, severity)
- When did it start?
- What changed recently? (deploys, config changes)
- Is it getting worse or stable?

### 2. Log Analysis
- Search for error messages and stack traces
- Correlate events across services
- Identify the first occurrence
- Look for patterns or spikes

### 3. Metrics Review
- Check error rates and latency
- Monitor resource utilization (CPU, memory, disk)
- Look for anomalies in traffic patterns
- Review dependency health

### 4. Recent Changes
- Review recent deployments
- Check configuration changes
- Look for infrastructure changes
- Identify new dependencies

### 5. Root Cause Categories

**Code Issues**
- Bugs in recent changes
- Edge cases not handled
- Race conditions

**Infrastructure**
- Resource exhaustion
- Network problems
- Database issues

**Dependencies**
- Third-party service outages
- API changes
- Rate limiting

**Configuration**
- Misconfigured settings
- Missing environment variables
- Permission issues

## Output Format

Provide:
1. **Summary**: One-sentence description of the issue
2. **Impact**: Users/systems affected, severity
3. **Root cause**: What's causing the problem
4. **Immediate fix**: Steps to restore service
5. **Long-term fix**: Prevent recurrence
6. **Timeline**: Key events during incident
