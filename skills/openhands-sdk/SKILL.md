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
print("All done!")
```

## Core classes (`openhands.sdk`)

| Class | Purpose |
|---|---|
| [`Agent`](https://docs.openhands.dev/sdk/arch/agent.md) | Reasoning-action loop |
| [`Condenser`](https://docs.openhands.dev/sdk/arch/condenser.md) | Conversation history compression system |
| [`Conversation`](https://docs.openhands.dev/sdk/arch/conversation.md) | Conversation orchestration system |
| [`Event`](https://docs.openhands.dev/sdk/arch/events.md) | Typed event framework |
| [`LLM`](https://docs.openhands.dev/sdk/arch/llm.md) | Provider-agnostic language model interface |
| [`SecurityAnalyzer`](https://docs.openhands.dev/sdk/arch/security.md) | Action security analysis and validation |
| [`Skill`](https://docs.openhands.dev/sdk/arch/skill.md) | Reusable prompt system |
| [`Tool / ToolDefinition`](https://docs.openhands.dev/sdk/arch/tool-system.md) | Action-observation tool framework |
| [`Workspace`](https://docs.openhands.dev/sdk/arch/workspace.md) | Execution environment abstraction |

## API reference

[`openhands.sdk.agent`](https://docs.openhands.dev/sdk/api-reference/openhands.sdk.agent.md), [`openhands.sdk.conversation`](https://docs.openhands.dev/sdk/api-reference/openhands.sdk.conversation.md), [`openhands.sdk.event`](https://docs.openhands.dev/sdk/api-reference/openhands.sdk.event.md), [`openhands.sdk.llm`](https://docs.openhands.dev/sdk/api-reference/openhands.sdk.llm.md), [`openhands.sdk.security`](https://docs.openhands.dev/sdk/api-reference/openhands.sdk.security.md), [`openhands.sdk.tool`](https://docs.openhands.dev/sdk/api-reference/openhands.sdk.tool.md), [`openhands.sdk.utils`](https://docs.openhands.dev/sdk/api-reference/openhands.sdk.utils.md), [`openhands.sdk.workspace`](https://docs.openhands.dev/sdk/api-reference/openhands.sdk.workspace.md)

## Guides

**Getting Started**
- [FAQ](https://docs.openhands.dev/sdk/faq.md): Frequently asked questions about the OpenHands SDK
- [Getting Started](https://docs.openhands.dev/sdk/getting-started.md): Install the OpenHands SDK and build AI agents that write software.
- [Hello World](https://docs.openhands.dev/sdk/guides/hello-world.md): The simplest possible OpenHands agent - configure an LLM, create an agent, and complete a task.
- [Software Agent SDK](https://docs.openhands.dev/sdk.md): Build AI agents that write software. A clean, modular SDK with production-ready tools.

**Agent**
- [ACP Agent](https://docs.openhands.dev/sdk/guides/agent-acp.md): Delegate to an ACP-compatible server (Claude Code, Gemini CLI, etc.) instead of calling an LLM directly.
- [Agent Settings](https://docs.openhands.dev/sdk/guides/agent-settings.md): Configure, serialize, and recreate agents from structured settings.
- [Agent Skills & Context](https://docs.openhands.dev/sdk/guides/skill.md): Skills add specialized behaviors, domain knowledge, and context-aware triggers to your agent through structured prompts.
- [Browser Session Recording](https://docs.openhands.dev/sdk/guides/browser-session-recording.md): Record and replay your agent's browser sessions using rrweb.
- [Browser Use](https://docs.openhands.dev/sdk/guides/agent-browser-use.md): Enable web browsing and interaction capabilities for your agent.
- [Context Condenser](https://docs.openhands.dev/sdk/guides/context-condenser.md): Manage agent memory by condensing conversation history to save tokens.
- [Creating Custom Agent](https://docs.openhands.dev/sdk/guides/agent-custom.md): Learn how to design specialized agents with custom tool sets
- [Critic (Experimental)](https://docs.openhands.dev/sdk/guides/critic.md): Real-time evaluation of agent actions using an LLM-based critic model, with built-in iterative refinement.
- [File-Based Agents](https://docs.openhands.dev/sdk/guides/agent-file-based.md): Define specialized sub-agents as simple Markdown files with YAML frontmatter — no Python code required.
- [Hooks](https://docs.openhands.dev/sdk/guides/hooks.md): Use lifecycle hooks to observe, log, and customize agent execution.
- [Interactive Terminal](https://docs.openhands.dev/sdk/guides/agent-interactive-terminal.md): Enable agents to interact with terminal applications like ipython, python REPL, and other interactive CLI tools.
- [Iterative Refinement](https://docs.openhands.dev/sdk/guides/iterative-refinement.md): Implement iterative refinement workflows where agents refine their work based on critique feedback until quality thresholds are met.
- [Plugins](https://docs.openhands.dev/sdk/guides/plugins.md): Plugins bundle skills, hooks, MCP servers, agents, and commands into reusable packages that extend agent capabilities.
- [Stuck Detector](https://docs.openhands.dev/sdk/guides/agent-stuck-detector.md): Detect and handle stuck agents automatically with timeout mechanisms.
- [Sub-Agent Delegation](https://docs.openhands.dev/sdk/guides/agent-delegation.md): Enable parallel task execution by delegating work to multiple sub-agents that run independently and return consolidated results.
- [Theory of Mind (TOM) Agent](https://docs.openhands.dev/sdk/guides/agent-tom-agent.md): Enable your agent to understand user intent and preferences through Theory of Mind capabilities, providing personalized guidance based on user modeling.

**LLM**
- [Exception Handling](https://docs.openhands.dev/sdk/guides/llm-error-handling.md): Provider‑agnostic exceptions raised by the SDK and recommended patterns for handling them.
- [GPT-5 Preset (ApplyPatchTool)](https://docs.openhands.dev/sdk/guides/llm-gpt5-preset.md): Use the GPT-5 preset to build an agent that swaps the standard FileEditorTool for ApplyPatchTool.
- [Image Input](https://docs.openhands.dev/sdk/guides/llm-image-input.md): Send images to multimodal agents for vision-based tasks and analysis.
- [LLM Fallback Strategy](https://docs.openhands.dev/sdk/guides/llm-fallback.md): Automatically try alternate LLMs when the primary model fails with a transient error.
- [LLM Profile Store](https://docs.openhands.dev/sdk/guides/llm-profile-store.md): Save, load, and manage reusable LLM configurations so you never repeat setup code again.
- [LLM Registry](https://docs.openhands.dev/sdk/guides/llm-registry.md): Dynamically select and configure language models using the LLM registry.
- [LLM Streaming](https://docs.openhands.dev/sdk/guides/llm-streaming.md): Stream LLM responses token-by-token for real-time display and interactive user experiences.
- [LLM Subscriptions](https://docs.openhands.dev/sdk/guides/llm-subscriptions.md): Use your ChatGPT Plus/Pro subscription to access Codex models without consuming API credits.
- [Model Routing](https://docs.openhands.dev/sdk/guides/llm-routing.md): Route agent's LLM requests to different models.
- [Reasoning](https://docs.openhands.dev/sdk/guides/llm-reasoning.md): Access model reasoning traces from Anthropic extended thinking and OpenAI responses API.

**Conversation**
- [Ask Agent Questions](https://docs.openhands.dev/sdk/guides/convo-ask-agent.md): Get sidebar replies from the agent during conversation execution without interrupting the main flow.
- [Conversation with Async](https://docs.openhands.dev/sdk/guides/convo-async.md): Use async/await for concurrent agent operations and non-blocking execution.
- [Custom Visualizer](https://docs.openhands.dev/sdk/guides/convo-custom-visualizer.md): Customize conversation visualization by creating custom visualizers or configuring the default visualizer.
- [Fork a Conversation](https://docs.openhands.dev/sdk/guides/convo-fork.md): Branch off an existing conversation for follow-up exploration without contaminating the original.
- [Pause and Resume](https://docs.openhands.dev/sdk/guides/convo-pause-and-resume.md): Pause agent execution, perform operations, and resume without losing state.
- [Persistence](https://docs.openhands.dev/sdk/guides/convo-persistence.md): Save and restore conversation state for multi-session workflows.
- [Send Message While Running](https://docs.openhands.dev/sdk/guides/convo-send-message-while-running.md): Interrupt running agents to provide additional context or corrections.

**Tools & MCP**
- [Custom Tools](https://docs.openhands.dev/sdk/guides/custom-tools.md): Tools define what agents can do. The SDK includes built-in tools for common operations and supports creating custom tools for specialized needs.
- [Model Context Protocol](https://docs.openhands.dev/sdk/guides/mcp.md): Model Context Protocol (MCP) enables dynamic tool integration from external servers. Agents can discover and use MCP-provided tools automatically.
- [Parallel Tool Execution](https://docs.openhands.dev/sdk/guides/parallel-tool-execution.md): Execute multiple tools concurrently within a single LLM response to improve throughput for independent operations.
- [Task Tool Set](https://docs.openhands.dev/sdk/guides/task-tool-set.md): Delegate complex work to specialized sub-agents that run synchronously and return results to the parent agent.

**Security & Observability**
- [Metrics Tracking](https://docs.openhands.dev/sdk/guides/metrics.md): Track token usage, costs, and latency metrics for your agents.
- [Observability & Tracing](https://docs.openhands.dev/sdk/guides/observability.md): Enable OpenTelemetry tracing to monitor and debug your agent's execution with tools like Laminar, MLflow, Honeycomb, or any OTLP-compatible backend.
- [Secret Registry](https://docs.openhands.dev/sdk/guides/secrets.md): Provide environment variables and secrets to agent workspace securely.
- [Security & Action Confirmation](https://docs.openhands.dev/sdk/guides/security.md): Control agent action execution through confirmation policy and security analyzer.

**Deployment**
- [API-based Sandbox](https://docs.openhands.dev/sdk/guides/agent-server/api-sandbox.md): Connect to hosted API-based agent server for fully managed infrastructure.
- [Apptainer Sandbox](https://docs.openhands.dev/sdk/guides/agent-server/apptainer-sandbox.md): Run agent server in rootless Apptainer containers for HPC and shared computing environments.
- [Custom Tools with Remote Agent Server](https://docs.openhands.dev/sdk/guides/agent-server/custom-tools.md): Learn how to use custom tools with a remote agent server by building a custom base image that includes your tool implementations.
- [Docker Sandbox](https://docs.openhands.dev/sdk/guides/agent-server/docker-sandbox.md): Run agent server in isolated Docker containers for security and reproducibility.
- [Local Agent Server](https://docs.openhands.dev/sdk/guides/agent-server/local-server.md): Run agents through a local HTTP server with RemoteConversation for client-server architecture.
- [OpenHands Cloud Workspace](https://docs.openhands.dev/sdk/guides/agent-server/cloud-workspace.md): Connect to OpenHands Cloud for fully managed sandbox environments with optional SaaS credential inheritance.
- [Overview](https://docs.openhands.dev/sdk/guides/agent-server/overview.md): Run agents on remote servers with isolated workspaces for production deployments.

**Workflows**
- [Assign Reviews](https://docs.openhands.dev/sdk/guides/github-workflows/assign-reviews.md): Automate PR management with intelligent reviewer assignment and workflow notifications using OpenHands Agent
- [PR Review](https://docs.openhands.dev/sdk/guides/github-workflows/pr-review.md): Use OpenHands Agent to generate meaningful pull request review
- [TODO Management](https://docs.openhands.dev/sdk/guides/github-workflows/todo-management.md): Implement TODOs using OpenHands Agent

## Examples

Source: [`examples/01_standalone_sdk/`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk)

- [`01_hello_world.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/01_hello_world.py) - Hello World
- [`02_custom_tools.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/02_custom_tools.py) - Custom Tools
- [`03_activate_skill.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/03_activate_skill.py) - Activate Skill
- [`04_confirmation_mode_example.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/04_confirmation_mode_example.py) - Confirmation Mode Example
- [`05_use_llm_registry.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/05_use_llm_registry.py) - Use Llm Registry
- [`06_interactive_terminal_w_reasoning.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/06_interactive_terminal_w_reasoning.py) - Interactive Terminal W Reasoning
- [`07_mcp_integration.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/07_mcp_integration.py) - Mcp Integration
- [`08_mcp_with_oauth.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/08_mcp_with_oauth.py) - Mcp With Oauth
- [`09_pause_example.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/09_pause_example.py) - Pause Example
- [`10_persistence.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/10_persistence.py) - Persistence
- [`11_async.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/11_async.py) - Async
- [`12_custom_secrets.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/12_custom_secrets.py) - Custom Secrets
- [`13_get_llm_metrics.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/13_get_llm_metrics.py) - Get Llm Metrics
- [`14_context_condenser.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/14_context_condenser.py) - Context Condenser
- [`15_browser_use.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/15_browser_use.py) - Browser Use
- [`16_llm_security_analyzer.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/16_llm_security_analyzer.py) - Llm Security Analyzer
- [`17_image_input.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/17_image_input.py) - Image Input
- [`18_send_message_while_processing.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/18_send_message_while_processing.py) - Send Message While Processing
- [`19_llm_routing.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/19_llm_routing.py) - Llm Routing
- [`20_stuck_detector.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/20_stuck_detector.py) - Stuck Detector
- [`21_generate_extraneous_conversation_costs.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/21_generate_extraneous_conversation_costs.py) - Generate Extraneous Conversation Costs
- [`22_anthropic_thinking.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/22_anthropic_thinking.py) - Anthropic Thinking
- [`23_responses_reasoning.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/23_responses_reasoning.py) - Responses Reasoning
- [`24_planning_agent_workflow.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/24_planning_agent_workflow.py) - Planning Agent Workflow
- [`25_agent_delegation.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/25_agent_delegation.py) - Agent Delegation
- [`26_custom_visualizer.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/26_custom_visualizer.py) - Custom Visualizer
- [`27_observability_laminar.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/27_observability_laminar.py) - Observability Laminar
- [`28_ask_agent_example.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/28_ask_agent_example.py) - Ask Agent Example
- [`29_llm_streaming.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/29_llm_streaming.py) - Llm Streaming
- [`30_tom_agent.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/30_tom_agent.py) - Tom Agent
- [`31_iterative_refinement.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/31_iterative_refinement.py) - Iterative Refinement
- [`32_configurable_security_policy.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/32_configurable_security_policy.py) - Configurable Security Policy
- [`33_hooks`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/33_hooks) - Hooks
- [`34_critic_example.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/34_critic_example.py) - Critic Example
- [`35_subscription_login.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/35_subscription_login.py) - Subscription Login
- [`36_event_json_to_openai_messages.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/36_event_json_to_openai_messages.py) - Event Json To Openai Messages
- [`37_llm_profile_store`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/37_llm_profile_store) - Llm Profile Store
- [`38_browser_session_recording.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/38_browser_session_recording.py) - Browser Session Recording
- [`39_llm_fallback.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/39_llm_fallback.py) - Llm Fallback
- [`40_acp_agent_example.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/40_acp_agent_example.py) - Acp Agent Example
- [`41_task_tool_set.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/41_task_tool_set.py) - Task Tool Set
- [`42_file_based_subagents.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/42_file_based_subagents.py) - File Based Subagents
- [`43_mixed_marketplace_skills`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/43_mixed_marketplace_skills) - Mixed Marketplace Skills
- [`44_model_switching_in_convo.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/44_model_switching_in_convo.py) - Model Switching In Convo
- [`45_parallel_tool_execution.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/45_parallel_tool_execution.py) - Parallel Tool Execution
- [`46_agent_settings.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/46_agent_settings.py) - Agent Settings
- [`47_defense_in_depth_security.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/47_defense_in_depth_security.py) - Defense In Depth Security
- [`48_conversation_fork.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/48_conversation_fork.py) - Conversation Fork
