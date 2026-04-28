---
name: openhands-sdk
description: >-
  Reference skill for the OpenHands Software Agent SDK — the Python framework
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

This skill documents the **OpenHands Software Agent SDK** — a modular Python
framework for building AI agents that interact with code, files, and system
commands.

**Full documentation:** <https://docs.openhands.dev/sdk>
**Source code:** <https://github.com/OpenHands/software-agent-sdk>
**Examples:** <https://github.com/OpenHands/software-agent-sdk/tree/main/examples/01_standalone_sdk>

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

## Installation

```bash
# Core SDK + built-in tools (local development)
pip install openhands-sdk openhands-tools

# Full production stack (adds Docker/remote workspace + agent server)
pip install openhands-sdk openhands-tools openhands-workspace openhands-agent-server
```

Or install from source:

```bash
git clone https://github.com/OpenHands/software-agent-sdk.git
cd software-agent-sdk
make build
```

---

## Four-Package Architecture

| Package | Purpose | When you need it |
|---|---|---|
| **openhands.sdk** | Core agent framework — Agent, LLM, Conversation, Tool system, Events, Workspace base classes, Skills, Condenser, Security | Always (required) |
| **openhands.tools** | Pre-built tools — BashTool, FileEditorTool, GrepTool, TaskTrackerTool, DelegateTool, etc. | Optional — provides common tools |
| **openhands.workspace** | Extended workspace implementations — DockerWorkspace, APIRemoteWorkspace, OpenHandsCloudWorkspace | Optional — for sandboxed/production deployments |
| **openhands.agent_server** | FastAPI HTTP/WebSocket server for remote agent execution | Optional — for multi-user/production deployments |

**Key design:** Same agent code works across all deployment modes — just swap the workspace type (`LocalWorkspace` → `DockerWorkspace` → `RemoteWorkspace` / `APIRemoteWorkspace` / `OpenHandsCloudWorkspace`).

---

## Core Concepts

- **LLM** — Provider-agnostic language model interface (any LiteLLM-supported provider)
- **Agent** — The reasoning-action loop: calls the LLM for decisions, executes tools to perform actions
- **Tool** — Action + Observation + Executor pattern; defines what agents can do
- **Conversation** — Manages the interaction lifecycle, state, and event history
- **Workspace** — Execution environment (local, Docker, or remote)
- **Event** — Typed event framework (ActionEvent, ObservationEvent, MessageEvent, etc.)
- **Skill** — Reusable prompts with trigger-based activation
- **Condenser** — Conversation history compression for token management
- **Security** — Action risk assessment and validation before execution

---

## Hello World

```python
import os
from openhands.sdk import LLM, Agent, Conversation, Tool
from openhands.tools.file_editor import FileEditorTool
from openhands.tools.task_tracker import TaskTrackerTool
from openhands.tools.terminal import TerminalTool

llm = LLM(
    model=os.getenv("LLM_MODEL", "anthropic/claude-sonnet-4-5-20250929"),
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL", None),
)

agent = Agent(
    llm=llm,
    tools=[
        Tool(name=TerminalTool.name),
        Tool(name=FileEditorTool.name),
        Tool(name=TaskTrackerTool.name),
    ],
)

cwd = os.getcwd()
conversation = Conversation(agent=agent, workspace=cwd)
conversation.send_message("Write 3 facts about the current project into FACTS.txt.")
conversation.run()
```

**Run it:**

```bash
export LLM_API_KEY="your-api-key"
uv run python examples/01_standalone_sdk/01_hello_world.py
```

**Using OpenHands Cloud as your LLM provider:**

```bash
export LLM_MODEL="openhands/claude-sonnet-4-5-20250929"
```

**Using your own provider key:**

```bash
export LLM_MODEL="anthropic/claude-sonnet-4-5-20250929"  # or openai/gpt-4o, etc.
```

---

## Default Agent (Preset)

Use `get_default_agent()` for the standard agent with common built-in tools:

