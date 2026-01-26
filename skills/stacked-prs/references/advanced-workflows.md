# Advanced Stacked PR Workflows

## Mid-Stack Changes

When a reviewer requests changes to PR #2 in a 4-PR stack:

### Step 1: Make the change on the affected branch

```bash
git checkout feature/auth-02-api
# Make changes
git add . && git commit -m "Address review feedback"
git push
```

### Step 2: Rebase downstream branches

```bash
# Rebase PR #3 onto updated PR #2
git checkout feature/auth-03-ui
git rebase feature/auth-02-api
# Resolve any conflicts
git push --force-with-lease

# Rebase PR #4 onto updated PR #3
git checkout feature/auth-04-tests
git rebase feature/auth-03-ui
git push --force-with-lease
```

### Step 3: Notify reviewers

Comment on downstream PRs that they've been rebased. Reviewers may need to re-review.

---

## Handling Merge Conflicts in Rebases

When conflicts occur during `git rebase`:

```bash
# Git will pause at the conflicting commit
# 1. Edit the conflicting files
# 2. Mark as resolved
git add <conflicting-files>
# 3. Continue rebase
git rebase --continue

# If things go wrong, abort and start fresh
git rebase --abort
```

### Conflict Prevention Strategies

1. **Frequent rebases** - Don't let branches drift far from their base
2. **Smaller commits** - Easier to identify and resolve conflicts
3. **Communication** - Coordinate with team on shared files
4. **Feature flags** - Allow incomplete features to coexist

---

## Reordering PRs in a Stack

Sometimes you realize PR #2 should come before PR #1. This is complex:

### Option A: Interactive Rebase (risky)

```bash
git checkout feature/last-branch-in-stack
git rebase -i main
# Reorder commits in the editor
```

**Warning:** This rewrites all history. Only do this if you're comfortable with interactive rebase.

### Option B: Create New Branches (safer)

1. Create new branches in the correct order
2. Cherry-pick commits to the right branches
3. Open new PRs, close old ones

---

## Inserting a PR into an Existing Stack

To add a new PR #2.5 between existing PRs #2 and #3:

```bash
# Start from PR #2
git checkout feature/auth-02-api
git checkout -b feature/auth-02b-validation

# Make your new changes
git add . && git commit -m "Add validation layer"
git push -u origin feature/auth-02b-validation

# Rebase PR #3 onto the new branch
git checkout feature/auth-03-ui
git rebase feature/auth-02b-validation
git push --force-with-lease

# Update PR #3's base branch to the new PR
gh pr edit <pr-3-number> --base feature/auth-02b-validation
```

---

## Splitting a PR That's Already Open

To split an existing large PR into a stack:

### Strategy 1: Reset and Recommit

```bash
# Create a backup branch
git checkout large-feature
git checkout -b large-feature-backup

# Reset to main, keeping changes
git checkout -b feature/part-1
git reset main
# Now all changes are unstaged

# Selectively stage and commit just part 1
git add <part-1-files>
git commit -m "Part 1: Models"
git push -u origin feature/part-1

# Create part 2 branch
git checkout -b feature/part-2
git add <part-2-files>
git commit -m "Part 2: API"
git push -u origin feature/part-2

# Repeat for remaining parts
```

### Strategy 2: Cherry-Pick Commits

If the original PR has well-structured commits:

```bash
# Identify commits for each part
git log --oneline large-feature

# Create branches and cherry-pick
git checkout main
git checkout -b feature/part-1
git cherry-pick <commit-a> <commit-b>

git checkout -b feature/part-2
git cherry-pick <commit-c> <commit-d>
```

---

## Working with Graphite CLI

### Basic Stack Operations

```bash
# Initialize graphite in repo
gt init

# Create stacked branches
gt branch create part-1
gt branch create part-2  # automatically builds on part-1

# View your stack
gt stack

# Submit all PRs in stack
gt stack submit

# Sync entire stack after upstream changes
gt stack sync

# Restack after main changes
gt stack restack
```

### Handling Feedback with Graphite

```bash
# After making changes to part-1
gt branch checkout part-1
# ... make changes ...
git commit -m "Address feedback"

# Sync propagates changes through stack automatically
gt stack sync
```

---

## When Stacks Go Wrong

### Scenario: Stack is too tangled to fix

Sometimes it's easier to start fresh:

1. Create a new branch from main
2. Use `git diff` to get all changes from the stack
3. Apply changes to new branch
4. Re-split into clean stack

```bash
# Get combined diff of entire stack
git diff main...feature/part-4 > all-changes.patch

# Start fresh
git checkout main
git checkout -b feature-clean/part-1

# Apply patch selectively or reference it
# Then re-split logically
```

### Scenario: Reviewer wants to see full feature context

Provide a "preview" branch that merges all stack branches:

```bash
git checkout feature/part-4  # Last branch has all changes
# Or create a merge preview:
git checkout main
git checkout -b feature/preview
git merge --no-ff feature/part-1
git merge --no-ff feature/part-2
git merge --no-ff feature/part-3
git merge --no-ff feature/part-4
git push origin feature/preview
```

Include a link to the preview branch in PR descriptions for reviewers who want full context.

---

## Team Coordination

### When Multiple People Work on a Stack

1. **Designate a stack owner** - One person manages rebases
2. **Communicate before force-pushing** - Prevent lost work
3. **Use `--force-with-lease`** - Safer than `--force`
4. **Consider protected branches** - For critical base branches

### Review Assignment

- Assign the same reviewers to all PRs in a stack for context continuity
- Or split by expertise: backend reviewer for API PRs, frontend for UI PRs
