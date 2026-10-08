# /triage-incident

Investigate a production incident.

## Usage

```
/triage-incident
/triage-incident <error-message-or-description>
/triage-incident --service <service-name>
```

## Examples

```
/triage-incident
```
Investigates the most recent error or alert.

```
/triage-incident "500 errors on /api/users"
```
Investigates a specific error pattern.
