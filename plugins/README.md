# Plugins Directory

This directory contains OpenHands plugins - extensions with executable code components such as hooks and advanced scripts.

## Launch a plugin

- `city-weather` — [![Launch City Weather](https://img.shields.io/badge/Launch%20City%20Weather-blue?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0xIDE1aC0ydi02aDJ2NnptMC04aC0yVjdoMnYyeiIvPjwvc3ZnPg==)](https://app.all-hands.dev/launch?plugins=W3sic291cmNlIjogImdpdGh1YjpPcGVuSGFuZHMvZXh0ZW5zaW9ucyIsICJyZWYiOiAibWFpbiIsICJyZXBvX3BhdGgiOiAicGx1Z2lucy9jaXR5LXdlYXRoZXIifV0=)
- `cobol-modernization` — [![Launch COBOL Modernization](https://img.shields.io/badge/Launch%20COBOL%20Modernization-blue?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0xIDE1aC0ydi02aDJ2NnptMC04aC0yVjdoMnYyeiIvPjwvc3ZnPg==)](https://app.all-hands.dev/launch?plugins=W3sic291cmNlIjogImdpdGh1YjpPcGVuSGFuZHMvZXh0ZW5zaW9ucyIsICJyZWYiOiAibWFpbiIsICJyZXBvX3BhdGgiOiAicGx1Z2lucy9jb2JvbC1tb2Rlcm5pemF0aW9uIn1d)
- `migration-scoring` — [![Launch Migration Scoring](https://img.shields.io/badge/Launch%20Migration%20Scoring-blue?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0xIDE1aC0ydi02aDJ2NnptMC04aC0yVjdoMnYyeiIvPjwvc3ZnPg==)](https://app.all-hands.dev/launch?plugins=W3sic291cmNlIjogImdpdGh1YjpPcGVuSGFuZHMvZXh0ZW5zaW9ucyIsICJyZWYiOiAibWFpbiIsICJyZXBvX3BhdGgiOiAicGx1Z2lucy9taWdyYXRpb24tc2NvcmluZyJ9XQ==)
- `pr-review` — [![Launch PR Review](https://img.shields.io/badge/Launch%20PR%20Review-blue?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0xIDE1aC0ydi02aDJ2NnptMC04aC0yVjdoMnYyeiIvPjwvc3ZnPg==)](https://app.all-hands.dev/launch?plugins=W3sic291cmNlIjogImdpdGh1YjpPcGVuSGFuZHMvZXh0ZW5zaW9ucyIsICJyZWYiOiAibWFpbiIsICJyZXBvX3BhdGgiOiAicGx1Z2lucy9wci1yZXZpZXcifV0=)
- `vulnerability-remediation` — [![Launch Vulnerability Remediation](https://img.shields.io/badge/Launch%20Vulnerability%20Remediation-blue?logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0xIDE1aC0ydi02aDJ2NnptMC04aC0yVjdoMnYyeiIvPjwvc3ZnPg==)](https://app.all-hands.dev/launch?plugins=W3sic291cmNlIjogImdpdGh1YjpPcGVuSGFuZHMvZXh0ZW5zaW9ucyIsICJyZWYiOiAibWFpbiIsICJyZXBvX3BhdGgiOiAicGx1Z2lucy92dWxuZXJhYmlsaXR5LXJlbWVkaWF0aW9uIn1d)

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

