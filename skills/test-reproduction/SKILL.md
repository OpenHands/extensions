---
name: test-reproduction
description: Create minimal reproduction scripts to verify bugs before implementing fixes. Use when you need to confirm a bug exists, create a test case, or validate that a problem can be reproduced. Essential for test-driven bug fixing.
---

# Test Reproduction

Create focused reproduction scripts that demonstrate the issue before implementing any fix.

## Why Create Reproduction Scripts First

- Confirms you understand the issue correctly
- Provides immediate feedback when testing fixes
- Serves as a regression test
- Documents the expected vs actual behavior

## Creating a Reproduction Script

### 1. Study Existing Tests

Before creating your script:
- Look at test files in the repository
- Understand the test framework being used (pytest, unittest, etc.)
- Note patterns for setup, execution, and assertions
- Identify how to import and use the affected components

### 2. Create a Minimal Script

Build the smallest possible script that reproduces the issue:

```python
# reproduce_issue.py
# Minimal script to reproduce bug #1234

from module import affected_function

# Setup
test_data = ...

# Execute
result = affected_function(test_data)

# Verify (this should fail with the bug)
expected = ...
assert result == expected, f"Expected {expected}, got {result}"
```

**Keep it minimal:**
- Only import what's needed
- Minimal test data
- Clear assertion or output that shows the bug
- Comments explaining what should happen

### 3. Run and Verify

Execute the reproduction script:
```bash
python reproduce_issue.py
```

**Expected outcome**: The script should fail or show incorrect behavior, confirming the bug.

### 4. Adjust as Needed

If the script doesn't reproduce the issue:
- Re-read the bug report
- Check your understanding of the issue
- Verify you're using the right inputs
- Add debugging output to understand what's happening
- Try different scenarios from the bug report

## Best Practices

- Create the script **before** implementing any fix
- Make it runnable with a single command
- Include clear output showing what's wrong
- Document expected vs actual behavior in comments
- Keep the script in the workspace for validation later
