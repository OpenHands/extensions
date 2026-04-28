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

    class _Stub:
        """Generic stub that accepts any arguments."""
        def __init__(self, *args, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

        def model_copy(self, update=None):
            copied = _Stub(**self.__dict__)
            if update:
                for k, v in update.items():
                    setattr(copied, k, v)
            return copied

    sdk = types.ModuleType("openhands.sdk")
    sdk.LLM = _Stub
    sdk.Agent = _Stub
    sdk.AgentContext = _Stub
    sdk.Conversation = _Stub
    sdk.Tool = _Stub

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

    class _Skill:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    sdk_context = _ensure_package("openhands.sdk.context")
    sdk_context.Skill = _Skill
    sys.modules["openhands.sdk.context"] = sdk_context

    sdk_skills = types.ModuleType("openhands.sdk.skills")
    sdk_skills.load_project_skills = lambda cwd: []
    sys.modules["openhands.sdk.skills"] = sdk_skills

    conversation = types.ModuleType("openhands.sdk.conversation")
    conversation.get_agent_final_response = lambda events: ""
    sys.modules["openhands.sdk.conversation"] = conversation

    git_utils = types.ModuleType("openhands.sdk.git.utils")
    git_utils.run_git_command = lambda command, repo_dir: "deadbeef"
    sys.modules["openhands.sdk.git.utils"] = git_utils

    sdk_plugin = types.ModuleType("openhands.sdk.plugin")
    sdk_plugin.PluginSource = _Stub
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


def test_register_sub_agents_completes_without_error():
    """Smoke test: _register_sub_agents() runs without raising."""
    module = _load_agent_script_module()
    # _register_sub_agents calls register_agent (stubbed as a no-op)
    module._register_sub_agents()


def test_create_file_reviewer_agent_factory_is_callable():
    """Smoke test: _create_file_reviewer_agent accepts an LLM and is callable."""
    module = _load_agent_script_module()
    # The factory should be callable; with our stubs LLM is just `object`
    result = module._create_file_reviewer_agent(object())
    # Agent stub is `object`, so the factory should return *something*
    assert result is not None


def test_create_conversation_uses_sdk_project_skill_loader(tmp_path, monkeypatch):
    """PR review delegates project skill discovery to the SDK."""
    module = _load_agent_script_module()
    monkeypatch.chdir(tmp_path)

    project_skill = module.Skill(
        name="custom-codereview-guide",
        content="Review in Chinese",
        is_agentskills_format=True,
    )
    monkeypatch.setattr(module, "load_project_skills", lambda cwd: [project_skill])

    config = {
        "review_agent_mode": "openhands",
        "model": "test-model",
        "api_key": "test-key",
        "base_url": "",
        "use_sub_agents": False,
    }

    conversation = module.create_conversation(config, secrets={})

    assert conversation.agent.agent_context.skills == [project_skill]
