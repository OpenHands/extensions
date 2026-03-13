# Skill Design Patterns

Comprehensive guidance for designing effective skills when refactoring prompts.

## Skill Granularity Guidelines

### Too Granular (Antipattern)

❌ **Problem**: Creating a skill for every sentence or minor instruction

**Example:**
- `read-issue-title` skill
- `identify-error-message` skill
- `note-file-name` skill

**Why it's bad**: Excessive overhead, context bloat, triggers are unclear

### Too Broad (Antipattern)

❌ **Problem**: One skill that does everything

**Example:**
- `fix-everything` skill that handles analysis, testing, implementation, and verification

**Why it's bad**: No modularity, can't reuse parts, hard to maintain

### Just Right ✅

**Sweet spot**: Each skill represents a coherent, reusable capability

**Examples:**
- `code-issue-analysis` - Complete issue analysis workflow
- `test-creation` - Reproduction script creation and validation
- `code-exploration` - Codebase navigation and understanding

**Characteristics:**
- Clear, single purpose
- Independently useful
- Appropriate abstraction level
- 50-300 lines of guidance (typically)

## Progressive Disclosure in Skills

Skills should layer information efficiently:

### Level 1: Metadata (Always in Context)

```yaml
---
name: code-issue-analysis
description: Analyze bug reports and feature requests from issue descriptions. Use when starting work on a code issue to understand requirements, identify affected components, and plan the implementation approach.
---
```

**Key**: Description must be comprehensive enough to trigger correctly

### Level 2: Skill Body (Loaded When Triggered)

```markdown
# Code Issue Analysis

## Quick Start
Read the issue and identify:
- Problem statement
- Expected vs actual behavior
- Affected components
```

**Keep**: Core workflow, essential instructions

**Move out**: Detailed examples, edge cases, comprehensive references

### Level 3: Bundled Resources (Loaded As Needed)

```markdown
## Detailed Analysis

For complex issues, see:
- references/analysis-frameworks.md - Structured analysis methods
- references/common-patterns.md - Frequent bug patterns
```

**Contains**: Deep dives, extensive examples, reference material

## Skill Boundary Patterns

### Pattern 1: Sequential Workflow Phases

When prompt has clear phases (Phase 1, 2, 3...), create skills per phase:

**Original prompt structure:**
```
Phase 1: Analysis
Phase 2: Exploration
Phase 3: Implementation
Phase 4: Verification
```

**Refactored skills:**
- `code-issue-analysis` (Phase 1)
- `code-exploration` (Phase 2)
- `code-implementation` (Phase 3)
- `code-verification` (Phase 4)

**When to use**: Clear sequential workflows with distinct purposes

### Pattern 2: Responsibility-Based

Group by technical responsibility rather than workflow order:

**Example:**
- `test-infrastructure` - All testing-related guidance
- `code-quality` - Standards, style, best practices
- `git-workflow` - Version control procedures

**When to use**: When concerns cut across workflow phases

### Pattern 3: Domain-Specific

Create skills for domain-specific knowledge:

**Example:**
- `swebench-conventions` - SWE-bench specific rules
- `python-testing` - Python test patterns
- `conda-environment` - Conda environment management

**When to use**: Domain knowledge reusable across multiple prompts

### Pattern 4: Hybrid

Combine patterns as needed:

**Example:**
- Core workflow skills (Pattern 1)
- Supporting domain skills (Pattern 3)
- Cross-cutting concern skills (Pattern 2)

## Skill Dependencies

### Independent Skills (Preferred)

```yaml
---
name: test-creation
description: Create reproduction scripts for bugs...
---
```

Can be used standalone, no dependencies.

### Weak Dependencies (Acceptable)

```markdown
# Code Verification

Verify your fix works:
1. Run reproduction test
2. Run related tests
3. Check for regressions

Optionally use the test-creation skill if you don't have a reproduction script yet.
```

References another skill optionally, works without it.

### Strong Dependencies (Avoid)

```markdown
# Code Fix (Antipattern)

This skill requires:
1. Running code-exploration first
2. Having completed issue-analysis
3. Created tests with test-creation

Without these, this skill cannot work.
```

❌ Tightly coupled, hard to use independently.

## Skill Descriptions (Critical!)

The description field controls when skills trigger. Make them comprehensive:

### Weak Description ❌

```yaml
description: Analyzes code issues
```

**Problem**: Vague, won't trigger reliably

### Better Description ✅

```yaml
description: Analyze bug reports and feature requests from issue descriptions. Use when starting work on a code issue to understand requirements, identify affected components, and plan the implementation approach. Includes methods for parsing stack traces, identifying error patterns, and extracting technical details.
```

**Why better**:
- States what it does
- States when to use it
- Includes key capabilities
- Uses triggering keywords

## Common Antipatterns

### 1. Instruction Duplication

❌ **Problem**: Same instructions in multiple skills

**Solution**: Move common instructions to a shared skill or reference doc

### 2. Overly Generic Skills

❌ **Problem**: "helper" or "utility" skills with no clear purpose

**Solution**: Be specific about what the skill accomplishes

### 3. Implementation Details in Prompts

❌ **Problem**: Prompt contains detailed instructions that should be in skills

**Solution**: Move detailed guidance to skills, keep only workflow in prompt

### 4. Skills That Are Too Specific

❌ **Problem**: `django-3.2-test-runner` only works for Django 3.2

**Solution**: Create `python-test-runner` with Django-specific variants in references

### 5. Missing Triggering Context

❌ **Problem**: Skill has great content but poor description, never triggers

**Solution**: Write comprehensive descriptions with triggering keywords

## Refactoring Checklist

When decomposing a prompt into skills:

- [ ] Each skill has a single, clear purpose
- [ ] Skills are independently reusable
- [ ] Descriptions include WHAT and WHEN
- [ ] No circular dependencies
- [ ] No instruction duplication
- [ ] Appropriate granularity (not too fine, not too coarse)
- [ ] References used for detailed content
- [ ] Scripts used for deterministic operations
- [ ] Assets used for templates/boilerplate
- [ ] Original prompt functionality preserved
- [ ] Skills tested independently
- [ ] Refactored prompt tested end-to-end
