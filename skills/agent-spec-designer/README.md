# Agent Spec Designer Skill

## Overview
`agent-spec-designer` is a custom OpenHands Skill that enables users to create high-quality, Markdown-based sub-agents through an **interview-style workflow**.

Instead of manually writing agent specifications, this skill guides users step-by-step by asking structured questions and generating a complete agent spec automatically.

## Why This Skill?

Creating file-based agents in OpenHands currently requires:
- Understanding the Markdown schema
- Manually defining all requirements
- Handling edge cases and constraints

This skill solves that by:
- Guiding users interactively
- Ensuring complete and high-quality specifications
- Reducing onboarding friction

## Features

- Interview-style requirement gathering
- Enforces complete agent specification:
  - Goal
  - Tasks
  - Inputs / Outputs
  - Constraints
  - Edge Cases
  - Success Criteria
  - And other aspects based on the situation
- Detects missing or ambiguous requirements
- Suggests improvements (tools, execution, validation, etc.)
- Generates clean, implementation-ready Markdown

## How It Works

### 1. Trigger the skill
/agent-designer


### 2. Interview Phase
The agent will ask questions like:
- What is the goal of your agent?
- What tasks should it perform?
- What inputs and outputs are expected?

### 3. Refinement
- Detects gaps
- Asks follow-up questions
- Suggests improvements

### 4. Generation
Produces a structured Markdown agent specification.

### 5. Optional Save
User can choose to save the spec as a `.md` file.

## Example Use Cases
- Designing a research assistant agent
- Designing a data analysis agent


## File Structure
SKILL.md # Skill definition and behavior
README.md # Documentation

## Design Principles
- Ask one question at a time
- Prefer clarity over speed
- Avoid assumptions
- Ensure completeness before generation