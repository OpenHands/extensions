---
name: test-improvement-workflow
description: >
  Orchestrates Paul Hammond's test-design-reviewer, tdd, testing, and refactoring skills into a
  systematic workflow for improving test suite quality using Dave Farley's 8 properties.
  Use when asked to "improve test quality", "refactor tests", or "audit tests and fix them".
triggers:
  - test improvement workflow
  - test-improvement-workflow
  - improve test quality
  - refactor tests
  - audit tests and fix them
version: 1.0.0
metadata:
  openhands:
    requires:
      bins: ["grep", "pytest"]
    dependencies:
      - test-design-reviewer
      - tdd
      - refactoring
      - testing
---

# Test Improvement Workflow

A systematic workflow for improving test suite quality using Dave Farley's 8 properties of good tests. Orchestrates the `test-design-reviewer`, `tdd`, `testing`, and `refactoring` skills into a complete improvement cycle.

## Prerequisites

Ensure these skills are available in the workspace:
- `test-design-reviewer` - For auditing test quality using Dave Farley's framework
- `tdd` - For RED-GREEN-MUTATE-KILL MUTANTS-REFACTOR cycle
- `refactoring` - For safe, behavior-preserving code improvements
- `testing` - For behavior-driven testing patterns and edge case documentation

## Workflow Overview

```
+-----------------------------------------------------------------+
|  1. AUDIT: Run test-design-reviewer to get Farley Score         |
+-----------------------------------------------------------------+
|  2. PRIORITIZE: Determine most efficient order of fixes         |
|     (Always show prioritized improvements to user)              |
+-----------------------------------------------------------------+
|  3. PRESENT: Show improvements table with effort/impact         |
|     - Even for exemplary suites (>=9.0), show the list          |
|     - Let user decide whether to proceed                        |
+-----------------------------------------------------------------+
|  4. VALIDATE: Verify each improvement addresses a real issue    |
|     - Check claims against actual code with grep/search         |
|     - Remove invalid improvements before implementation         |
|     - Present revised list if any were invalidated              |
+-----------------------------------------------------------------+
|  5. PLAN: Create task list with skill assignments               |
|     - TDD skill for new code (RED -> GREEN)                     |
|     - Refactoring skill for existing code changes               |
|     - testing skill for edge case comments                      |
|     - test-design-reviewer skill for other test comments        |
+-----------------------------------------------------------------+
|  6. EXECUTE: Follow plan, commit after each phase               |
+-----------------------------------------------------------------+
|  7. VERIFY: Run unbiased re-audit in NEW conversation           |
+-----------------------------------------------------------------+
```

**Important**: Always show the prioritized improvements table to the user, regardless of the Farley Score. Even exemplary test suites (>=9.0) benefit from seeing what minor improvements are possible.

---

## Step 1: Initial Audit

Run the test-design-reviewer skill to evaluate current test quality:

```
test-design-reviewer audit test quality of each test file and make a report of results
```

This produces:
- Property scores (Understandable, Maintainable, Repeatable, Atomic, Necessary, Granular, Fast, First)
- Farley Score (1-10 weighted average)
- Recommendations for improvement

### Consolidating Recommendations (IMPORTANT)

The audit may identify improvements in multiple places:
- **Detailed Analysis** section (per-property observations)
- **Areas for Improvement** section (general observations)
- **Top Recommendations** section (prioritized list)

**Problem**: Items may appear in one section but not another, or appear in multiple sections, creating confusion and potential duplicates.

**Solution**: After the audit, consolidate ALL recommendations into a **single unified list**:

```markdown
## Consolidated Recommendations

Collect ALL improvements from:
1. Property-specific issues from Detailed Analysis
2. Items from Areas for Improvement
3. Items from Top Recommendations
4. Any CRITICAL patterns detected (e.g., scope='session')

Then:
- Remove duplicates (same issue mentioned in multiple places)
- Classify by tier (CRITICAL -> HIGH -> MEDIUM)
- Present as single prioritized table
```

---

