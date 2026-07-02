---
name: test-improvement-patterns
description: >
  Common execution patterns for implementing validated test-suite improvements.
  Use after planning work to apply safe refactoring, TDD loops, and recurring
  test clean-up patterns.
triggers:
  - test improvement patterns
  - apply test refactoring patterns
  - execute test improvements
version: 1.0.0
metadata:
  openhands:
    requires:
      bins: ["pytest", "git"]
---

# Test Improvement Patterns

Use this skill after the user approves validated improvements. It focuses on how to execute the work safely and efficiently.

## Planning principles

- Use `tdd` when the change introduces new behavior or new helper code.
- Use `refactoring` when the change should preserve behavior.
- Keep changes small enough to verify after each phase.
- Commit before and after large refactoring phases so you always have a safe checkpoint.

## Execution loops

### TDD loop for new behavior

```bash
# 1. Write a failing test
pytest test_file.py::TestClass::test_method -v

# 2. Implement the minimum code to pass
pytest test_file.py::TestClass::test_method -v

# 3. Commit the working change before further cleanup
git add -A && git commit -m "feat: add helper method"
```

### Refactoring loop for existing behavior

```bash
# 1. Save the known-good state
git add -A && git commit -m "checkpoint: before refactoring"

# 2. Make behavior-preserving changes
pytest test_file.py -v

# 3. Commit the refactor
git add -A && git commit -m "refactor: consolidate tests with parameterization"
```

## Commit message conventions

| Change type | Format | Example |
|---|---|---|
| New feature | `feat: <description>` | `feat: add is_unchanged helper` |
| Refactoring | `refactor: <description>` | `refactor: consolidate tests with parametrize` |
| Tests only | `test: <description>` | `test: add failing coverage for helper` |

## Code hygiene reminder

Keep imports at the top of the file. Do not hide imports inside individual tests unless delayed import behavior is the subject of the test.

## Common improvement patterns

### Pattern 0: Replace session-scoped mutable fixtures

**Problem**: shared fixture state leaks between tests.

```python
@pytest.fixture(autouse=True, scope='session')
def mock_api_client():
    with mock_service() as client:
        service._client = client
        yield client
        service._client = None
```

**Preferred direction**: use function scope unless there is a strong, proven reason not to.

```python
@pytest.fixture(autouse=True)
def mock_api_client():
    with mock_service() as client:
        service._client = client
        yield client
        service._client = None
```

### Pattern 1: Reduce implementation coupling

**Problem**: tests reach into internal data structures.

```python
assert ("key", "value") in result.unchanged
```

**Preferred direction**: assert through a stable interface.

```python
assert result.is_unchanged("key")
```

### Pattern 2: Consolidate with parameterization

**Problem**: many tests differ only by input and expected output.

```python
def test_case_a(self):
    assert func("a") == "A"

def test_case_b(self):
    assert func("b") == "B"
```

**Preferred direction**: collapse them into one parametrized test.

```python
@pytest.mark.parametrize("input,expected", [("a", "A"), ("b", "B")])
def test_func_transforms_correctly(self, input, expected):
    assert func(input) == expected
```

### Pattern 3: Extract common assertions

**Problem**: the same assertion bundle appears across multiple tests.

```python
content = file.read_text()
assert "key1" in content
assert "key2" in content
```

**Preferred direction**: move the repeated assertion logic into a reusable helper.

```python
def assert_file_contains_all(file_path, expected_strings):
    content = file_path.read_text()
    for expected in expected_strings:
        assert expected in content
```

### Pattern 4: Replace `time.sleep()` with time control

**Problem**: real delays make tests slow and flaky.

```python
time.sleep(1)
assert runtime.running_time >= 1.0
```

**Preferred direction**: use deterministic time control.

```python
from datetime import timedelta
from freezegun import freeze_time

with freeze_time("2025-01-01 12:00:00") as frozen_time:
    start_runtime()
    frozen_time.tick(delta=timedelta(seconds=5))
    assert runtime.running_time >= 5.0
```

## Final verification reminder

After each pattern application, rerun the smallest relevant test slice first, then the broader suite needed to prove no regression.
