import importlib.util
import sys
import types
from pathlib import Path


def _ensure_package(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        sys.modules[name] = module
    return module


def _load_agent_script_module():
    _ensure_package("openhands")
    _ensure_package("openhands.sdk")
    _ensure_package("openhands.sdk.context")
    _ensure_package("openhands.sdk.git")
    _ensure_package("openhands.tools")
    _ensure_package("openhands.tools.preset")

    lmnr = types.ModuleType("lmnr")

    class _Laminar:
        @staticmethod
        def get_trace_id():
            return None

        @staticmethod
        def get_laminar_span_context():
            return None

        @staticmethod
        def flush():
            return None

        @staticmethod
        def start_as_current_span(*args, **kwargs):
            class _ContextManager:
                def __enter__(self):
                    return None

                def __exit__(self, exc_type, exc, tb):
                    return False

            return _ContextManager()

        @staticmethod
        def set_trace_metadata(metadata):
            return None

    lmnr.Laminar = _Laminar
    sys.modules["lmnr"] = lmnr

    sdk = types.ModuleType("openhands.sdk")
    sdk.LLM = object
    sdk.Agent = object
    sdk.AgentContext = object
    sdk.Conversation = object
    sdk.Tool = object

    class _Logger:
        def info(self, *args, **kwargs):
            return None

        def warning(self, *args, **kwargs):
            return None

        def error(self, *args, **kwargs):
            return None

        def debug(self, *args, **kwargs):
            return None

    sdk.get_logger = lambda name: _Logger()
    sys.modules["openhands.sdk"] = sdk

    sdk_context = _ensure_package("openhands.sdk.context")
    sdk_context.Skill = object
    sys.modules["openhands.sdk.context"] = sdk_context

    context_skills = types.ModuleType("openhands.sdk.context.skills")
    context_skills.load_project_skills = lambda cwd: []
    sys.modules["openhands.sdk.context.skills"] = context_skills

    conversation = types.ModuleType("openhands.sdk.conversation")
    conversation.get_agent_final_response = lambda events: ""
    sys.modules["openhands.sdk.conversation"] = conversation

    git_utils = types.ModuleType("openhands.sdk.git.utils")
    git_utils.run_git_command = lambda command, repo_dir: "deadbeef"
    sys.modules["openhands.sdk.git.utils"] = git_utils

    sdk_plugin = types.ModuleType("openhands.sdk.plugin")
    sdk_plugin.PluginSource = object
    sys.modules["openhands.sdk.plugin"] = sdk_plugin

    tools_delegate = types.ModuleType("openhands.tools.delegate")
    tools_delegate.DelegationVisualizer = object
    sys.modules["openhands.tools.delegate"] = tools_delegate

    # register_agent lives in openhands.sdk, not openhands.tools.delegate
    sdk.register_agent = lambda **kwargs: None

    tools_task = types.ModuleType("openhands.tools.task")

    class _TaskToolSet:
        name = "TaskToolSet"

    tools_task.TaskToolSet = _TaskToolSet
    sys.modules["openhands.tools.task"] = tools_task

    tools_preset = types.ModuleType("openhands.tools.preset.default")
    tools_preset.get_default_condenser = lambda llm: None
    tools_preset.get_default_tools = lambda enable_browser=False: []
    sys.modules["openhands.tools.preset.default"] = tools_preset

    # Clear any cached 'prompt' module so agent_script.py picks up the
    # correct prompt.py from its own scripts/ directory (not the one from
    # another plugin like release-notes).
    sys.modules.pop("prompt", None)

    script_path = (
        Path(__file__).parent.parent
        / "plugins"
        / "pr-review"
        / "scripts"
        / "agent_script.py"
    )
    spec = importlib.util.spec_from_file_location("pr_review_agent_script", script_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["pr_review_agent_script"] = module
    spec.loader.exec_module(module)
    return module


def test_get_review_comment_body_uses_body_text_for_empty_suggestion_block():
    module = _load_agent_script_module()

    body = module._get_review_comment_body(
        {
            "body": "```suggestion\n```",
            "bodyText": (
                "Suggested change\n"
                "      \n"
                "- Do **NOT** approve the PR.\n"
                "      \n"
                "- Leave a **COMMENT** review with the exact package details."
            ),
        }
    )

    assert body == (
        "Suggested change\n\n"
        "- Do **NOT** approve the PR.\n\n"
        "- Leave a **COMMENT** review with the exact package details."
    )


def test_format_thread_includes_rendered_suggestion_text_in_review_context():
    module = _load_agent_script_module()

    lines = module._format_thread(
        {
            "path": ".agents/skills/custom-codereview-guide.md",
            "line": 96,
            "isOutdated": False,
            "isResolved": False,
            "comments": {
                "nodes": [
                    {
                        "author": {"login": "enyst"},
                        "body": "```suggestion\n```",
                        "bodyText": (
                            "Suggested change\n"
                            "\n"
                            "- Do **NOT** approve the PR.\n"
                            "\n"
                            "- Explain that Dependabot ignores the freshness guardrail."
                        ),
                    }
                ]
            },
        }
    )

    formatted = "\n".join(lines)

    assert "**.agents/skills/custom-codereview-guide.md:96** - ⚠️ UNRESOLVED" in formatted
    assert "Suggested change" in formatted
    assert "- Do **NOT** approve the PR." in formatted
    assert "Dependabot ignores the freshness guardrail" in formatted
    assert "```suggestion" not in formatted
