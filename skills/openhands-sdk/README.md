# openhands-sdk

Reference skill for the **OpenHands Software Agent SDK** — the Python framework
for building AI agents that write software.

- Skill instructions and API overview: [`SKILL.md`](./SKILL.md)

## What's covered

- Installation and package architecture (4-package design)
- Core concepts: LLM, Agent, Conversation, Tool, Workspace, Events
- Hello World and default agent presets
- Custom tools (Action / Observation / Executor pattern)
- MCP (Model Context Protocol) integration
- Sub-agent delegation for parallel task processing
- Conversation persistence (save/restore state)
- Security: confirmation policies, LLM analyzer, defense-in-depth
- Agent settings (serializable configuration)
- Context condenser, skills, callbacks, metrics
- Remote agent server deployment
- Links to 40+ runnable examples

## Quick start

```bash
pip install openhands-sdk openhands-tools
export LLM_API_KEY="your-api-key"
```

```python
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.terminal import TerminalTool

llm = LLM(model="anthropic/claude-sonnet-4-5-20250929", api_key="...")
agent = Agent(llm=llm, tools=[Tool(name=TerminalTool.name)])
conversation = Conversation(agent=agent, workspace=".")
conversation.send_message("List files in the current directory")
conversation.run()
```

## See Also

- [Full SDK docs](https://docs.openhands.dev/sdk)
- [SDK source code](https://github.com/OpenHands/software-agent-sdk)
- [Examples](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/01_standalone_sdk)
