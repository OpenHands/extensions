---
allowed-tools: Bash(*)
argument-hint: --plugin <path> --message <text> --expect <pattern> [--regex] [--open]
description: Test plugin loading via OpenHands Cloud API - creates a conversation with the specified plugin and verifies the response
---

# Test Plugin Loading

Launch a conversation with a specified plugin loaded via the OpenHands Cloud API, wait for the agent response, and verify it matches an expected string or pattern.

## Instructions

Run the test script with the provided arguments: **$ARGUMENTS**

```bash
# Navigate to the plugin-test scripts directory and run the test
cd /path/to/extensions/plugins/plugin-test/scripts

# Run the test with the provided arguments
./test_plugin.sh $ARGUMENTS
```

If the script is not available locally, you can download and run it:

```bash
curl -sL "https://raw.githubusercontent.com/OpenHands/extensions/main/plugins/plugin-test/scripts/test_plugin.sh" -o /tmp/test_plugin.sh
chmod +x /tmp/test_plugin.sh
/tmp/test_plugin.sh $ARGUMENTS
```

## Required Environment Variables

Before running, ensure these are set:

```bash
export OH_API_KEY="sk-oh-your-api-key"
# Alternative: OPENHANDS_API_KEY is also accepted as a fallback

# Optional: override defaults
export OPENHANDS_URL="https://app.all-hands.dev"
export MARKETPLACE_REPO="github:OpenHands/extensions"
export MARKETPLACE_REF="main"
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `--plugin PATH` | Yes | Path to plugin within marketplace (e.g., `plugins/city-weather`) |
| `--message TEXT` | Yes | Initial message to send (e.g., `/city-weather:now Tokyo`) |
| `--expect STRING` | Yes | String or regex pattern to expect in the response |
| `--regex` | No | Treat `--expect` as a regex pattern |
| `--open` | No | Open the conversation in a browser when ready |
| `--verbose` | No | Show detailed debug output |

## Example Usage

```bash
# Test the city-weather plugin
/plugin-test:test --plugin "plugins/city-weather" --message "/city-weather:now Tokyo" --expect "Weather Report"

# Test the magic-test plugin with regex matching
/plugin-test:test --plugin "plugins/magic-test" --message "alakazam" --expect "Plugin loaded successfully" --regex

# Test with verbose output and open browser
/plugin-test:test --plugin "plugins/city-weather" --message "/city-weather:now London" --expect "Temperature" --verbose --open
```

## Expected Output

On success:
```
=== Plugin Test ===

Configuration:
  OpenHands URL:  https://app.all-hands.dev
  Marketplace:    github:OpenHands/extensions (ref: main)
  Plugin:         plugins/city-weather
  Message:        /city-weather:now Tokyo
  Expect:         Weather Report

[INFO] Creating conversation with plugin: plugins/city-weather
[INFO] Task created: abc123...
[INFO] Waiting for conversation to start (max 180s)...
[PASS] Conversation ready: def456...
[INFO] Fetching conversation events...
[INFO] Agent responded (1234 chars)
[PASS] Response matches expected pattern: "Weather Report"

=== TEST PASSED ===

View conversation:
  https://app.all-hands.dev/conversations/def456...
```

On failure, the script exits with code 1 and shows the actual response for debugging.

## Notes

- Sandbox startup typically takes 30-90 seconds
- The script polls the API every 3 seconds by default
- Maximum wait time is 180 seconds (configurable with `--max-wait`)
- Use `--verbose` to see full API responses for debugging