```python
from openhands.tools.preset.default import get_default_agent

agent = get_default_agent(llm=llm, cli_mode=True)
```

Or use `get_default_tools()` for the default tool set:

```python
from openhands.tools.preset.default import get_default_tools

tools = get_default_tools(enable_browser=True)
agent = Agent(llm=llm, tools=tools)
```

---

## Custom Tools

Tools follow the **Action / Observation / Executor** pattern:

1. **Action** (Pydantic model) — defines input parameters
2. **Observation** (Pydantic model) — defines output data; must implement `to_llm_content`
3. **Executor** (`ToolExecutor[A, O]`) — implements the tool's logic
4. **ToolDefinition** — ties them together and registers with the agent

```python
from openhands.sdk import Action, Observation, TextContent, ToolDefinition
from openhands.sdk.tool import ToolExecutor, register_tool
from pydantic import Field

class MyAction(Action):
    query: str = Field(description="The search query")

class MyObservation(Observation):
    result: str = ""

    @property
    def to_llm_content(self):
        return [TextContent(text=self.result)]

class MyExecutor(ToolExecutor[MyAction, MyObservation]):
    def __call__(self, action: MyAction, conversation=None) -> MyObservation:
        return MyObservation(result=f"Result for: {action.query}")

class MyTool(ToolDefinition[MyAction, MyObservation]):
    @classmethod
    def create(cls, conv_state) -> list[ToolDefinition]:
        return [cls(
            description="My custom tool",
            action_type=MyAction,
            observation_type=MyObservation,
            executor=MyExecutor(),
        )]

# Register and use
register_tool("MyTool", MyTool)
agent = Agent(llm=llm, tools=[Tool(name="MyTool")])
```

**Tool registration** supports both tool classes and factory functions:

```python
# Factory function — receives conv_state, returns list[ToolDefinition]
def _make_tools(conv_state) -> list[ToolDefinition]:
    executor = TerminalExecutor(working_dir=conv_state.workspace.working_dir)
    return [terminal_tool, grep_tool]

register_tool("MyToolSet", _make_tools)
```

**Shared executors** — multiple tools can share executors for efficiency:

```python
terminal_executor = TerminalExecutor(working_dir=conv_state.workspace.working_dir)
bash_tool = TerminalTool.create(conv_state, executor=terminal_executor)[0]
grep_tool = GrepTool.create(conv_state, terminal_executor=terminal_executor)[0]
```

See: <https://docs.openhands.dev/sdk/guides/custom-tools>

---

## MCP Integration (Model Context Protocol)

Connect external MCP servers for dynamic tool discovery:

```python
mcp_config = {
    "mcpServers": {
        "fetch": {"command": "uvx", "args": ["mcp-server-fetch"]},
        "repomix": {"command": "npx", "args": ["-y", "repomix@1.4.2", "--mcp"]},
    }
}

agent = Agent(
    llm=llm,
    tools=tools,
    mcp_config=mcp_config,
    # Optional: filter which MCP tools are available
    filter_tools_regex="^(?!repomix)(.*)|^repomix.*pack_codebase.*$",
)
```

**MCP with OAuth** (e.g., Notion):

```python
mcp_config = {
    "mcpServers": {
        "Notion": {"url": "https://mcp.notion.com/mcp", "auth": "oauth"}
    }
}
```

See: <https://docs.openhands.dev/sdk/guides/mcp>

---

## Sub-Agent Delegation

Delegate work to multiple sub-agents for parallel processing:

```python
from openhands.sdk.tool import register_tool
from openhands.tools.delegate import DelegateTool
from openhands.tools.preset.default import get_default_tools

register_tool("DelegateTool", DelegateTool)

tools = get_default_tools(enable_browser=False)
tools.append(Tool(name=DelegateTool.name))

agent = Agent(llm=llm, tools=tools)
```

The agent uses `spawn` to create sub-agents and `delegate` to assign tasks:

```json
{"command": "spawn", "ids": ["research", "implementation"]}
```

