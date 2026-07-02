---
name: test-prioritization-framework
description: >
  Reliability-first framework for consolidating and prioritizing test audit
  findings. Use after a test review to rank issues as CRITICAL, HIGH, or
  MEDIUM and present a clear improvement table.
triggers:
  - prioritize test improvements
  - test prioritization framework
  - rank test issues
version: 1.0.0
---

# Test Prioritization Framework

Use this skill after an audit has produced a list of possible test-suite improvements. Its job is to turn scattered findings into one ranked plan that puts correctness first.

## Consolidate recommendations first

Audit output can scatter recommendations across multiple sections. Before ranking anything, create one unified list from:

1. Property-specific findings
2. General improvement notes
3. Top recommendations
4. Any reliability risks you noticed during code inspection

Then:

- remove duplicates
- merge overlapping phrasing into one issue
- keep the strongest evidence for each issue
- rank only the deduplicated list

## Tier definitions

### CRITICAL - Foundational reliability

These issues can make tests pass or fail for the wrong reasons.

Properties most often involved:

- Atomic
- Repeatable

Common examples:

- state leakage from `scope='session'` or other shared fixtures
- test order dependencies
- shared mutable class or module state
- non-deterministic time or randomness
- tests that only pass when run with neighboring tests

### HIGH - Visible quality issues

These issues are obvious and worth fixing, but they usually do not invalidate the truthfulness of the suite.

Properties most often involved:

- Understandable
- Maintainable
- Necessary

Common examples:

- oversized tests that cover multiple behaviors
- duplicated setup or payload construction
- tests tightly coupled to implementation details
- unclear or missing test documentation
- redundant tests that add little new coverage

### MEDIUM - Developer experience issues

These issues affect speed and ergonomics more than correctness.

Properties most often involved:

- Fast
- Granular
- First

Common examples:

- slow tests that use `time.sleep()`
- tests with too many assertions to diagnose quickly
- signs that tests were added after the implementation rather than driving it

## Automatic CRITICAL flags

Flag these patterns as CRITICAL even if the initial audit did not emphasize them:

| Pattern | Why it is risky | What to verify |
|---|---|---|
| `scope='session'` fixture with mutable state | state can leak across the entire suite | whether resources persist between tests |
| `scope='module'` fixture with mutable state | state can leak within a file | whether teardown resets state |
| shared class-level variables | one test may depend on another test's mutation | whether tests write to shared objects |
| missing cleanup for autouse fixtures | setup side effects may survive the test | whether teardown is guaranteed |

## Ordering rule

Use this order every time:

1. CRITICAL
2. HIGH
3. MEDIUM

Do not let a high-ROI MEDIUM issue jump ahead of a CRITICAL reliability risk.

## Efficiency scoring within a tier

After tiering, rank items within the same tier by expected return:

```text
Efficiency Score = (Property Weight x Estimated Score Gain) / Effort Value
```

Suggested weights:

- Understandable = 1.5
- Maintainable = 1.5
- Repeatable = 1.25
- Atomic = 1.0
- Necessary = 1.0
- Granular = 1.0
- First = 1.0
- Fast = 0.75

Suggested effort values:

- Low = 1
- Medium = 2
- High = 3

## Presentation format

Always show the user a prioritized table, even for strong suites.

```markdown
## Prioritized Improvements

**Current Farley Score: X.X/10**

### CRITICAL - Foundational Reliability
| # | Improvement | Property | Effort | Note |
|---|---|---|---|---|
| 1 | Revisit session-scoped fixture | Atomic | Medium | Needs investigation |

### HIGH - Visible Symptoms
| # | Improvement | Property | Delta | Effort | Efficiency |
|---|---|---|---|---|---|
| 2 | Add helper or builder pattern | Maintainable | +0.5 | Low | 0.75 |

### MEDIUM - Developer Experience
| # | Improvement | Property | Delta | Effort | Efficiency |
|---|---|---|---|---|---|
| 3 | Replace `time.sleep()` with time control | Fast | +0.5 | Low | 0.38 |
```

## Investigation note requirement for CRITICAL items

Every CRITICAL item should include:

1. why it was flagged
2. the specific reliability risk
3. one or more verification commands
4. a conservative recommendation to investigate first

Example:

```text
Issue: `mock_api_client` uses `scope='session'`
Risk: state may persist across tests and mask failures.
Verification steps:
  pytest test/unit/ -p random_order --random-order-seed=12345
  pytest test/unit/test_billing.py::TestBilling::test_billing_full_lifecycle -v
```

## Status guidance by score

| Farley Score | CRITICAL items | HIGH and MEDIUM items |
|---|---|---|
| < 6.0 | Investigate | Required |
| 6.0 - 7.4 | Investigate | Recommended |
| 7.5 - 8.9 | Investigate | Recommended |
| >= 9.0 | Investigate | Optional |

CRITICAL items always require investigation regardless of the overall score.
