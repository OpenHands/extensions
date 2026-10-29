# Canvas Pulse

Canvas Pulse is a dependency-free Canvas Extension that turns `/server_info`
into a live operational dashboard. It demonstrates the complete host API v1
page workflow:

- registering a sidebar page;
- making an authenticated Agent Server request;
- navigating to a nested extension route; and
- cleaning up polling when the page unmounts.

The checked-in `extension.js` is already a self-contained browser ESM bundle.

## Install in Agent Canvas

In **Customize → Apps → Add app**, paste this folder's URL at the commit you reviewed as **App source**:

```text
https://github.com/OpenHands/extensions/tree/<commit>/apps/canvas-pulse
```

The form splits it into source `https://github.com/OpenHands/extensions`, **Ref** `<commit>` and **Path** `apps/canvas-pulse`. The App installs disabled. Review its source at that revision, switch it on and confirm **Enable trusted app**, then open **Canvas Pulse** from the sidebar. Canvas installs a copy, so after a change use **Update** on its card, or uninstall and reinstall.

## Source

Moved from [OpenHands/canvas-apps](https://github.com/OpenHands/canvas-apps/tree/b83068fdce5ec7f85c07b8aefa15d413982059d0/canvas-pulse) at `b83068fdce5ec7f85c07b8aefa15d413982059d0`, keeping the MIT [LICENSE](LICENSE). Installations made from canvas-apps do not follow this move: uninstall them and install again from this registry.
