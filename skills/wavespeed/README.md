# WaveSpeed

Generate and edit AI media — image, video, audio, 3D — on the [WaveSpeed](https://wavespeed.ai) platform from OpenHands, through the open-source [`wavespeed` CLI](https://github.com/WaveSpeedAI/wavespeed-cli).

The skill teaches the agent the find → inspect → run pattern: search the live model catalog, read the selected model's input schema, quote the price, run it with `--json`, and upload local files with the `@path` marker. The agent never asks the user to paste an API key into the chat; `wavespeed login` (or `WAVESPEED_API_KEY` in the sandbox environment) handles auth.

## Setup

```bash
npm install -g @wavespeed/cli
wavespeed login          # or export WAVESPEED_API_KEY=...
```

## Example prompts

- "Generate a 16:9 hero image of a cyberpunk skyline at golden hour."
- "Animate ./hero.jpg into a 5-second clip with subtle parallax."
- "Replace the background of ./product.png with a sunlit kitchen, and tell me the cost first."

## More

Per-model skills (Seedream, Seedance, Veo 3.1, Wan, Nano Banana, MiniMax Speech, upscalers, face swap, watermark removal) and the `@wavespeed/mcp` server declaration live in [WaveSpeedAI/agent-skills](https://github.com/WaveSpeedAI/agent-skills).