## Step 2: Prioritize Improvements (Reliability-First Approach)

**CRITICAL**: Prioritize fixes by **foundational reliability first**, not by visibility or quick wins. Silent issues that affect test correctness are more dangerous than visible issues that affect developer experience.

### Priority Classification Framework

Classify each improvement into one of three tiers:

```
+-----------------------------------------------------------------------------------+
|                         PRIORITY CLASSIFICATION                                    |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  TIER 1: FOUNDATIONAL RELIABILITY (CRITICAL)                                     |
|  -------------------------------------------------------                          |
|  Issues affecting test CORRECTNESS - tests may pass/fail for wrong reasons       |
|                                                                                   |
|  Properties: Atomic, Repeatable                                                   |
|  Examples:                                                                        |
|  - Session-scoped fixtures causing state leakage between tests                   |
|  - Shared mutable state across test classes                                       |
|  - Test order dependencies                                                        |
|  - Non-deterministic behavior (time-dependent, random without seeds)              |
|  - Tests that pass together but fail in isolation                                 |
|                                                                                   |
|  FLAG AS CRITICAL even if not immediately visible!                               |
|                                                                                   |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  TIER 2: VISIBLE SYMPTOMS (HIGH)                                                 |
|  ---------------------------------                                                |
|  Issues with obvious, tangible problems affecting quality                         |
|                                                                                   |
|  Properties: Understandable, Maintainable, Necessary                             |
|  Examples:                                                                        |
|  - Large integration tests (100+ lines testing multiple behaviors)               |
|  - Duplicated test code/payloads across files                                    |
|  - Tests coupled to implementation details                                       |
|  - Missing or unclear test documentation                                         |
|  - Redundant tests providing no additional value                                 |
|                                                                                   |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  TIER 3: DEVELOPER EXPERIENCE (MEDIUM)                                           |
|  ----------------------------------------                                        |
|  Issues affecting speed or convenience, not correctness                           |
|                                                                                   |
|  Properties: Fast, Granular, First (TDD)                                         |
|  Examples:                                                                        |
|  - Slow tests using time.sleep() instead of time mocking                         |
|  - Tests with multiple assertions (failure diagnosis harder)                     |
|  - Tests that appear to be written after implementation                          |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Why This Order Matters

**Key Insight**: Session-scoped fixtures, state leakage, and test isolation issues are **silent killers**. Tests pass but for the wrong reasons. You don't know you have a problem until it bites you in production.

### Automatic CRITICAL Flags

The following patterns should be **automatically flagged as CRITICAL** during audit, even if scores appear acceptable:

| Pattern | Why It's Critical | Investigation Needed |
|---------|-------------------|---------------------|
| `scope='session'` on fixtures | State accumulates across ALL tests | Check if resources persist between tests |
| `scope='module'` with mutable state | State leaks within module | Verify cleanup between tests |
| Shared class-level variables | Tests may depend on prior test mutations | Check for `cls.` variables modified in tests |
| Missing `autouse` cleanup fixtures | Resources may not be released | Verify teardown exists |

### Efficiency Score Calculation (Within Tiers)

After tier classification, calculate efficiency **within each tier**:

```
Efficiency Score = (Property Weight x Score Improvement) / Effort Value

Where:
- Property Weights: Understandable=1.5, Maintainable=1.5, Repeatable=1.25, others=1.0, Fast=0.75
- Score Improvement: Estimated points gained (e.g., improving a property from 8->9 = +1.0)
- Effort Values: Low=1, Medium=2, High=3
```

**But remember**: A CRITICAL Tier 1 issue with low efficiency still comes before a HIGH Tier 2 issue with high efficiency.

---

## Step 3: Present Prioritized Improvements

**Always show the prioritized improvements table**, regardless of the Farley Score.

### Improvements Table Format (with Tier Classification)

```markdown
## Prioritized Improvements

**Current Farley Score: X.X/10 ([Rating])**

