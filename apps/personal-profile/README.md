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

## Install in Agent Canvas

In **Customize → Apps → Add app**, paste this folder's URL at the commit you reviewed as **App source**:

```text
https://github.com/OpenHands/extensions/tree/<commit>/apps/personal-profile
```

The form splits it into source `https://github.com/OpenHands/extensions`, **Ref** `<commit>` and **Path** `apps/personal-profile`. The App installs disabled. Review its source at that revision, switch it on and confirm **Enable trusted app**, then open **Profile** from the sidebar. Canvas installs a copy, so after a change use **Update** on its card, or uninstall and reinstall.

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

## Source

Moved from [OpenHands/canvas-apps](https://github.com/OpenHands/canvas-apps/tree/b83068fdce5ec7f85c07b8aefa15d413982059d0/personal-profile) at `b83068fdce5ec7f85c07b8aefa15d413982059d0`, keeping the MIT [LICENSE](LICENSE). Installations made from canvas-apps do not follow this move: uninstall them and install again from this registry.
