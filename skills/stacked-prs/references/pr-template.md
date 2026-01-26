# Stacked PR Description Template

Copy and customize this template for each PR in your stack.

---

## Template

```markdown
## 🥞 Stack Overview

This PR is **part [X] of [Y]** in the [Feature Name] stack.

| # | PR | Status | Description |
|---|-----|--------|-------------|
| 1 | #123 | ✅ Merged | Data models and migrations |
| 2 | #124 | 👀 This PR | API endpoints |
| 3 | #125 | ⏳ Blocked | UI components |
| 4 | #126 | ⏳ Blocked | Integration tests |

**Stack base:** `main`
**Full feature:** [Brief description of overall feature]

---

## What This PR Does

[Describe what THIS specific PR accomplishes - keep it focused]

## Why This Ordering

[Explain why this PR comes at this position in the stack]

## Review Notes

- [ ] Review this PR in isolation - it should make sense without later PRs
- [ ] Previous PR(s) must be merged first
- [ ] Any specific areas to focus review on

## Testing

- [ ] All existing tests pass
- [ ] New tests added for this PR's changes (if applicable)
- [ ] Manually tested [describe how]

## Dependencies

- **Depends on:** #123 (must be merged first)
- **Blocks:** #125, #126 (waiting on this PR)
```

---

## Compact Template (for smaller stacks)

```markdown
## Stack: [Feature Name] (Part X/Y)

**Previous:** #123 | **Next:** #125

### This PR
[What this specific PR does]

### Stack Progress
1. ✅ #123 - Models
2. 👀 #124 - API (this PR)
3. ⏳ #125 - UI
```

---

## Tips for Good Stack Descriptions

1. **Always link all PRs** - Makes navigation easy
2. **Update status indicators** - Keep ✅/👀/⏳ current
3. **Explain the "why"** - Help reviewers understand the decomposition
4. **Keep individual PR descriptions focused** - Don't repeat full feature spec in each
5. **Note special review considerations** - Anything non-obvious about this slice
