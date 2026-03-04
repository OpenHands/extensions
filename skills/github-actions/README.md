# GitHub Actions Skill

A comprehensive skill for creating, debugging, and testing GitHub Actions workflows and custom actions.

## Overview

This skill provides guidance for working with GitHub Actions, including:
- Creating and structuring workflows
- Building custom actions (composite and reusable)
- Testing actions locally and in CI
- Debugging failed workflows
- Avoiding common pitfalls
- Best practices and security considerations

## When to Use This Skill

Use this skill when:
- Creating new GitHub Actions workflows
- Building custom composite or reusable actions
- Debugging workflow failures
- Setting up CI/CD pipelines
- Troubleshooting permission or secret issues
- Testing actions before merging to main

## Best Practices

1. **Pin action versions**: Use specific versions (`@v4`) or SHA hashes, not `@main`
2. **Minimal permissions**: Explicitly set `permissions` to minimum required
3. **Debug steps**: Add debug output when creating new actions or troubleshooting tricky issues (not required for every workflow)
4. **Fail fast**: Use `fail-fast: false` in matrix builds only when needed
5. **Secrets handling**: Never print secrets; they're masked but can be exposed via encoding
6. **Caching**: Use `actions/cache` for dependencies to speed up workflows
7. **Concurrency control**: Use `concurrency` to cancel redundant workflow runs
8. **Timeout limits**: Set `timeout-minutes` to prevent hung jobs
