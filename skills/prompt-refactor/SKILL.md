---
name: prompt-refactor
description: Decompose monolithic prompts into modular, reusable skills. Use this skill when you need to refactor a large prompt template into a skills-based architecture, analyze prompt structure, or convert phase-based instructions into independent skill modules. Ideal for improving prompt maintainability and reusability.
---

# Prompt Refactor

Decompose monolithic prompts into modular, reusable skills for better maintainability and reusability.

## When to Use This Skill

Use this skill when you need to:
- Convert a monolithic prompt into skills-based architecture
- Analyze a prompt's structure and identify factorizable components
- Create modular, reusable skill modules from phase-based instructions
- Refactor benchmark prompts or evaluation templates

## Workflow

### Step 1: Analyze the Prompt Structure

First, understand the prompt's organization and identify distinct phases or workflows.

**Run the analysis script:**

```bash
python3 scripts/analyze_prompt.py <path_to_prompt_file>
```

This will identify:
- Distinct phases or sections
- Workflow patterns
- Suggested skill decomposition

**Manual analysis (if script doesn't work):**

Look for:
- Numbered phases or steps (e.g., "Phase 1. READING:", "Step 2: Analysis")
- Section headers (## Headers)
- Distinct responsibilities or concerns
- Sequential workflows
- Reusable patterns

### Step 2: Identify Skill Boundaries

Group related instructions into cohesive skills based on:

**Single Responsibility**: Each skill should have one clear purpose
- ✅ Good: "code-issue-analysis" - analyzes bug reports
- ❌ Bad: "analyze-and-fix" - mixes analysis and implementation

**Reusability**: Skills that could be useful beyond this specific prompt
- ✅ High reusability: "test-creation", "code-exploration"
- ⚠️ Medium reusability: "swebench-verification" (domain-specific but reusable)
- ❌ Low reusability: Single-use, context-specific instructions

**Independence**: Skills should minimize dependencies on other skills
- ✅ Independent: Can be used standalone
- ⚠️ Weak dependency: References another skill optionally
- ❌ Strong dependency: Cannot function without another skill

### Step 3: Design Each Skill

For each identified skill, plan:

**1. Frontmatter (metadata)**
- `name`: Concise, descriptive identifier (lowercase-with-dashes)
- `description`: What it does AND when to use it (this is crucial for triggering)

**2. Skill body structure**
- Overview: 1-2 sentences
- Key instructions: Specific, actionable steps
- Examples: Concrete illustrations where helpful
- References: Link to bundled resources if needed

**3. Bundled resources** (if applicable)
- `scripts/`: Automation scripts for deterministic tasks
- `references/`: Detailed documentation, patterns, best practices
- `assets/`: Templates or boilerplate files

See `references/skill-design-patterns.md` for detailed guidance on skill design.

### Step 4: Create the Skills

For each skill identified:

**Initialize the skill structure:**

```bash
python3 /path/to/skill-creator/scripts/init_skill.py <skill-name> --path ./skills/
```

**Customize the skill:**
1. Update frontmatter (name, description)
2. Write the skill body based on the original prompt's content
3. Add any necessary bundled resources
4. Remove unused example files

**Validate the skill:**

```bash
python3 /path/to/skill-creator/scripts/quick_validate.py ./skills/<skill-name>
```

### Step 5: Create the Refactored Prompt

Create a new prompt that leverages the skills:

**Instead of inline instructions:**
```jinja2
Phase 1. READING: read the problem and reword it in clearer terms
   1.1 If there are code or config snippets...
   1.2 Highlight message errors...
```

**Use skill references:**
```jinja2
Use the code-issue-analysis skill to understand the problem.

Use the test-creation skill to create reproduction scripts.

Use the code-fix-verification skill to validate your changes.
```

**Template structure:**

```jinja2
{# Context setup #}
Repository: {{ instance.repo_path }}
Issue: {{ instance.problem_statement }}

{# Skill-based workflow #}
Follow this workflow:

1. Analyze the issue (use code-issue-analysis skill)
2. Explore the codebase (use code-exploration skill)  
3. Create reproduction test (use test-creation skill)
4. Implement fix (use code-implementation skill)
5. Verify solution (use code-fix-verification skill)

{# Domain-specific constraints #}
Constraints:
- Don't modify test files
- Dependencies already installed
- Make minimal changes
```

### Step 6: Test and Iterate

**Test the refactored prompt:**
1. Run it on sample instances
2. Verify skills trigger correctly
3. Check that the workflow is clear
4. Compare results with original prompt

**Iterate based on results:**
- If skills don't trigger: Improve descriptions in frontmatter
- If workflow is unclear: Add more guidance in prompt
- If skills overlap: Refine skill boundaries
- If missing functionality: Create additional skills

## Best Practices

### Do:
- ✅ Keep skills focused and single-purpose
- ✅ Write comprehensive descriptions (they control triggering)
- ✅ Test each skill independently
- ✅ Maintain backward compatibility when refactoring existing prompts
- ✅ Document skill dependencies explicitly

### Don't:
- ❌ Create skills that are too granular (skill-per-sentence)
- ❌ Create skills that are too broad (one-skill-does-everything)
- ❌ Duplicate content across multiple skills
- ❌ Forget to update skill descriptions (they're critical for triggering)
- ❌ Create circular dependencies between skills

## Resources

### scripts/analyze_prompt.py

Analyzes a prompt file and identifies:
- Phases and sections
- Workflow patterns
- Suggested skill decomposition

### references/skill-design-patterns.md

Detailed guidance on effective skill design, including:
- Progressive disclosure patterns
- Skill granularity guidelines
- Bundled resource organization
- Common antipatterns to avoid
