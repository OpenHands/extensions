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

- [ACP Agent](https://docs.openhands.dev/sdk/guides/agent-acp.md): Delegate to an ACP-compatible server (Claude Code, Gemini CLI, etc.) instead of calling an LLM directly.
- [Agent Settings](https://docs.openhands.dev/sdk/guides/agent-settings.md): Configure, serialize, and recreate agents from structured settings.
- [Agent Skills & Context](https://docs.openhands.dev/sdk/guides/skill.md): Skills add specialized behaviors, domain knowledge, and context-aware triggers to your agent through structured prompts.
- [API-based Sandbox](https://docs.openhands.dev/sdk/guides/agent-server/api-sandbox.md): Connect to hosted API-based agent server for fully managed infrastructure.
- [Apptainer Sandbox](https://docs.openhands.dev/sdk/guides/agent-server/apptainer-sandbox.md): Run agent server in rootless Apptainer containers for HPC and shared computing environments.
- [Ask Agent Questions](https://docs.openhands.dev/sdk/guides/convo-ask-agent.md): Get sidebar replies from the agent during conversation execution without interrupting the main flow.
- [Assign Reviews](https://docs.openhands.dev/sdk/guides/github-workflows/assign-reviews.md): Automate PR management with intelligent reviewer assignment and workflow notifications using OpenHands Agent
- [Browser Session Recording](https://docs.openhands.dev/sdk/guides/browser-session-recording.md): Record and replay your agent's browser sessions using rrweb.
- [Browser Use](https://docs.openhands.dev/sdk/guides/agent-browser-use.md): Enable web browsing and interaction capabilities for your agent.
- [Context Condenser](https://docs.openhands.dev/sdk/guides/context-condenser.md): Manage agent memory by condensing conversation history to save tokens.
- [Conversation with Async](https://docs.openhands.dev/sdk/guides/convo-async.md): Use async/await for concurrent agent operations and non-blocking execution.
- [Creating Custom Agent](https://docs.openhands.dev/sdk/guides/agent-custom.md): Learn how to design specialized agents with custom tool sets
- [Critic (Experimental)](https://docs.openhands.dev/sdk/guides/critic.md): Real-time evaluation of agent actions using an LLM-based critic model, with built-in iterative refinement.
- [Custom Tools](https://docs.openhands.dev/sdk/guides/custom-tools.md): Tools define what agents can do. The SDK includes built-in tools for common operations and supports creating custom tools for specialized needs.
- [Custom Tools with Remote Agent Server](https://docs.openhands.dev/sdk/guides/agent-server/custom-tools.md): Learn how to use custom tools with a remote agent server by building a custom base image that includes your tool implementations.
- [Custom Visualizer](https://docs.openhands.dev/sdk/guides/convo-custom-visualizer.md): Customize conversation visualization by creating custom visualizers or configuring the default visualizer.
- [Docker Sandbox](https://docs.openhands.dev/sdk/guides/agent-server/docker-sandbox.md): Run agent server in isolated Docker containers for security and reproducibility.
- [Exception Handling](https://docs.openhands.dev/sdk/guides/llm-error-handling.md): Provider‑agnostic exceptions raised by the SDK and recommended patterns for handling them.
- [FAQ](https://docs.openhands.dev/sdk/faq.md): Frequently asked questions about the OpenHands SDK
- [File-Based Agents](https://docs.openhands.dev/sdk/guides/agent-file-based.md): Define specialized sub-agents as simple Markdown files with YAML frontmatter — no Python code required.
- [Fork a Conversation](https://docs.openhands.dev/sdk/guides/convo-fork.md): Branch off an existing conversation for follow-up exploration without contaminating the original.
- [Getting Started](https://docs.openhands.dev/sdk/getting-started.md): Install the OpenHands SDK and build AI agents that write software.
- [GPT-5 Preset (ApplyPatchTool)](https://docs.openhands.dev/sdk/guides/llm-gpt5-preset.md): Use the GPT-5 preset to build an agent that swaps the standard FileEditorTool for ApplyPatchTool.
- [Hello World](https://docs.openhands.dev/sdk/guides/hello-world.md): The simplest possible OpenHands agent - configure an LLM, create an agent, and complete a task.
- [Hooks](https://docs.openhands.dev/sdk/guides/hooks.md): Use lifecycle hooks to observe, log, and customize agent execution.
- [Image Input](https://docs.openhands.dev/sdk/guides/llm-image-input.md): Send images to multimodal agents for vision-based tasks and analysis.
- [Interactive Terminal](https://docs.openhands.dev/sdk/guides/agent-interactive-terminal.md): Enable agents to interact with terminal applications like ipython, python REPL, and other interactive CLI tools.
- [Iterative Refinement](https://docs.openhands.dev/sdk/guides/iterative-refinement.md): Implement iterative refinement workflows where agents refine their work based on critique feedback until quality thresholds are met.
- [LLM Fallback Strategy](https://docs.openhands.dev/sdk/guides/llm-fallback.md): Automatically try alternate LLMs when the primary model fails with a transient error.
- [LLM Profile Store](https://docs.openhands.dev/sdk/guides/llm-profile-store.md): Save, load, and manage reusable LLM configurations so you never repeat setup code again.
- [LLM Registry](https://docs.openhands.dev/sdk/guides/llm-registry.md): Dynamically select and configure language models using the LLM registry.
- [LLM Streaming](https://docs.openhands.dev/sdk/guides/llm-streaming.md): Stream LLM responses token-by-token for real-time display and interactive user experiences.
- [LLM Subscriptions](https://docs.openhands.dev/sdk/guides/llm-subscriptions.md): Use your ChatGPT Plus/Pro subscription to access Codex models without consuming API credits.
- [Local Agent Server](https://docs.openhands.dev/sdk/guides/agent-server/local-server.md): Run agents through a local HTTP server with RemoteConversation for client-server architecture.
- [Metrics Tracking](https://docs.openhands.dev/sdk/guides/metrics.md): Track token usage, costs, and latency metrics for your agents.
- [Model Context Protocol](https://docs.openhands.dev/sdk/guides/mcp.md): Model Context Protocol (MCP) enables dynamic tool integration from external servers. Agents can discover and use MCP-provided tools automatically.
- [Model Routing](https://docs.openhands.dev/sdk/guides/llm-routing.md): Route agent's LLM requests to different models.
- [Observability & Tracing](https://docs.openhands.dev/sdk/guides/observability.md): Enable OpenTelemetry tracing to monitor and debug your agent's execution with tools like Laminar, MLflow, Honeycomb, or any OTLP-compatible backend.
- [OpenHands Cloud Workspace](https://docs.openhands.dev/sdk/guides/agent-server/cloud-workspace.md): Connect to OpenHands Cloud for fully managed sandbox environments with optional SaaS credential inheritance.
- [Overview](https://docs.openhands.dev/sdk/guides/agent-server/overview.md): Run agents on remote servers with isolated workspaces for production deployments.
- [Parallel Tool Execution](https://docs.openhands.dev/sdk/guides/parallel-tool-execution.md): Execute multiple tools concurrently within a single LLM response to improve throughput for independent operations.
- [Pause and Resume](https://docs.openhands.dev/sdk/guides/convo-pause-and-resume.md): Pause agent execution, perform operations, and resume without losing state.
- [Persistence](https://docs.openhands.dev/sdk/guides/convo-persistence.md): Save and restore conversation state for multi-session workflows.
- [Plugins](https://docs.openhands.dev/sdk/guides/plugins.md): Plugins bundle skills, hooks, MCP servers, agents, and commands into reusable packages that extend agent capabilities.
- [PR Review](https://docs.openhands.dev/sdk/guides/github-workflows/pr-review.md): Use OpenHands Agent to generate meaningful pull request review
- [Reasoning](https://docs.openhands.dev/sdk/guides/llm-reasoning.md): Access model reasoning traces from Anthropic extended thinking and OpenAI responses API.
- [Secret Registry](https://docs.openhands.dev/sdk/guides/secrets.md): Provide environment variables and secrets to agent workspace securely.
- [Security & Action Confirmation](https://docs.openhands.dev/sdk/guides/security.md): Control agent action execution through confirmation policy and security analyzer.
- [Send Message While Running](https://docs.openhands.dev/sdk/guides/convo-send-message-while-running.md): Interrupt running agents to provide additional context or corrections.
- [Software Agent SDK](https://docs.openhands.dev/sdk.md): Build AI agents that write software. A clean, modular SDK with production-ready tools.
- [Stuck Detector](https://docs.openhands.dev/sdk/guides/agent-stuck-detector.md): Detect and handle stuck agents automatically with timeout mechanisms.
- [Sub-Agent Delegation](https://docs.openhands.dev/sdk/guides/agent-delegation.md): Enable parallel task execution by delegating work to multiple sub-agents that run independently and return consolidated results.
- [Task Tool Set](https://docs.openhands.dev/sdk/guides/task-tool-set.md): Delegate complex work to specialized sub-agents that run synchronously and return results to the parent agent.
- [Theory of Mind (TOM) Agent](https://docs.openhands.dev/sdk/guides/agent-tom-agent.md): Enable your agent to understand user intent and preferences through Theory of Mind capabilities, providing personalized guidance based on user modeling.
- [TODO Management](https://docs.openhands.dev/sdk/guides/github-workflows/todo-management.md): Implement TODOs using OpenHands Agent

## Examples

Source: [`examples/`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples)

### [`01_standalone_sdk/`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/01_standalone_sdk)

- [`01_hello_world.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/01_hello_world.py)
- [`02_custom_tools.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/02_custom_tools.py)
- [`03_activate_skill.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/03_activate_skill.py)
- [`04_confirmation_mode_example.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/04_confirmation_mode_example.py)
- [`05_use_llm_registry.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/05_use_llm_registry.py)
- [`06_interactive_terminal_w_reasoning.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/06_interactive_terminal_w_reasoning.py)
- [`07_mcp_integration.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/07_mcp_integration.py)
- [`08_mcp_with_oauth.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/08_mcp_with_oauth.py)
- [`09_pause_example.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/09_pause_example.py)
- [`10_persistence.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/10_persistence.py)
- [`11_async.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/11_async.py)
- [`12_custom_secrets.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/12_custom_secrets.py)
- [`13_get_llm_metrics.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/13_get_llm_metrics.py)
- [`14_context_condenser.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/14_context_condenser.py)
- [`15_browser_use.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/15_browser_use.py)
- [`16_llm_security_analyzer.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/16_llm_security_analyzer.py)
- [`17_image_input.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/17_image_input.py)
- [`18_send_message_while_processing.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/18_send_message_while_processing.py)
- [`19_llm_routing.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/19_llm_routing.py)
- [`20_stuck_detector.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/20_stuck_detector.py)
- [`21_generate_extraneous_conversation_costs.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/21_generate_extraneous_conversation_costs.py)
- [`22_anthropic_thinking.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/22_anthropic_thinking.py)
- [`23_responses_reasoning.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/23_responses_reasoning.py)
- [`24_planning_agent_workflow.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/24_planning_agent_workflow.py)
- [`25_agent_delegation.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/25_agent_delegation.py)
- [`26_custom_visualizer.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/26_custom_visualizer.py)
- [`27_observability_laminar.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/27_observability_laminar.py)
- [`28_ask_agent_example.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/28_ask_agent_example.py)
- [`29_llm_streaming.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/29_llm_streaming.py)
- [`30_tom_agent.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/30_tom_agent.py)
- [`31_iterative_refinement.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/31_iterative_refinement.py)
- [`32_configurable_security_policy.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/32_configurable_security_policy.py)
- [`33_hooks`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/01_standalone_sdk/33_hooks)
- [`34_critic_example.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/34_critic_example.py)
- [`35_subscription_login.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/35_subscription_login.py)
- [`36_event_json_to_openai_messages.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/36_event_json_to_openai_messages.py)
- [`37_llm_profile_store`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/01_standalone_sdk/37_llm_profile_store)
- [`38_browser_session_recording.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/38_browser_session_recording.py)
- [`39_llm_fallback.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/39_llm_fallback.py)
- [`40_acp_agent_example.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/40_acp_agent_example.py)
- [`41_task_tool_set.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/41_task_tool_set.py)
- [`42_file_based_subagents.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/42_file_based_subagents.py)
- [`43_mixed_marketplace_skills`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/01_standalone_sdk/43_mixed_marketplace_skills)
- [`44_model_switching_in_convo.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/44_model_switching_in_convo.py)
- [`45_parallel_tool_execution.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/45_parallel_tool_execution.py)
- [`46_agent_settings.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/46_agent_settings.py)
- [`47_defense_in_depth_security.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/47_defense_in_depth_security.py)
- [`48_conversation_fork.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/01_standalone_sdk/48_conversation_fork.py)

### [`02_remote_agent_server/`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/02_remote_agent_server)

- [`01_convo_with_local_agent_server.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/02_remote_agent_server/01_convo_with_local_agent_server.py)
- [`02_convo_with_docker_sandboxed_server.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/02_remote_agent_server/02_convo_with_docker_sandboxed_server.py)
- [`03_browser_use_with_docker_sandboxed_server.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/02_remote_agent_server/03_browser_use_with_docker_sandboxed_server.py)
- [`04_convo_with_api_sandboxed_server.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/02_remote_agent_server/04_convo_with_api_sandboxed_server.py)
- [`05_vscode_with_docker_sandboxed_server.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/02_remote_agent_server/05_vscode_with_docker_sandboxed_server.py)
- [`06_custom_tool`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/02_remote_agent_server/06_custom_tool)
- [`07_convo_with_cloud_workspace.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/02_remote_agent_server/07_convo_with_cloud_workspace.py)
- [`08_convo_with_apptainer_sandboxed_server.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/02_remote_agent_server/08_convo_with_apptainer_sandboxed_server.py)
- [`09_acp_agent_with_remote_runtime.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/02_remote_agent_server/09_acp_agent_with_remote_runtime.py)
- [`10_cloud_workspace_share_credentials.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/02_remote_agent_server/10_cloud_workspace_share_credentials.py)
- [`11_conversation_fork.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/02_remote_agent_server/11_conversation_fork.py)
- [`hook_scripts`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/02_remote_agent_server/hook_scripts)

### [`03_github_workflows/`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/03_github_workflows)

- [`01_basic_action`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/03_github_workflows/01_basic_action)
- [`02_pr_review`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/03_github_workflows/02_pr_review)
- [`03_todo_management`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/03_github_workflows/03_todo_management)
- [`04_datadog_debugging`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/03_github_workflows/04_datadog_debugging)
- [`05_posthog_debugging`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/03_github_workflows/05_posthog_debugging)

### [`04_llm_specific_tools/`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/04_llm_specific_tools)

- [`01_gpt5_apply_patch_preset.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/04_llm_specific_tools/01_gpt5_apply_patch_preset.py)
- [`02_gemini_file_tools.py`](https://github.com/OpenHands/software-agent-sdk/blob/main/examples/04_llm_specific_tools/02_gemini_file_tools.py)

### [`05_skills_and_plugins/`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/05_skills_and_plugins)

- [`01_loading_agentskills`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/05_skills_and_plugins/01_loading_agentskills)
- [`02_loading_plugins`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/05_skills_and_plugins/02_loading_plugins)
- [`03_managing_installed_skills`](https://github.com/OpenHands/software-agent-sdk/tree/main/examples/05_skills_and_plugins/03_managing_installed_skills)