```json
{"command": "delegate", "tasks": {
    "research": "Find best practices for async code",
    "implementation": "Refactor the MyClass class"
}}
```

**Custom sub-agent types** with `register_agent`:

```python
from openhands.sdk.subagent import register_agent
from openhands.sdk import AgentContext
from openhands.sdk.context import Skill

def create_specialist(llm):
    return Agent(
        llm=llm,
        tools=[],
        agent_context=AgentContext(
            skills=[Skill(name="specialist", content="You are a specialist.", trigger=None)],
            system_message_suffix="Focus on your specialty.",
        ),
    )

register_agent(name="specialist", factory_func=create_specialist, description="A specialist agent")
```

See: <https://docs.openhands.dev/sdk/guides/agent-delegation>

---

## Conversation Persistence

Save and restore conversation state across sessions:

```python
import uuid

conversation = Conversation(
    agent=agent,
    workspace=cwd,
    persistence_dir="./.conversations",
    conversation_id=uuid.uuid4(),
)
conversation.send_message("Start long task")
conversation.run()  # State automatically saved

# Later, in a different session — restore with same ID + persistence_dir
conversation = Conversation(
    agent=agent,
    workspace=cwd,
    persistence_dir="./.conversations",
    conversation_id=conversation_id,
)
conversation.send_message("Continue task")
conversation.run()  # Continues from saved state
```

**What gets persisted:** message history, agent configuration, execution state,
tool outputs, statistics, workspace context, activated skills, secrets, agent state.

See: <https://docs.openhands.dev/sdk/guides/convo-persistence>

---

## Security & Action Confirmation

### Confirmation Policies

```python
from openhands.sdk.security.confirmation_policy import AlwaysConfirm, NeverConfirm, ConfirmRisky

conversation.set_confirmation_policy(AlwaysConfirm())   # require approval for all actions
conversation.set_confirmation_policy(NeverConfirm())     # auto-execute everything
conversation.set_confirmation_policy(ConfirmRisky())     # only confirm risky actions
```

### Security Analyzer

```python
from openhands.sdk.security.llm_analyzer import LLMSecurityAnalyzer

conversation.set_security_analyzer(LLMSecurityAnalyzer())
conversation.set_confirmation_policy(ConfirmRisky())
```

### Defense-in-Depth (Deterministic + LLM)

```python
from openhands.sdk.security import (
    PatternSecurityAnalyzer, PolicyRailSecurityAnalyzer,
    EnsembleSecurityAnalyzer, ConfirmRisky, SecurityRisk,
)

security_analyzer = EnsembleSecurityAnalyzer(analyzers=[
    PolicyRailSecurityAnalyzer(),
    PatternSecurityAnalyzer(),
    LLMSecurityAnalyzer(),  # optional, for deeper coverage
])
conversation.set_security_analyzer(security_analyzer)
conversation.set_confirmation_policy(ConfirmRisky(threshold=SecurityRisk.HIGH))
```

### Custom Security Analyzer

```python
from openhands.sdk.security.analyzer import SecurityAnalyzerBase
from openhands.sdk.security.risk import SecurityRisk

class CustomAnalyzer(SecurityAnalyzerBase):
    def security_risk(self, action) -> SecurityRisk:
        action_str = str(action.action.model_dump()).lower()
        if any(p in action_str for p in ['rm -rf', 'sudo']):
            return SecurityRisk.HIGH
        return SecurityRisk.LOW
```

See: <https://docs.openhands.dev/sdk/guides/security>

---

## Agent Settings (Serializable Configuration)

```python
from openhands.sdk import AgentSettings, LLM, Tool
from openhands.sdk.settings import CondenserSettings

settings = AgentSettings(
    llm=LLM(model="anthropic/claude-sonnet-4-5-20250929", api_key=SecretStr(api_key)),
    tools=[Tool(name=TerminalTool.name), Tool(name=FileEditorTool.name)],
    condenser=CondenserSettings(enabled=True, max_size=50),
)

# Serialize to JSON and back
payload = settings.model_dump(mode="json")
restored = AgentSettings.model_validate(payload)

# Create agent from settings
agent = settings.create_agent()
```

