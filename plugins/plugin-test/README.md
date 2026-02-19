# Plugin Test Tool

Test plugin loading via the OpenHands Cloud API. Launch conversations with any plugin from a marketplace, wait for the agent to respond, and verify the response matches an expected string or pattern.

## Features

- **Automated testing**: Launch conversations and verify responses programmatically
- **Flexible matching**: Substring or regex pattern matching
- **Configurable marketplace**: Test plugins from any marketplace repository
- **Detailed output**: Verbose mode for debugging API interactions
- **CI/CD ready**: Exit codes indicate pass/fail for integration into pipelines

## Quick Start

### Prerequisites

- `curl` and `jq` installed
- OpenHands API key (from [app.all-hands.dev](https://app.all-hands.dev))

### Basic Usage

```bash
export OH_API_KEY="sk-oh-your-api-key"

# Test the city-weather plugin
./scripts/test_plugin.sh \
  --plugin "plugins/city-weather" \
  --message "/city-weather:now Tokyo" \
  --expect "Weather Report"
```

### Using the Slash Command

If you have this plugin loaded, you can invoke it directly:

```
/plugin-test:test --plugin "plugins/city-weather" --message "/city-weather:now Tokyo" --expect "Weather Report"
```

---

## Command Reference

```
Usage: test_plugin.sh [OPTIONS]

Required Arguments:
  --plugin PATH       Path to plugin within the marketplace repo
  --message TEXT      Initial message to send
  --expect STRING     String or regex pattern to expect in the response

Options:
  --regex             Treat --expect as a regex pattern (default: substring)
  --open              Open the conversation in a browser when ready
  --verbose           Show detailed output including API responses
  --max-wait SECONDS  Maximum time to wait for conversation (default: 180)
  --poll SECONDS      Polling interval in seconds (default: 3)
  --help              Show help message
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OH_API_KEY` | (required) | Your OpenHands API key |
| `OPENHANDS_API_KEY` | - | Alternative name for API key (fallback) |
| `OPENHANDS_URL` | `https://app.all-hands.dev` | OpenHands Cloud URL |
| `MARKETPLACE_REPO` | `github:OpenHands/extensions` | Plugin marketplace repository |
| `MARKETPLACE_REF` | `main` | Git ref (branch/tag) for marketplace |

---

## Examples

### Test city-weather plugin

```bash
export OH_API_KEY="sk-oh-..."

./scripts/test_plugin.sh \
  --plugin "plugins/city-weather" \
  --message "/city-weather:now Tokyo" \
  --expect "Weather Report"
```

### Test magic-test plugin with regex

```bash
./scripts/test_plugin.sh \
  --plugin "plugins/magic-test" \
  --message "What happens if I say alakazam?" \
  --expect "Plugin loaded successfully" \
  --regex
```

### Test with custom marketplace

```bash
export MARKETPLACE_REPO="github:myorg/my-plugins"
export MARKETPLACE_REF="develop"

./scripts/test_plugin.sh \
  --plugin "plugins/my-plugin" \
  --message "/my-plugin:hello" \
  --expect "Hello World"
```

### Verbose mode for debugging

```bash
./scripts/test_plugin.sh \
  --plugin "plugins/city-weather" \
  --message "/city-weather:now London" \
  --expect "Temperature" \
  --verbose
```

### Open in browser after test

```bash
./scripts/test_plugin.sh \
  --plugin "plugins/city-weather" \
  --message "/city-weather:now Paris" \
  --expect "Weather" \
  --open
```

---

## CI/CD Integration

The script returns exit codes suitable for CI pipelines:

| Exit Code | Meaning |
|-----------|---------|
| 0 | Test passed - response matched expected pattern |
| 1 | Test failed - response didn't match, or error occurred |

### GitHub Actions Example

```yaml
- name: Test city-weather plugin
  env:
    OH_API_KEY: ${{ secrets.OH_API_KEY }}
  run: |
    ./plugins/plugin-test/scripts/test_plugin.sh \
      --plugin "plugins/city-weather" \
      --message "/city-weather:now Tokyo" \
      --expect "Weather Report"
```

---

## How It Works

1. **Create Conversation**: POST to `/api/v1/app-conversations` with the plugin spec
2. **Wait for Sandbox**: Poll `/api/v1/app-conversations/start-tasks/search` until status is `READY`
3. **Fetch Events**: Query the Agent Server for conversation events
4. **Verify Response**: Check if the agent's response matches the expected pattern

### Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   test_plugin   │────▶│   App Server    │────▶│  Agent Server   │
│     script      │     │  (Cloud URL)    │     │  (In Sandbox)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                      │                        │
        │ 1. Create conv       │ 2. Start sandbox       │
        │    with plugin       │    load plugin         │
        │                      │                        │
        │ 3. Poll for ready    │                        │
        │                      │                        │ 4. Agent runs,
        │ 5. Fetch events ◀────────────────────────────│    responds
        │                                               │
        │ 6. Verify response                            │
        └───────────────────────────────────────────────┘
```

---

## Plugin Structure

```
plugin-test/
├── .claude-plugin/
│   └── plugin.json      # Plugin manifest
├── commands/
│   └── test.md          # Slash command definition
├── scripts/
│   └── test_plugin.sh   # Test execution script
└── README.md
```

---

## Related Resources

- [OpenHands Cloud](https://app.all-hands.dev)
- [OpenHands API Documentation](https://docs.openhands.dev)
- [Plugin Marketplace](https://github.com/OpenHands/extensions)