### CRITICAL - Foundational Reliability
| # | Improvement | Property | Effort | Note |
|---|-------------|----------|--------|------|
| 1 | Reconsider session-scoped fixtures | Atomic | Medium | Needs investigation |

### HIGH - Visible Symptoms
| # | Improvement | Property | Delta Score | Effort | Efficiency |
|---|-------------|----------|-------------|--------|------------|
| 2 | Add test helper/builder pattern | Maintainable | +0.5 | Low | **0.75** |
| 3 | Break up large integration test | Granular | +1.0 | High | **0.33** |

### MEDIUM - Developer Experience
| # | Improvement | Property | Delta Score | Effort | Efficiency |
|---|-------------|----------|-------------|--------|------------|
| 4 | Replace time.sleep() with freezegun | Fast/Repeatable | +0.5 | Low | **0.50** |

**Legend**:
- CRITICAL: Affects test correctness - may cause false passes/failures
- HIGH: Visible quality issues
- MEDIUM: Developer experience improvements
- Efficiency = (Weight x Delta Score) / Effort. Higher = better ROI within tier.
```

### Key Principle: CRITICAL Items Need Investigation Notes

For CRITICAL items, always include:
1. **Why it's flagged**: Explain the potential reliability risk
2. **Investigation steps**: Commands to verify if it's actually a problem
3. **Conservative approach**: Recommend investigation even if uncertain

```markdown
### CRITICAL Investigation Required

**Issue**: `mock_api_client` fixture uses `scope='session'`

**Risk**: Resources created in one test may persist to subsequent tests, causing:
- Tests that pass together but fail in isolation
- State leakage masking bugs
- Order-dependent test results

**Verification Steps**:
\`\`\`bash
# Run tests in random order to detect dependencies
pytest test/unit/ -p random_order --random-order-seed=12345

# Run a single test in isolation
pytest test/unit/test_billing.py::TestBilling::test_billing_full_lifecycle -v
\`\`\`

**Recommendation**: Investigate before other improvements. If isolation issues exist, fix them first.
```

### Status Labels by Score

| Farley Score | CRITICAL Status | HIGH/MEDIUM Status |
|--------------|-----------------|---------------------|
| < 6.0 (Fair/Poor) | Investigate | **Required** |
| 6.0 - 7.4 (Good) | Investigate | Recommended |
| 7.5 - 8.9 (Excellent) | Investigate | Recommended |
| >= 9.0 (Exemplary) | Investigate | Optional |

**Note**: CRITICAL items always require investigation regardless of overall score.

---

## Step 4: Validate Improvements Against Actual Code

**CRITICAL**: Before implementing any improvements, verify each one addresses a real issue in the code. This prevents wasted effort on phantom problems.

### Why Validation is Required

Initial audits can produce false positives due to:
- **Misread line numbers** - Claiming duplicate code/classes that don't exist
- **Mischaracterized patterns** - Labeling intentional design choices as problems
- **Overlooked documentation** - Suggesting comments that already exist
- **Fixture misunderstanding** - Calling different fixtures "redundant" when they serve different purposes

### Validation Checklist

For each proposed improvement, verify with actual code inspection:

| Improvement Type | Validation Method | What to Check |
|-----------------|-------------------|---------------|
| "Remove duplicate X" | `grep -n "class X\|def X" file.py` | Does X actually appear multiple times? |
| "Add missing comments" | `grep -n "# \|\"\"\"" file.py` | Are comments actually absent? |
| "Consolidate similar fixtures" | Compare fixture definitions | Do they use different sample data intentionally? |
| "Extract common pattern" | Search for actual repetition | Is the pattern truly repeated, or just similar? |
| "Remove redundant tests" | Analyze test purpose | Do the tests verify different behaviors? |

### Validation Process

For each improvement in the table:

1. **State the specific claim** (e.g., "TestMainOutputMessages is duplicated at lines 262 and 1372")
2. **Run verification command** (e.g., `grep -n "class TestMainOutputMessages" test_file.py`)
3. **Compare result to claim**:
   - Valid: Evidence supports the claim -> Keep improvement
   - Invalid: Evidence contradicts the claim -> Remove from list
   - Partial: Claim is overstated -> Revise improvement scope