See: <https://docs.openhands.dev/sdk/guides/agent-settings>

---

## Context Condenser

Compress conversation history to manage token usage:

```python
from openhands.sdk.settings import CondenserSettings

settings = AgentSettings(
    llm=llm,
    tools=tools,
    condenser=CondenserSettings(enabled=True, max_size=50),
)
```

See: <https://docs.openhands.dev/sdk/guides/context-condenser>

---

## Skills & Agent Context

Add domain-specific knowledge to agents via skills:

```python
from openhands.sdk import AgentContext
from openhands.sdk.context import Skill

skills = [
    Skill(
        name="my_domain",
        content="You are an expert in X. Always follow Y convention.",
        trigger=None,  # always active; or set a keyword trigger
    ),
]

agent = Agent(
    llm=llm,
    tools=tools,
    agent_context=AgentContext(
        skills=skills,
        system_message_suffix="Additional system prompt content.",
    ),
)
```

See: <https://docs.openhands.dev/sdk/guides/skill>

---

## Conversation Callbacks & Events

```python
from openhands.sdk import Event, LLMConvertibleEvent

llm_messages = []

def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())

conversation = Conversation(
    agent=agent,
    callbacks=[conversation_callback],
    workspace=cwd,
)
```

**Event types:**

| Kind | Source | Purpose |
|---|---|---|
| `ActionEvent` | `agent` | Tool call requested by the agent |
| `ObservationEvent` | `environment` | Tool result from the sandbox |
| `MessageEvent` | `user` / `assistant` | Chat messages |
| `ConversationStateUpdateEvent` | `environment` | State transitions/metadata |

---

## Metrics Tracking

```python
# After conversation.run()
cost = llm.metrics.accumulated_cost
print(f"Total cost: ${cost:.4f}")

# Or via conversation stats
stats = conversation.conversation_stats.get_combined_metrics()
print(f"Combined cost: ${stats.accumulated_cost:.4f}")
```

See: <https://docs.openhands.dev/sdk/guides/metrics>

---

## Observability & Tracing

Enable OpenTelemetry tracing for monitoring and debugging:

See: <https://docs.openhands.dev/sdk/guides/observability>

---

## Remote Agent Server

Deploy agents to Docker containers, a runtime API, OpenHands Cloud, or an already-running agent server:

```python
# Docker workspace — agent runs in an isolated container
from openhands.workspace import DockerWorkspace

workspace = DockerWorkspace()
conversation = Conversation(agent=agent, workspace=workspace)

# Direct agent-server connection — connect to an already-running remote agent server
from openhands.sdk.workspace import RemoteWorkspace

workspace = RemoteWorkspace(
    host="https://agent-server.example.com",
    working_dir="/workspace",
    api_key="session-api-key",  # optional if the server does not require auth
)
conversation = Conversation(agent=agent, workspace=workspace)

# Runtime API workspace — provision/attach to a remote runtime via Runtime API
from openhands.workspace import APIRemoteWorkspace

workspace = APIRemoteWorkspace(
    runtime_api_url="https://runtime.eval.all-hands.dev",
    runtime_api_key="runtime-api-key",
    server_image="ghcr.io/openhands/agent-server:latest-python",
)
conversation = Conversation(agent=agent, workspace=workspace)

# OpenHands Cloud workspace — provision a sandbox through OpenHands Cloud
from openhands.workspace import OpenHandsCloudWorkspace

workspace = OpenHandsCloudWorkspace(
    cloud_api_url="https://app.all-hands.dev",
    cloud_api_key="openhands-cloud-api-key",
)
conversation = Conversation(agent=agent, workspace=workspace)
```

