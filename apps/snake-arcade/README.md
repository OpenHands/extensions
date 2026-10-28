# Snake Arcade

Snake Arcade is a dependency-free Agent Canvas extension for a quick, colorful
game of Snake. It supports arrow keys, WASD, touch controls, pause/resume, a
responsive game board, and a high score saved separately for each Canvas
backend.

The checked-in `extension.js` is the complete browser ESM entrypoint; there is
no runtime build step.

## Test

```sh
npm install
npm test
```

For a standalone visual preview, serve this directory from any local static
server and open `preview.html`. The actual Canvas runtime entrypoint remains
the self-contained `extension.js` file.

## Install in Agent Canvas

In **Customize → Apps → Add app**, paste this folder's URL at the commit you reviewed as **App source**:

```text
https://github.com/OpenHands/extensions/tree/<commit>/apps/snake-arcade
```

The form splits it into source `https://github.com/OpenHands/extensions`, **Ref** `<commit>` and **Path** `apps/snake-arcade`. The App installs disabled. Review its source at that revision, switch it on and confirm **Enable trusted app**, then open **Snake** from the sidebar. Canvas installs a copy, so after a change use **Update** on its card, or uninstall and reinstall.

## Verify in Canvas

1. Start a game with **Enter**, **Space**, or the **New game** button.
2. Steer with arrow keys, WASD, or the on-screen direction pad.
3. Pause with **Space** or **P** and confirm the game resumes cleanly.
4. Reload the page and confirm the high score remains.
5. Disable the extension and confirm its navigation item and keyboard handlers
   disappear; re-enable it and confirm it mounts once.

## Source

Moved from [OpenHands/canvas-apps](https://github.com/OpenHands/canvas-apps/tree/b83068fdce5ec7f85c07b8aefa15d413982059d0/snake-arcade) at `b83068fdce5ec7f85c07b8aefa15d413982059d0`, keeping the MIT [LICENSE](LICENSE). Installations made from canvas-apps do not follow this move: uninstall them and install again from this registry.
