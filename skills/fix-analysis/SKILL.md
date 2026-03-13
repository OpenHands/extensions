---
name: fix-analysis
description: Analyze and plan code fixes before implementation. Use after understanding the issue and exploring the code to articulate the problem clearly, identify the root cause, and plan the solution approach. Bridges analysis and implementation.
---

# Fix Analysis

Clearly articulate the problem and solution before writing code.

## State the Problem Clearly

### 1. What is the Problem?

Write a concise statement:
- Current behavior (what happens now)
- Expected behavior (what should happen)
- Root cause (why the problem occurs)

**Example:**
"The `parse_date()` function fails when given dates in ISO 8601 format because it only handles MM/DD/YYYY format. This causes ValueError exceptions when processing international data."

### 2. Where is the Problem Located?

Specify exact locations:
- File: `src/utils/date_parser.py`
- Function/Class: `parse_date()` function
- Line numbers: Lines 45-52

### 3. How Does the Test Reproduce It?

Explain how your reproduction script demonstrates the issue:
- What inputs trigger the problem
- What the script does
- What output shows the bug

## Plan the Fix

### 1. Consider Best Practices

Before implementing, consider:
- **Backward compatibility**: Will this break existing code?
- **Edge cases**: What unusual inputs should be handled?
- **Performance**: Will this impact speed or memory?
- **Testing**: How will we verify this works?
- **Code style**: Does it match project conventions?

### 2. Describe the Solution

Explain how you'll fix the problem:
- What code will change
- What new logic or conditions are needed
- How this addresses the root cause
- Why this approach is best

**Example:**
"Add support for ISO 8601 format by using the `dateutil.parser` library, which handles multiple date formats. Keep existing MM/DD/YYYY support for backward compatibility. Add format detection logic to try ISO 8601 first, then fall back to the original parser."

### 3. Identify Side Effects

Consider what else might be affected:
- Other functions that call this code
- Tests that might break
- Documentation that needs updates
- Related functionality that might need similar fixes

## Output

Produce a clear fix plan containing:
- Problem statement (1-2 sentences)
- Exact location (file, function, lines)
- Solution approach (paragraph)
- Implementation steps (bulleted list)
- Testing strategy (how to verify)