Use `RemoteWorkspace` when you already have an agent-server URL. Use `APIRemoteWorkspace` or `OpenHandsCloudWorkspace` when the SDK should provision the remote environment for you.

See: <https://docs.openhands.dev/sdk/guides/agent-server/overview>

---

## LLM Configuration

### Provider Keys

```python
# Direct provider (Anthropic, OpenAI, etc.)
llm = LLM(model="anthropic/claude-sonnet-4-5-20250929", api_key=SecretStr("sk-..."))

# OpenHands Cloud (recommended — no markup)
llm = LLM(model="openhands/claude-sonnet-4-5-20250929", api_key=SecretStr("oh-..."))
```

### ChatGPT Subscription Login

```python
llm = LLM.subscription_login(vendor="openai", model="gpt-5.2-codex")
```

### LLM Features

- **Streaming:** `llm.stream(...)` for token-by-token output
- **Fallback strategy:** Automatically try alternate LLMs on failure
- **Reasoning traces:** Access extended thinking from Anthropic/OpenAI
- **Image input:** Send images to multimodal agents
- **Model routing:** Route requests to different models
- **Error handling:** Provider-agnostic exception hierarchy
- **Profile store:** Save/load reusable LLM configurations

See: <https://docs.openhands.dev/sdk/guides/llm-streaming>, and other guides under the LLM Features section.

---

## Additional Features

<!-- BEGIN AUTO-SYNCED ADDITIONAL FEATURES -->
| Feature | Guide |
|---|---|
| ACP Agent | <https://docs.openhands.dev/sdk/guides/agent-acp> |
| API-based Sandbox | <https://docs.openhands.dev/sdk/guides/agent-server/api-sandbox> |
| Apptainer Sandbox | <https://docs.openhands.dev/sdk/guides/agent-server/apptainer-sandbox> |
| Ask Agent Questions | <https://docs.openhands.dev/sdk/guides/convo-ask-agent> |
| Assign Reviews | <https://docs.openhands.dev/sdk/guides/github-workflows/assign-reviews> |
| Browser Session Recording | <https://docs.openhands.dev/sdk/guides/browser-session-recording> |
| Browser Use | <https://docs.openhands.dev/sdk/guides/agent-browser-use> |
| Conversation with Async | <https://docs.openhands.dev/sdk/guides/convo-async> |
| Creating Custom Agent | <https://docs.openhands.dev/sdk/guides/agent-custom> |
| Critic (Experimental) | <https://docs.openhands.dev/sdk/guides/critic> |
| Custom Tools with Remote Agent Server | <https://docs.openhands.dev/sdk/guides/agent-server/custom-tools> |
| Custom Visualizer | <https://docs.openhands.dev/sdk/guides/convo-custom-visualizer> |
| Docker Sandbox | <https://docs.openhands.dev/sdk/guides/agent-server/docker-sandbox> |
| Exception Handling | <https://docs.openhands.dev/sdk/guides/llm-error-handling> |
| File-Based Agents | <https://docs.openhands.dev/sdk/guides/agent-file-based> |
| GPT-5 Preset (ApplyPatchTool) | <https://docs.openhands.dev/sdk/guides/llm-gpt5-preset> |
| Hello World | <https://docs.openhands.dev/sdk/guides/hello-world> |
| Hooks | <https://docs.openhands.dev/sdk/guides/hooks> |
| Image Input | <https://docs.openhands.dev/sdk/guides/llm-image-input> |
| Interactive Terminal | <https://docs.openhands.dev/sdk/guides/agent-interactive-terminal> |
| Iterative Refinement | <https://docs.openhands.dev/sdk/guides/iterative-refinement> |
| LLM Fallback Strategy | <https://docs.openhands.dev/sdk/guides/llm-fallback> |
| LLM Profile Store | <https://docs.openhands.dev/sdk/guides/llm-profile-store> |
| LLM Registry | <https://docs.openhands.dev/sdk/guides/llm-registry> |
| LLM Subscriptions | <https://docs.openhands.dev/sdk/guides/llm-subscriptions> |
| Local Agent Server | <https://docs.openhands.dev/sdk/guides/agent-server/local-server> |
| Model Routing | <https://docs.openhands.dev/sdk/guides/llm-routing> |
| OpenHands Cloud Workspace | <https://docs.openhands.dev/sdk/guides/agent-server/cloud-workspace> |
| PR Review | <https://docs.openhands.dev/sdk/guides/github-workflows/pr-review> |
| Parallel Tool Execution | <https://docs.openhands.dev/sdk/guides/parallel-tool-execution> |
| Pause and Resume | <https://docs.openhands.dev/sdk/guides/convo-pause-and-resume> |
| Plugins | <https://docs.openhands.dev/sdk/guides/plugins> |
| Reasoning | <https://docs.openhands.dev/sdk/guides/llm-reasoning> |
| Secret Registry | <https://docs.openhands.dev/sdk/guides/secrets> |
| Send Message While Running | <https://docs.openhands.dev/sdk/guides/convo-send-message-while-running> |
| Stuck Detector | <https://docs.openhands.dev/sdk/guides/agent-stuck-detector> |
| TODO Management | <https://docs.openhands.dev/sdk/guides/github-workflows/todo-management> |
| Task Tool Set | <https://docs.openhands.dev/sdk/guides/task-tool-set> |
| Theory of Mind (TOM) Agent | <https://docs.openhands.dev/sdk/guides/agent-tom-agent> |
<!-- END AUTO-SYNCED ADDITIONAL FEATURES -->

