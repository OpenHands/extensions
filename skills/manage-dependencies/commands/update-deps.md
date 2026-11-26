# /update-deps

Manage and update project dependencies.

## Usage

```
/update-deps
/update-deps --check
/update-deps --security
/update-deps --safe
/update-deps <package>@<version>
```

## Examples

```
/update-deps --check
```
Lists all outdated packages without making changes.

```
/update-deps --security
```
Updates only packages with known security vulnerabilities.

```
/update-deps --safe
```
Updates all packages to latest minor/patch versions.

```
/update-deps react@19.0.0
```
Updates a specific package, handling breaking changes.
