---
name: code-verification
description: Verify code changes work correctly and don't break existing functionality. Use after implementing changes to test the fix, run related tests, and ensure no regressions. Critical final step before submitting changes.
---

# Code Verification

Thoroughly test your implementation to ensure correctness and no regressions.

## Verification Steps

### 1. Run Your Reproduction Script

First, verify your fix solves the original problem:
```bash
python reproduce_issue.py
```

**Expected outcome**: The script should now pass or show correct behavior.

If it still fails:
- Review your implementation
- Check if you edited the right location
- Verify your changes are syntactically correct
- Debug the issue further

### 2. Test Edge Cases

Extend your reproduction script with additional test cases:
- Boundary conditions
- Null/empty inputs
- Unusual but valid inputs
- Previously working cases (regression check)

**Example:**
```python
# Test original functionality still works
assert parse_date("12/25/2023") == expected_date_1

# Test new functionality
assert parse_date("2023-12-25") == expected_date_2

# Test edge cases
assert parse_date("2023-12-25T00:00:00") == expected_date_3
```

### 3. Run Existing Tests

Run the repository's test suite for related code:

```bash
# Run all tests
pytest

# Or run specific test file
pytest tests/test_date_parser.py

# Or run tests for specific function
pytest -k test_parse_date
```

**What to check:**
- Tests for the function you modified
- Tests for functions that call your function
- Integration tests that use your component

### 4. Fix Any Test Failures

If tests fail:
1. Read the failure message carefully
2. Understand what the test expects
3. Determine if:
   - Your fix broke valid functionality (fix your code)
   - The test expectations are outdated (understand why before changing)
   - The test itself has issues (rare)

### 5. Verify No Regressions

Ensure existing functionality still works:
- Run the full test suite if possible
- Manually test related features
- Check that your changes don't affect unrelated code paths

## Final Verification Checklist

Before considering the work complete:

- [ ] Reproduction script passes
- [ ] Edge cases handled
- [ ] Related tests pass
- [ ] No new test failures introduced
- [ ] Manual testing of affected functionality
- [ ] Code review of your changes (self-review)
- [ ] Verify minimal scope (didn't change too much)

## If Tests Keep Failing

Debug systematically:
1. Add print statements to understand execution flow
2. Check if you're testing the right code (imports, paths)
3. Verify test environment is set up correctly
4. Re-read the issue requirements
5. Consider if your solution approach needs adjustment
