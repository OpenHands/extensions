---
name: test-validation-checklist
description: >
  Checklist for validating proposed test-suite improvements against the real
  code before implementation. Use to remove false positives, narrow overstated
  recommendations, and keep only evidence-backed work.
triggers:
  - validate test improvements
  - test validation checklist
  - verify test audit findings
version: 1.0.0
metadata:
  openhands:
    requires:
      bins: ["grep"]
---

# Test Validation Checklist

Use this skill after you have a proposed improvement list and before you start editing code. Its purpose is to prevent work on phantom problems.

## Why validation matters

Audit output can contain false positives or overstated claims. Common causes include:

- misread line numbers
- treating intentional design choices as defects
- missing existing comments or documentation
- confusing similar fixtures with genuinely redundant ones
- assuming repetition without confirming the repeated code actually exists

## Core rule

For each proposed improvement, verify the claim against the source code before implementation.

Possible outcomes:

- **Valid** - the evidence supports the improvement
- **Invalid** - the claim is unsupported and should be dropped
- **Partial** - the idea is directionally correct but needs narrower scope

## Validation checklist by improvement type

| Improvement type | Validation method | What to confirm |
|---|---|---|
| Remove duplicate class or helper | `grep -n "class X\|def X" file.py` | whether the symbol really appears multiple times |
| Add missing comments | `grep -n "# \|\"\"\"" file.py` | whether comments or docstrings are already present |
| Consolidate fixtures | compare fixture definitions side by side | whether they differ in meaningful data or behavior |
| Extract a repeated pattern | search for exact or near-exact repetition | whether the pattern is repeated enough to justify extraction |
| Remove redundant tests | inspect assertions and setup intent | whether the tests cover genuinely distinct behaviors |
| Flag isolation risk | inspect fixture scope and teardown | whether state can leak across test boundaries |

## Validation process

For each item in the prioritized table:

1. Write down the exact claim.
2. Run a concrete verification command or inspect the relevant code block.
3. Compare the evidence with the claim.
4. Mark the item as Valid, Invalid, or Partial.
5. Update the improvement list before any implementation begins.

## Example workflow

```text
Claim: TestMainOutputMessages is duplicated at lines 262 and 1372.
Check: grep -n "class TestMainOutputMessages" tests/test_cli.py
Result:
- one match -> Invalid
- two or more matches -> Valid
- one class plus repeated helper logic -> Partial
```

## Evidence guidelines

Prefer commands or inspections that directly answer the claim. Good evidence includes:

- exact symbol matches
- side-by-side fixture comparison
- specific examples of repeated assertion blocks
- proof that a cleanup path is missing
- proof that tests fail in isolation or random order

Avoid vague statements such as "this looks redundant" without concrete proof.

## After validation

If any items were invalidated or narrowed:

1. show the user the revised list
2. explain which items changed and why
3. recalculate projected impact if the list changed materially
4. implement only the validated or narrowed items

## Escalation rule for reliability risks

If validation confirms state leakage, order dependence, or non-determinism, move that item to the front of the implementation queue even if it originally appeared lower.