---

## API Reference

| Module | Description |
|---|---|
| `openhands.sdk.agent` | Agent class, reasoning loop, agent context |
| `openhands.sdk.conversation` | Conversation lifecycle, state management |
| `openhands.sdk.event` | Typed event framework |
| `openhands.sdk.llm` | LLM interface, metrics, provider config |
| `openhands.sdk.security` | Security analyzers, confirmation policies, risk levels |
| `openhands.sdk.tool` | Tool system — ToolDefinition, Action, Observation, Executor |
| `openhands.sdk.utils` | Logging, utilities |
| `openhands.sdk.workspace` | Workspace base classes |

Full API reference: <https://docs.openhands.dev/sdk/api-reference/openhands.sdk.agent>

---

## Examples Index

The SDK ships with 40+ examples at `examples/01_standalone_sdk/`:

| # | Example | What it demonstrates |
|---|---|---|
| 01 | `hello_world.py` | Minimal agent setup |
| 02 | `custom_tools.py` | Custom grep tool with shared executors |
| 03 | `activate_microagent.py` | Skills activation |
| 04 | `confirmation_mode_example.py` | Action confirmation |
| 07 | `mcp_integration.py` | MCP server integration |
| 08 | `mcp_with_oauth.py` | MCP with OAuth |
| 10 | `persistence.py` | Save/restore conversation state |
| 16 | `llm_security_analyzer.py` | LLM-based security analysis |
| 25 | `agent_delegation.py` | Sub-agent delegation |
| 32 | `configurable_security_policy.py` | Custom security policies |
| 36 | `event_json_to_openai_messages.py` | Convert persisted events to LLM messages |
| 46 | `agent_settings.py` | Serializable agent configuration |
| 47 | `defense_in_depth_security.py` | Pattern + policy + LLM security ensemble |

Run any example:

```bash
export LLM_API_KEY="your-api-key"
cd software-agent-sdk
uv run python examples/01_standalone_sdk/01_hello_world.py
```

---

## Further Resources

- **Full SDK documentation:** <https://docs.openhands.dev/sdk>
- **SDK source code:** <https://github.com/OpenHands/software-agent-sdk>
- **LLMs.txt (structured doc index):** <https://docs.openhands.dev/llms.txt>
- **Slack community:** <https://join.slack.com/t/openhands-ai/shared_invite/>
- **GitHub Issues:** <https://github.com/OpenHands/software-agent-sdk/issues>