### After Validation

If any improvements were invalidated:

1. **Present revised assessment** showing which were valid/invalid and why
2. **Recalculate Farley Score** if all improvements were invalidated
3. **Proceed only with validated improvements**

---

## Step 5: Create Implementation Plan

**After user confirms** which improvements to implement, create a detailed task plan with skill assignments.

### Skill Assignment Rules

| Task Type | Skill | When to Use |
|-----------|-------|-------------|
| Adding new code | **TDD** | New helper methods, new test utilities |
| Modifying existing code | **Refactoring** | Consolidating tests, updating assertions |
| Adding edge case comments | **testing** | Comments documenting boundary conditions, branch coverage |
| Adding other test comments | **test-design-reviewer** | Docstrings, test documentation, clarity improvements |
| Verification | **TDD** | Running tests, checking coverage |

### Plan Structure

**For new functionality (TDD skill):**
1. RED: Write failing tests for new behavior
2. GREEN: Implement minimum code to pass
3. VERIFY: Run tests to confirm GREEN
4. COMMIT: Save working code before refactoring

**For code improvements (Refactoring skill):**
1. COMMIT FIRST: Always commit working code before refactoring
2. REFACTOR: Make behavior-preserving changes
3. VERIFY: Run tests to confirm no regressions
4. COMMIT: Save refactored code

---

## Step 6: Execute the Plan

Follow the plan systematically:

### TDD Cycle (for new code)

```bash
# 1. Write failing test
# 2. Run test - confirm it fails (RED)
pytest test_file.py::TestClass::test_method -v

# 3. Implement minimum code
# 4. Run test - confirm it passes (GREEN)
pytest test_file.py::TestClass::test_method -v

# 5. Commit before refactoring
git add -A && git commit -m "feat: add helper method"
```

### Refactoring Cycle (for existing code)

```bash
# 1. Commit current working state FIRST
git add -A && git commit -m "checkpoint: before refactoring"

# 2. Make refactoring changes
# 3. Run ALL tests to verify no regressions
pytest test_file.py -v

# 4. Commit refactoring
git add -A && git commit -m "refactor: consolidate tests with parameterization"
```

### Commit Message Conventions

| Type | Format | Example |
|------|--------|---------|
| New feature | `feat: <description>` | `feat: add is_unchanged() helper to UpdateResult` |
| Refactoring | `refactor: <description>` | `refactor: consolidate tests with @pytest.mark.parametrize` |
| Tests only | `test: <description>` | `test: add failing tests for new helper` |

### Code Quality Guidelines

- **Imports at top of file**: Always place all imports at the top of the file, never inline within test functions or classes.

```python
# Correct: imports at top of file
import pytest
from mymodule import helper_function

class TestMyFeature:
    def test_example(self):
        result = helper_function()
        assert result == expected

# Incorrect: inline imports
class TestMyFeature:
    def test_example(self):
        from mymodule import helper_function  # Don't do this
```

---

## Step 7: Unbiased Re-evaluation

**Critical**: Run the workflow again in a **new conversation** to ensure unbiased evaluation.

### Why a New Conversation?

- No prior knowledge of target scores
- No context bias from implementation work
- Objective assessment of current code state only

### Instructions for Re-evaluation

Start a new conversation with:

```
test-improvement-workflow
```

**Important**: Do NOT include any target scores or expectations in the prompt.

---

## Common Improvement Patterns

### Pattern 0: Fix Session-Scoped Fixtures (CRITICAL)

**Problem**: Session-scoped fixtures share state across all tests

```python
# Before (state leaks between tests)
@pytest.fixture(autouse=True, scope='session')
def mock_api_client():
    with mock_service() as client:
        service._client = client
        yield client
        service._client = None
```

**Solution**: Change to function scope for isolation

```python
# After (each test gets fresh state)
@pytest.fixture(autouse=True)
def mock_api_client():
    with mock_service() as client:
        service._client = client
        yield client
        service._client = None
```

