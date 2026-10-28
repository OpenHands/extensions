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

## Install

In **Customize → Extensions**, add the repository containing this directory and
set **Repository path** to:

```text
snake-arcade
```

Installation leaves the extension disabled. Review its source, enable it, then
open **Snake** in the Canvas navigation. The route is
`/extensions/snake-arcade/snake` and the rules screen is available at the nested
route `/extensions/snake-arcade/snake/how-to-play`.

## Verify in Canvas

1. Start a game with **Enter**, **Space**, or the **New game** button.
2. Steer with arrow keys, WASD, or the on-screen direction pad.
3. Pause with **Space** or **P** and confirm the game resumes cleanly.
4. Reload the page and confirm the high score remains.
5. Disable the extension and confirm its navigation item and keyboard handlers
   disappear; re-enable it and confirm it mounts once.
