---
description: Add valid Python type annotations to functions, methods, and variables
triggers:
  - type annotations
  - add types
  - annotate python
  - type hints
---

# Python Type Annotations

Add comprehensive, valid Python type annotations to Python files.

## Instructions

When asked to add type annotations to a Python file or directory:

1. **Analyze the code** to understand:
   - Function parameters and their expected types
   - Return values
   - Class attributes and instance variables
   - Module-level variables

2. **Add appropriate type annotations**:
   - Use built-in types: `str`, `int`, `float`, `bool`, `bytes`, `None`
   - Use `list[T]`, `dict[K, V]`, `set[T]`, `tuple[T, ...]` for collections (Python 3.9+)
   - Use `Optional[T]` or `T | None` for nullable types
   - Use `Union[A, B]` or `A | B` for multiple possible types
   - Use `Any` sparingly, only when the type is truly dynamic
   - Use `Callable[[Args], Return]` for function types
   - Import from `typing` module when needed: `from typing import Optional, Union, Any, Callable`

3. **Follow best practices**:
   - Annotate all function parameters and return types
   - Annotate class attributes in `__init__` or as class variables
   - Use descriptive type aliases for complex types
   - Preserve existing annotations if they are correct
   - Do not change the logic or behavior of the code

4. **Validate the annotations**:
   - Ensure the file still runs without syntax errors
   - Run `python -m py_compile <file>` to check syntax
   - If mypy is available, run `mypy <file>` to verify types

## Example Transformation

**Before:**
```python
def greet(name):
    return f"Hello, {name}!"

def add_numbers(a, b):
    return a + b
```

**After:**
```python
def greet(name: str) -> str:
    return f"Hello, {name}!"

def add_numbers(a: int, b: int) -> int:
    return a + b
```

## Notes

- Prefer `X | None` over `Optional[X]` for Python 3.10+
- Use `list` instead of `List` for Python 3.9+
- Add `from __future__ import annotations` for forward references in older Python versions
