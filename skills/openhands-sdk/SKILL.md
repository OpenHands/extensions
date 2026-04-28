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

The **OpenHands Software Agent SDK** is a modular Python framework for building
AI agents that interact with code, files, and system commands.

## Where to find documentation

The canonical, always-up-to-date documentation lives on the docs site:

- **Full documentation:** <https://docs.openhands.dev/sdk>
- **LLMs.txt (structured doc index for agents):** <https://docs.openhands.dev/llms.txt>
- **Source code:** <https://github.com/OpenHands/software-agent-sdk>
- **Examples:** <https://github.com/OpenHands/software-agent-sdk/tree/main/examples/01_standalone_sdk>

**When you need SDK details**, fetch <https://docs.openhands.dev/llms.txt> and
read the "OpenHands Software Agent SDK" section. It contains a complete index
of every guide, architecture page, and API reference with direct links. Follow
the links for the specific topic you need.

For deeper investigation, clone the repo and browse `examples/` and the SDK
source under `openhands-sdk/openhands/sdk/`.

---

## When to use this skill

Use this skill when you need to:

- Build a new agent using the OpenHands SDK
- Create custom tools (Action / Observation / Executor pattern)
- Configure LLMs, workspaces, or conversations programmatically
- Delegate tasks to sub-agents for parallel work
- Integrate MCP (Model Context Protocol) servers
- Add security analysis, confirmation policies, or persistence
- Deploy agents locally, in Docker, or on a remote server
- Understand the SDK's architecture and package structure

---

## Quick start

```bash
pip install openhands-sdk openhands-tools
export LLM_API_KEY="your-api-key"
```

```python
import os
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.terminal import TerminalTool

llm = LLM(
    model=os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
    api_key=os.getenv("LLM_API_KEY"),
)
agent = Agent(llm=llm, tools=[Tool(name=TerminalTool.name)])
conversation = Conversation(agent=agent, workspace=os.getcwd())
conversation.send_message("List files in the current directory")
conversation.run()
```

---

## Key resources in the docs

| Topic | Link |
|---|---|
| Getting started | <https://docs.openhands.dev/sdk/getting-started> |
| Hello World | <https://docs.openhands.dev/sdk/guides/hello-world> |
| Custom tools | <https://docs.openhands.dev/sdk/guides/custom-tools> |
| MCP integration | <https://docs.openhands.dev/sdk/guides/mcp> |
| Agent delegation | <https://docs.openhands.dev/sdk/guides/agent-delegation> |
| Security | <https://docs.openhands.dev/sdk/guides/security> |
| Conversation persistence | <https://docs.openhands.dev/sdk/guides/convo-persistence> |
| Agent server overview | <https://docs.openhands.dev/sdk/guides/agent-server/overview> |
| API reference | <https://docs.openhands.dev/sdk/api-reference/openhands.sdk.agent> |
| FAQ | <https://docs.openhands.dev/sdk/faq> |

For the complete list of all SDK guides and references, see
<https://docs.openhands.dev/llms.txt>.