### Pattern 1: Reduce Implementation Coupling

**Problem**: Tests directly access internal data structures

```python
# Before (coupled to internal structure)
assert ("key", "value") in result.unchanged
```

**Solution**: Add helper methods to production code

```python
# After (uses abstraction)
assert result.is_unchanged("key")
```

### Pattern 2: Consolidate with Parameterization

**Problem**: Multiple similar test methods

```python
# Before (redundant)
def test_case_a(self):
    assert func("a") == "A"

def test_case_b(self):
    assert func("b") == "B"
```

**Solution**: Use `@pytest.mark.parametrize`

```python
# After (consolidated)
@pytest.mark.parametrize("input,expected", [
    ("a", "A"),
    ("b", "B"),
])
def test_func_transforms_correctly(self, input, expected):
    assert func(input) == expected
```

### Pattern 3: Extract Common Assertions

**Problem**: Repeated assertion patterns across tests

```python
# Before (duplicated)
content = file.read_text()
assert "key1" in content
assert "key2" in content
```

**Solution**: Create reusable helper in conftest.py

```python
# conftest.py
def assert_file_contains_all(file_path, expected_strings):
    content = file_path.read_text()
    for expected in expected_strings:
        assert expected in content

# Test file
assert_file_contains_all(file, ["key1", "key2"])
```

### Pattern 4: Replace time.sleep() with Time Mocking

**Problem**: Tests use real delays, making them slow and flaky

```python
# Before (slow, non-deterministic)
time.sleep(1)
assert runtime.running_time >= 1.0
```

**Solution**: Use freezegun for deterministic time control

```python
# After (fast, deterministic)
from freezegun import freeze_time
from datetime import timedelta

with freeze_time("2025-01-01 12:00:00") as frozen_time:
    start_runtime()
    frozen_time.tick(delta=timedelta(seconds=5))
    assert runtime.running_time >= 5.0
```

---

## Workflow Summary

| Step | Action | Skill Used | Prompts User? |
|------|--------|------------|---------------|
| 1 | Audit test quality | test-design-reviewer | No |
| 1b | Consolidate all recommendations | - | No (automatic) |
| 2 | Classify by tier (CRITICAL -> HIGH -> MEDIUM) | test-design-reviewer | No (automatic) |
| 3 | Present tiered improvements table | test-design-reviewer | **Yes** (always) |
| 4 | Validate improvements against code | grep/search tools | No (automatic) |
| 5 | Create implementation plan | TDD + Refactoring | No (after user confirms) |
| 6 | Execute plan with commits | TDD + Refactoring | No |
| 7 | Re-run in new conversation | test-improvement-workflow | No |

---

## Quick Start

When this workflow is invoked, automatically:

1. **Audit** all test files using test-design-reviewer
2. **Consolidate** all recommendations into a single list (no duplicates)
3. **Classify improvements by tier**:
   - CRITICAL: Atomic/Repeatable issues (test correctness)
   - HIGH: Understandable/Maintainable/Necessary issues (visible quality)
   - MEDIUM: Fast/Granular/First issues (developer experience)
4. **Flag potential reliability risks** (e.g., `scope='session'`) as CRITICAL with investigation notes
5. **Calculate Efficiency Scores** within each tier: `Efficiency = (Property Weight x Delta Score) / Effort Value`
6. **Present** the consolidated, tiered improvements table with CRITICAL items first
7. **Validate** each improvement against actual code using grep/search
8. **Plan** implementation with TDD/Refactoring skill assignments (after user confirms)
9. **Execute** the plan, committing after each phase
10. **Recommend** re-evaluation in a new conversation

**CRITICAL**:
- Always consolidate recommendations before presenting - never show duplicates or scattered lists
- Foundational reliability issues (Tier 1) must be addressed before visible symptoms (Tier 2) or developer experience improvements (Tier 3)
- Atomic/Repeatable issues should be flagged as CRITICAL even if not immediately visible
