// BUILD_ASSETS is replaced with the compressed web export by build.mjs.
const assets = BUILD_ASSETS;

// Runs inside an opaque-origin iframe, never in the Canvas realm.
async function boot() {
  const status = document.querySelector('output');
  async function unpack(base64) {
    const bytes = Uint8Array.from(atob(base64), c => c.charCodeAt(0));
    return new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')));
  }
  addEventListener('message', async ({source, data}) => {
    if (source !== parent || !data?.assets) return;
    try {
      if (data.file && await data.file.slice(0, 4).text() !== 'GDPC') {
        throw new Error('Choose a Godot .pck file.');
      }
      const {js, wasm, pck} = data.assets;
      const script = document.createElement('script');
      script.textContent = await (await unpack(js)).text();
      document.head.append(script);
      const binary = await unpack(wasm);
      // Godot's loader appends .wasm to its base URL. Serve that one request
      // from memory instead of pointing the engine at a backend or CDN.
      window.fetch = async path => {
        if (path !== 'player.wasm') throw new Error('External resources are disabled.');
        return binary.clone();
      };
      const engine = new Engine({canvas: document.querySelector('canvas'), persistentPaths: [], executable: 'player'});
      await engine.init('player');
      const pack = data.file ? await data.file.arrayBuffer() : await (await unpack(pck)).arrayBuffer();
      await engine.preloadFile(pack, 'game.pck');
      await engine.start({args: ['--main-pack', 'game.pck', '--audio-driver', 'Dummy']});
      status.hidden = true;
    } catch (error) {
      status.textContent = `Could not start game: ${error.message}`;
    }
  });
}

export function activate(host) {
  if (host.apiVersion !== '1') throw new Error('Godot Player requires Canvas API 1.');
  return host.registerPage('player', ({container, path}) => {
    const root = document.createElement('section');
    root.className = 'oh-godot';
    container.append(root);
    if (path && path !== '/') {
      root.textContent = 'Unknown Godot Player page.';
      return () => root.remove();
    }
    root.innerHTML = `<style>
      .oh-godot {padding:clamp(12px,3vw,36px);max-width:1080px;margin:auto;color:var(--oh-foreground,#eef2f7)}
      .oh-godot header,.oh-godot footer {display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:14px}
      .oh-godot h1 {font-size:1.65rem;margin:.2em 0 .5em}.oh-godot small {color:var(--oh-muted,#a3b0c4);letter-spacing:.12em}
      .oh-godot iframe {display:block;width:100%;aspect-ratio:8/5;border:0;border-radius:12px;background:#09101a;margin:12px 0}
      .oh-godot button,.oh-godot input::file-selector-button {padding:8px 14px;border-radius:8px;background:var(--oh-surface-raised,#2c313f);border:1px solid var(--oh-border,#4b5468);color:var(--oh-contrast,white);cursor:pointer}
      .oh-godot input {max-width:100%}.oh-godot footer {font-size:.9rem;color:var(--oh-muted,#a3b0c4)}
    </style><header><div><small>GODOT PLAYER &nbsp;/&nbsp; WEB RUNTIME</small><h1>Periapsis</h1></div><button type="button">Restart demo</button></header><div class="screen"></div><footer><span>Space or tap to transmit when the satellite reaches the amber arc.</span><label>Open .pck <input type="file" accept=".pck"></label></footer>`;
    const screen = root.querySelector('.screen');
    const input = root.querySelector('input');
    function play(file) {
      const frame = document.createElement('iframe');
      frame.title = file?.name || 'Periapsis';
      frame.setAttribute('sandbox', 'allow-scripts');
      // An opaque origin cannot be named as the target; address only this frame.
      frame.addEventListener('load', () => frame.contentWindow?.postMessage({assets, file}, '*'), {once: true});
      frame.srcdoc = `<!doctype html><meta charset=utf-8><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline' 'wasm-unsafe-eval'; style-src 'unsafe-inline'; img-src data: blob:; connect-src 'none'; form-action 'none'; base-uri 'none'"><style>body{margin:0;background:#09101a;color:white;font:16px system-ui}output{position:absolute;inset:45% 0 auto;text-align:center}canvas{display:block;width:100vw;height:100vh}</style><canvas id="canvas" tabindex="0"></canvas><output>Loading Godot…</output><script>(${boot.toString()})()</script>`;
      screen.replaceChildren(frame);
      root.querySelector('h1').textContent = frame.title;
      root.querySelector('footer span').hidden = Boolean(file);
    }
    root.querySelector('button').onclick = () => { input.value = ''; play(null); };
    input.onchange = () => { if (input.files[0]) play(input.files[0]); };
    play(null);
    return () => root.remove();
  });
}
