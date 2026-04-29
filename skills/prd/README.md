# PRD Generator

Generate a Product Requirements Document (PRD) for a new feature through an interactive clarifying-question workflow. Use when planning a feature, starting a new project, or when asked to create a PRD.

## Triggers

This skill is activated by the following keywords:

- `create a prd`
- `write prd`
- `plan this feature`
- `requirements for`
- `spec out`
- `/prd`

## Overview

The PRD skill walks you through a structured workflow:

1. **Clarifying questions** — 3-5 questions with lettered options (respond with "1A, 2C, 3B" for quick iteration)
2. **PRD generation** — a structured document covering goals, user stories, functional requirements, non-goals, and more
3. **Output** — saved as `prd-[feature-name].md`

The generated PRD is written to be clear enough for junior developers and AI agents to implement from.

## Attribution

Based on the PRD skill from [snarktank/ralph](https://github.com/snarktank/ralph), adapted for the OpenHands extensions registry.
