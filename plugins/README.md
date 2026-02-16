# Plugins Directory

This directory contains OpenHands plugins - extensions with executable code components such as hooks and advanced scripts.

## What are Plugins?

Plugins differ from skills in that they include executable code that can hook into OpenHands workflows:

- **hooks/**: Scripts that run at specific points in the agent lifecycle
- **scripts/**: Executable utilities that extend agent capabilities

## Structure

Each plugin follows the same structure as a skill but with additional executable components:

```
plugins/
└── my-plugin/
    ├── SKILL.md          # Plugin definition and documentation
    ├── hooks/            # Lifecycle hooks (optional)
    │   ├── pre-task.sh
    │   └── post-task.sh
    └── scripts/          # Utility scripts (optional)
        └── helper.py
```

## Contributing

See the main [README](../README.md) for contribution guidelines.

