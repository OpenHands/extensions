# /fix-ci

Diagnose and fix CI/CD pipeline failures.

## Usage

```
/fix-ci
/fix-ci <workflow-name>
/fix-ci <pr-number>
```

## Examples

```
/fix-ci
```
Analyzes the most recent CI failure in the current repository.

```
/fix-ci build
```
Focuses on failures in the "build" workflow.

```
/fix-ci #123
```
Analyzes CI failures for PR #123.
