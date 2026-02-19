# City Weather Plugin

Get current weather, time, and precipitation forecast for any city worldwide using the free [Open-Meteo API](https://open-meteo.com/).

This plugin is also useful for **testing plugin loading** in OpenHands Cloud and the Software Agent SDK.

## Features

- **Slash command**: `/city-weather:now <city>`
- **Temperature** in both Fahrenheit and Celsius
- **Current time** in the city's local timezone
- **Precipitation forecast** for the next 4 hours
- **No API key required** — uses the free Open-Meteo API

## Usage

```
/city-weather:now New York
/city-weather:now Tokyo
/city-weather:now London
```

### Example Output

```
City Weather Report for Tokyo, Japan

- Current Time: 2025-02-19 14:30 JST
- Temperature: 52°F / 11°C
- Current Precipitation: 0.0 mm

Precipitation Forecast (Next 4 Hours):
| Time  | Probability |
|-------|-------------|
| 15:00 | 10%         |
| 16:00 | 15%         |
| 17:00 | 20%         |
| 18:00 | 25%         |
```

---

## Testing Plugin Loading

This plugin can be used to verify that plugin loading works correctly across different OpenHands platforms.

### OpenHands Cloud (app.all-hands.dev)

Test the plugin loading endpoint at [app.all-hands.dev](https://app.all-hands.dev):

```bash
curl -X POST "https://app.all-hands.dev/api/v1/app-conversations" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "initial_message": {
      "content": [{"type": "text", "text": "/city-weather:now Tokyo"}]
    },
    "plugins": [{
      "source": "github:OpenHands/extensions",
      "ref": "main",
      "repo_path": "plugins/city-weather"
    }]
  }'
```

The response includes a conversation ID. Poll `/api/v1/app-conversations/search` until `sandbox_status` is `"RUNNING"`, then view at:

```
https://app.all-hands.dev/conversations/{conversation_id}
```

> **Note:** Sandbox startup typically takes 30-90 seconds.

### Software Agent SDK (1.10.0+)

```python
from openhands.sdk import Agent, Conversation, LLM
from openhands.sdk.plugin import PluginSource
from openhands.sdk.tool import Tool
from openhands.tools.terminal import TerminalTool

llm = LLM(model="anthropic/claude-sonnet-4-20250514", api_key=SecretStr("..."))
agent = Agent(llm=llm, tools=[Tool(name=TerminalTool.name)])

conversation = Conversation(
    agent=agent,
    plugins=[
        PluginSource(
            source="github:OpenHands/extensions",
            ref="main",
            repo_path="plugins/city-weather"
        )
    ]
)

conversation.send_message("/city-weather:now Tokyo")
conversation.run()
```

---

## Plugin Structure

This plugin follows the [Claude Code plugin marketplace format](https://code.claude.com/docs/en/plugin-marketplaces):

```
city-weather/
├── .claude-plugin/
│   └── plugin.json      # Plugin manifest
├── commands/
│   └── now.md           # Slash command definition
└── README.md
```

### How It Works

1. The `/city-weather:now` slash command is converted to a `KeywordTrigger` skill
2. When triggered, the agent receives instructions to:
   - Call the Open-Meteo Geocoding API to find city coordinates
   - Call the Open-Meteo Weather API to fetch current conditions and forecast
   - Format and present the results

The `$ARGUMENTS` placeholder in the command captures user input (e.g., "Tokyo").

---

## API Reference

This plugin uses two Open-Meteo endpoints:

| Endpoint | Purpose |
|----------|---------|
| `geocoding-api.open-meteo.com/v1/search` | Convert city name to coordinates |
| `api.open-meteo.com/v1/forecast` | Fetch weather data |

Both APIs are free and require no authentication.

---

## Related Resources

- [OpenHands SDK Plugin Documentation](https://docs.openhands.dev/sdk/guides/plugins)
- [OpenHands Cloud](https://app.all-hands.dev)
- [Open-Meteo API Documentation](https://open-meteo.com/en/docs)
