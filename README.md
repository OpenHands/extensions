# OpenHands Skills Registry

This repository contains the public registry of **Skills** (formerly known as Microagents) for [OpenHands](https://github.com/OpenHands/OpenHands) - reusable guidelines that customize how OpenHands agents behave and solve tasks.

## What are Skills?

Skills are Markdown files containing instructions, best practices, and domain-specific knowledge that guide OpenHands agents when solving tasks. They act as specialized expertise modules that agents can leverage to handle specific scenarios more effectively.

Skills can:
- **Provide domain expertise**: Git workflows, Docker operations, CI/CD processes
- **Encode best practices**: Code review guidelines, testing strategies, security protocols
- **Customize behavior**: Platform-specific instructions (GitHub, GitLab, Azure DevOps)
- **Reduce repetition**: Common patterns that would otherwise need to be specified in every prompt

## Skill Types

OpenHands supports two types of skills:

### 1. General Skills
Always loaded as part of the agent's context, providing baseline knowledge and guidelines.

**Example use cases:**
- Repository-specific conventions and structure
- Project setup and build instructions
- General development guidelines

**Frontmatter:** Optional
```markdown
---
agent: CodeActAgent  # Optional: specify which agent this applies to
---

# Repository Purpose
This project is a web application built with React and Node.js...
```

### 2. Keyword-Triggered Skills
Activated only when specific keywords appear in the user's prompt, providing specialized knowledge on-demand.

**Example use cases:**
- Platform-specific workflows (git, docker, kubernetes)
- Specialized tasks (code review, security analysis)
- Tool-specific operations (npm, pdflatex, ssh)

**Frontmatter:** Required
```markdown
---
triggers:
  - docker
  - dockerfile
  - container
agent: CodeActAgent  # Optional: defaults to CodeActAgent
---

# Docker Guidelines
When working with Docker containers...
```

## Using Skills

### In OpenHands Application
Skills from this registry are automatically loaded when using OpenHands agents through the Software Agent SDK.

### In Custom Projects
You can create project-specific skills by adding a `.openhands/microagents/` directory to your repository:

```
your-repository/
└── .openhands/
    └── microagents/
        ├── repo.md           # General repository guidelines
        ├── git-flow.md       # Keyword-triggered: git workflow
        └── testing.md        # Keyword-triggered: testing practices
```

### Creating a Repository Skill

Ask OpenHands to analyze your repository:

```
Please browse the repository, look at the documentation and relevant code, 
and understand the purpose of this repository.

Create a `.openhands/microagents/repo.md` file with:
1. The purpose of this repository
2. The general setup of this repo
3. A brief description of the structure
4. CI/CD workflows and checks (from .github/ folder)
```

## Contributing Skills

We welcome contributions! Skills in this registry help the entire OpenHands community.

### Guidelines for Good Skills

1. **Be specific and actionable**: Provide clear, executable instructions
2. **Use examples**: Show concrete examples of commands, patterns, or workflows
3. **Keep it focused**: Each skill should address a specific domain or task
4. **Include context**: Explain why certain approaches are recommended
5. **Choose appropriate triggers**: For keyword-triggered skills, use obvious, relevant keywords

### Skill Template

#### General Skill Template
```markdown
---
agent: CodeActAgent
---

# Skill Name

## Overview
Brief description of what this skill provides.

## Guidelines
- Specific instruction 1
- Specific instruction 2

## Examples
```
Example code or workflow
```

## Best Practices
- Best practice 1
- Best practice 2
```

#### Keyword-Triggered Skill Template
```markdown
---
triggers:
  - keyword1
  - keyword2
  - keyword3
agent: CodeActAgent
---

# Skill Name

## When to Use This Skill
Description of scenarios where this skill applies.

## Guidelines
- Specific instruction 1
- Specific instruction 2

## Common Patterns
```
Example code or workflow
```

## Troubleshooting
- Common issue 1: Solution
- Common issue 2: Solution
```

### Submission Process

1. Fork this repository
2. Add your skill as a `.md` file in the `skills/` directory
3. Name it descriptively (e.g., `kubernetes.md`, `code-review.md`)
4. Submit a pull request with:
   - Clear description of the skill's purpose
   - Examples of when it would be triggered (if keyword-triggered)
   - Any relevant context or use cases

## Skill Frontmatter Reference

### Required Fields (for keyword-triggered skills only)

| Field | Description | Example |
|-------|-------------|---------|
| `triggers` | List of keywords that activate the skill | `triggers: [git, github, gitlab]` |

### Optional Fields

| Field | Description | Default |
|-------|-------------|---------|
| `agent` | Which agent this skill applies to | `CodeActAgent` |

## Examples

Browse the [`skills/`](skills/) directory to see real-world examples:

- **[`github.md`](skills/github.md)**: GitHub workflow best practices
- **[`docker.md`](skills/docker.md)**: Docker container management
- **[`code-review.md`](skills/code-review.md)**: Code review guidelines
- **[`security.md`](skills/security.md)**: Security best practices

## Learn More

- [OpenHands Documentation](https://docs.openhands.dev)
- [OpenHands GitHub Repository](https://github.com/OpenHands/OpenHands)
- [Software Agent SDK](https://github.com/OpenHands/software-agent-sdk)

## License

This repository is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
