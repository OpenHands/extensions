# Godot Player

Play *Periapsis* in Agent Canvas. Press Space or tap when the satellite crosses the amber arc. Link eight relays before missing three transmissions. The next pulse after a win or loss starts a new run.

**Open .pck** replaces the demo with a local game pack. Choose a trusted Godot 4.4.1 pack for the Compatibility renderer and single-thread Web template. Files stay in the browser. This silent player does not support persistent saves, network resources, C#, or GDExtensions. It requires WebGL 2, WebAssembly and `DecompressionStream`.

## Install

In **Apps for Agent Canvas → Add app**, select `https://github.com/OpenHands/extensions`, the ref containing the app, and repo path `apps/godot-player`. Review and enable it, then open `/extensions/godot-player/play`. The entrypoint includes the compressed engine and game; no CDN, sidecar, or local Godot install is needed to play. Game code runs in a scripts-only sandboxed iframe, not in the trusted Canvas page.

## Rebuild

From this directory, with Godot 4.4.1 and its matching official export templates installed:

```sh
mkdir -p /tmp/periapsis-web
godot --headless --path demo --import
godot --headless --path demo --script "$PWD/tests/relay.gd"
godot --headless --path demo --export-release Web /tmp/periapsis-web/index.html
node build.mjs /tmp/periapsis-web/index
node ../../skills/canvas-extension-api/scripts/validate-extension.mjs .
```

`build.mjs` combines `src/player.js` with the export's loader, WASM and pack into `extension.js`. For a browser check, open the app, transmit, load `/tmp/periapsis-web/index.pck`, then choose **Restart demo**. See `Godot-LICENSE.txt` and `Godot-COPYRIGHT.txt` for engine and third-party notices.
