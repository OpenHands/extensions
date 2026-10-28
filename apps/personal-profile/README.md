# Personal Profile

A dependency-free Canvas Extension that renders personal activity dashboards as
contribution graphs (heatmaps) and usage stats.

## Features

- **OpenHands conversation heatmap** — fetches all conversations via the
  authenticated Agent Server `/api/conversations/search` endpoint and bins
  activity by day into a 53-week GitHub-style contribution grid.
- **GitHub integration** — enter a GitHub username in the settings panel to
  fetch public profile data and recent events from the GitHub REST API. The
  events are rendered as a second contribution heatmap. The username is
  persisted in `localStorage`.
- **LLM usage stats** — aggregates token counts (prompt, completion, total)
  from conversation events that include `llm_metrics`, `token_usage`, or
  `usage` fields. Breaks down usage by model.

## Installation

Install from **Customize → Extensions** using:

```text
personal-profile
```

Or from a Git repository:

```text
source: github:owner/repository
repo_path: personal-profile
```

The extension remains disabled after installation. Enable it to run the
trusted same-realm code.

## Verification

1. Enable the extension and open the **Profile** nav item.
2. Confirm the OpenHands conversation heatmap loads.
3. Enter a GitHub username, click **Save**, and confirm the GitHub profile
   card and activity heatmap appear.
4. Click **Clear** to remove the GitHub username.
5. Disable the extension and confirm the nav item and page disappear.

## Development

```sh
npm install
npm test
```

The checked-in `extension.js` is the self-contained browser ESM entrypoint —
no build step is required.
