# /update-docs

Update documentation to match code changes.

## Usage

```
/update-docs
/update-docs <file-or-directory>
/update-docs --type <readme|api|inline>
```

## Examples

```
/update-docs
```
Scans recent changes and updates all relevant documentation.

```
/update-docs src/api/
```
Updates documentation for files in the API directory.

```
/update-docs --type readme
```
Focuses on updating README files only.
