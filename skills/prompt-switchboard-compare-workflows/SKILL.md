---
name: prompt-switchboard-compare-workflows
description: Use this skill when you want Prompt Switchboard's compare-first browser workflow through the local MCP sidecar without overclaiming a hosted relay or a live marketplace listing.
version: 1.0.0
---

# Prompt Switchboard Compare Workflows

Teach the agent how to use Prompt Switchboard as a local browser workspace for
side-by-side AI comparison.

## Use this skill when

- the user wants to compare the same prompt across multiple already-open AI chat tabs
- the user wants a browser-native compare workspace instead of a hosted API service
- the user wants one read-first MCP check before larger browser automation

## What the agent should know

- Prompt Switchboard is a compare-first browser extension workspace
- the MCP sidecar is local and supports readiness, compare, and workflow helper tools
- the first success path is to run one real compare and inspect the result locally

## Recommended workflow

1. Confirm the bridge is healthy with `prompt_switchboard.bridge_status`
2. Check the current browser/session state with `prompt_switchboard.check_readiness`
3. Run one comparison with `prompt_switchboard.compare`
4. Summarize the differences with `prompt_switchboard.analyze_compare`
5. Only then move to `prompt_switchboard.run_workflow` for broader orchestration

## Good first tasks

- compare one prompt across two or more models
- verify which model tabs are ready before asking for automation
- collect one inspectable compare artifact before proposing larger workflow changes

## Boundaries

- treat Prompt Switchboard as a local browser workflow, not a hosted platform
- keep claims grounded in the repo-owned MCP and extension surfaces
