---
name: openhands-sdk
description: >-
  Reference skill for the OpenHands Software Agent SDK - the Python framework
  for building AI agents that write software. Use when you need to build agents
  with the SDK, create custom tools, configure LLMs, manage conversations,
  delegate to sub-agents, or deploy agents locally or remotely.
triggers:
- openhands-sdk
- openhands sdk
- software-agent-sdk
- agent-sdk
- /sdk
---

# OpenHands Software Agent SDK

All SDK documentation lives at <https://docs.openhands.dev/sdk>.

For the full topic index, fetch <https://docs.openhands.dev/llms.txt> and read
the "OpenHands Software Agent SDK" section.

## Quick reference

Install: `pip install openhands-sdk openhands-tools`

```python
from openhands.sdk import Agent, LLM, Conversation, Tool
from openhands.tools.terminal import TerminalTool
from openhands.tools.file_editor import FileEditorTool

llm = LLM(model="anthropic/claude-sonnet-4-5-20250929", api_key="...")
agent = Agent(llm=llm, tools=[Tool(name=TerminalTool.name), Tool(name=FileEditorTool.name)])
conversation = Conversation(agent=agent, workspace=".")
conversation.send("Hello!")
```

## Core classes (`openhands.sdk`)

| Class | Purpose |
|---|---|
| `LLM` | Provider-agnostic language model interface (any LiteLLM-supported provider) |
| `Agent` | Reasoning-action loop - calls the LLM, executes tools |
| `Conversation` | Manages the interaction lifecycle, state, and event history |
| `Tool` | Tool reference passed to Agent; wraps a `ToolDefinition` |
| `ToolDefinition` | Action + Observation + Executor pattern for custom tools |
| `Event` | Typed event framework (`ActionEvent`, `ObservationEvent`, `MessageEvent`) |
| `Skill` | Reusable prompts with trigger-based activation |
| `Condenser` | Conversation history compression for token management |
| `SecurityAnalyzer` | Action risk assessment and validation before execution |

## Built-in tools (`openhands.tools`)

`TerminalTool`, `FileEditorTool`, `BashTool`, `GrepTool`, `GlobTool`,
`TaskTrackerTool`, `DelegateTool`, `BrowserTool`, `ApplyPatchTool`

## Workspaces (`openhands.workspace`)

`LocalWorkspace`, `DockerWorkspace`, `RemoteWorkspace`,
`APIRemoteWorkspace`, `OpenHandsCloudWorkspace`

Same agent code works across all modes - just swap the workspace type.

## Key topics

- **Custom tools** - Action / Observation / Executor / `register_tool()`
- **Sub-agent delegation** - `DelegateTool`, file-based agents
- **MCP integration** - connect external MCP servers for dynamic tools
- **Persistence** - save/restore conversation state across sessions
- **Agent Server** (`openhands.agent_server`) - FastAPI server for remote/multi-user deployments
- **Skills & Plugins** - extend agents with structured prompts and reusable packages
