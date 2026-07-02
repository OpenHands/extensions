---
name: manage-dependencies
description: Manage and upgrade project dependencies including security updates, breaking change handling, and version compatibility. Supports npm, pip, cargo, and other package managers.
triggers:
- /update-deps
- /manage-dependencies
- /upgrade-packages
---

# Manage Dependencies

Keep project dependencies up to date, secure, and compatible.

## Process

1. **Audit current state**: Review outdated packages and security vulnerabilities
2. **Plan updates**: Identify which packages need updating and in what order
3. **Handle breaking changes**: Address API changes and compatibility issues
4. **Update lock files**: Ensure consistent installations
5. **Validate**: Run tests to verify updates don't break functionality

## Update Strategies

### Security Updates (Highest Priority)
- Update packages with known CVEs immediately
- Check transitive dependencies for vulnerabilities
- Verify patches don't introduce regressions

### Minor/Patch Updates
- Generally safe to batch update
- Review changelogs for unexpected changes
- Run test suite after updates

### Major Version Updates
- Handle one at a time
- Review migration guides
- Update code for breaking changes
- Test thoroughly

## Package Manager Support

### npm/yarn/pnpm
```bash
npm outdated
npm update
npm audit fix
```

### pip/uv
```bash
pip list --outdated
pip install --upgrade package
pip-audit
```

### cargo
```bash
cargo outdated
cargo update
cargo audit
```

## Common Tasks

### Check for outdated packages
```
/update-deps --check
```

### Update all safe packages (minor/patch)
```
/update-deps --safe
```

### Update specific package with breaking changes
```
/update-deps lodash@5.0.0
```

### Fix security vulnerabilities
```
/update-deps --security
```

## Output Format

Provide:
1. **Current state**: List of outdated packages with versions
2. **Update plan**: Prioritized list of updates
3. **Breaking changes**: API changes that need code updates
4. **Code changes**: Fixes for compatibility issues
5. **Validation**: Test results after updates
