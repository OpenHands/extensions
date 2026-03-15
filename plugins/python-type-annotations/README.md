# Python Type Annotations Plugin

A simple plugin that instructs the agent to add valid Python type annotations to files or directories.

## Features

- Adds type annotations to function parameters and return types
- Annotates class attributes and instance variables
- Uses modern Python 3.9+ syntax (`list[T]` instead of `List[T]`)
- Validates syntax after making changes

## Usage

### With OpenHands CLI

```bash
openhands run \
  --plugin github:OpenHands/extensions/plugins/python-type-annotations \
  --prompt "Add type annotations to all Python files in src/"
```

### With OpenHands SDK

```python
from openhands.sdk import Agent, Conversation, LLM
from openhands.sdk.plugin import PluginSource

conversation = Conversation(
    agent=Agent(llm=LLM(model="anthropic/claude-sonnet-4-20250514")),
    plugins=[
        PluginSource(
            source="github:OpenHands/extensions",
            ref="main",
            repo_path="plugins/python-type-annotations"
        )
    ]
)

conversation.send_message("Add type annotations to hello.py")
conversation.run()
```

## Examples

See the `examples/basic/` directory for a before/after example:

- `before/hello.py` - Python code without type annotations
- `after/hello.py` - Same code with type annotations added

## Testing

The `workflows/update-example.yml` GitHub Action can be triggered manually to regenerate the `after/` example using the current plugin and OpenHands CLI.

## Plugin Structure

```
python-type-annotations/
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── type-annotations/
│       └── SKILL.md
├── examples/
│   └── basic/
│       ├── prompt.md
│       ├── before/
│       │   └── hello.py
│       └── after/
│           └── hello.py
├── workflows/
│   └── update-example.yml
└── README.md
```
