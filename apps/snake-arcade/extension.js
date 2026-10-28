const GRID_SIZE = 22;
const START_DELAY_MS = 138;
const MIN_DELAY_MS = 62;
const SCORE_PER_SNACK = 10;
const ROOT_ROUTE = "/extensions/snake-arcade/snake";

const DIRECTIONS = Object.freeze({
  up: Object.freeze({ x: 0, y: -1 }),
  down: Object.freeze({ x: 0, y: 1 }),
  left: Object.freeze({ x: -1, y: 0 }),
  right: Object.freeze({ x: 1, y: 0 }),
});

const KEY_DIRECTIONS = Object.freeze({
  ArrowUp: "up",
  w: "up",
  W: "up",
  ArrowDown: "down",
  s: "down",
  S: "down",
  ArrowLeft: "left",
  a: "left",
  A: "left",
  ArrowRight: "right",
  d: "right",
  D: "right",
});

const STYLE = `
  .snake-arcade {
    --snake-ink: var(--oh-foreground, #f8f8ff);
    --snake-muted: var(--oh-text-secondary, #a8abc2);
    --snake-panel: color-mix(in srgb, var(--oh-surface, #17172a) 90%, transparent);
    --snake-line: color-mix(in srgb, var(--oh-border, #55556c) 74%, transparent);
    min-height: 100%;
    box-sizing: border-box;
    padding: clamp(1rem, 3vw, 2.5rem);
    overflow: hidden;
    color: var(--snake-ink);
    background:
      radial-gradient(circle at 9% 3%, rgba(125, 92, 255, .23), transparent 29rem),
      radial-gradient(circle at 91% 11%, rgba(31, 231, 170, .13), transparent 26rem),
      var(--oh-background, #0b0b15);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  }
  .snake-arcade * { box-sizing: border-box; }
  .snake-arcade__shell { width: min(1040px, 100%); margin: 0 auto; }
  .snake-arcade__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem; margin-bottom: 1.2rem; }
  .snake-arcade__brand { display: flex; align-items: center; gap: .85rem; }
  .snake-arcade__mark { display: grid; width: 2.75rem; height: 2.75rem; place-items: center; border: 1px solid rgba(176, 255, 75, .5); border-radius: .9rem; color: #b8ff4f; background: rgba(184, 255, 79, .1); box-shadow: inset 0 0 1.2rem rgba(184, 255, 79, .08); font-size: 1.35rem; }
  .snake-arcade__eyebrow { margin: 0 0 .2rem; color: #b8ff4f; font-size: .66rem; font-weight: 800; letter-spacing: .16em; text-transform: uppercase; }
  .snake-arcade__title { margin: 0; font-size: clamp(1.45rem, 4vw, 2.15rem); line-height: 1; letter-spacing: -.045em; }
  .snake-arcade__header-action, .snake-arcade__button, .snake-arcade__pad-button {
    appearance: none;
    border: 1px solid var(--snake-line);
    color: var(--snake-ink);
    background: var(--snake-panel);
    font: inherit;
    cursor: pointer;
    transition: transform 120ms ease, border-color 120ms ease, background 120ms ease;
  }
  .snake-arcade__header-action { padding: .62rem .8rem; border-radius: .7rem; color: var(--snake-muted); font-size: .76rem; font-weight: 700; }
  .snake-arcade__header-action:hover, .snake-arcade__button:hover, .snake-arcade__pad-button:hover { border-color: rgba(184, 255, 79, .58); background: color-mix(in srgb, var(--snake-panel) 86%, #b8ff4f 14%); }
  .snake-arcade__header-action:focus-visible, .snake-arcade__button:focus-visible, .snake-arcade__pad-button:focus-visible, .snake-arcade__game:focus-visible { outline: 3px solid #b8ff4f; outline-offset: 3px; }
  .snake-arcade__header-action:active, .snake-arcade__button:active, .snake-arcade__pad-button:active { transform: translateY(1px); }
  .snake-arcade__layout { display: grid; grid-template-columns: minmax(0, 1fr) minmax(13.5rem, .37fr); gap: 1rem; align-items: start; }
  .snake-arcade__game, .snake-arcade__side, .snake-arcade__rules { border: 1px solid var(--snake-line); border-radius: 1rem; background: var(--snake-panel); box-shadow: 0 1.2rem 4rem rgba(0, 0, 0, .16); }
  .snake-arcade__game { min-width: 0; padding: clamp(.7rem, 2vw, 1rem); }
  .snake-arcade__stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .5rem; margin-bottom: .75rem; }
  .snake-arcade__stat { min-width: 0; padding: .72rem .8rem; border: 1px solid rgba(133, 136, 169, .19); border-radius: .72rem; background: rgba(8, 8, 18, .28); }
  .snake-arcade__stat-label { display: block; color: var(--snake-muted); font-size: .61rem; font-weight: 800; letter-spacing: .1em; text-transform: uppercase; }
  .snake-arcade__stat-value { display: block; margin-top: .22rem; overflow: hidden; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: clamp(1rem, 3vw, 1.32rem); font-weight: 800; text-overflow: ellipsis; white-space: nowrap; }
  .snake-arcade__board-wrap { position: relative; overflow: hidden; border: 1px solid rgba(184, 255, 79, .18); border-radius: .85rem; background: #090a12; box-shadow: inset 0 0 3rem rgba(34, 255, 163, .035); }
  .snake-arcade__canvas { display: block; width: 100%; aspect-ratio: 1; touch-action: none; }
  .snake-arcade__overlay { position: absolute; inset: 0; display: grid; place-items: center; padding: 1rem; background: rgba(5, 6, 13, .66); backdrop-filter: blur(4px); }
  .snake-arcade__overlay[hidden] { display: none; }
  .snake-arcade__overlay-card { width: min(22rem, 92%); padding: 1.35rem; border: 1px solid rgba(184, 255, 79, .32); border-radius: 1rem; text-align: center; background: rgba(15, 16, 29, .92); box-shadow: 0 1rem 3rem rgba(0, 0, 0, .35); }
  .snake-arcade__overlay-kicker { margin: 0 0 .3rem; color: #ff75c3; font-size: .63rem; font-weight: 850; letter-spacing: .13em; text-transform: uppercase; }
  .snake-arcade__overlay-title { margin: 0; font-size: clamp(1.35rem, 4vw, 2rem); letter-spacing: -.04em; }
  .snake-arcade__overlay-copy { margin: .55rem auto 1rem; color: var(--snake-muted); font-size: .78rem; line-height: 1.55; }
  .snake-arcade__button { min-height: 2.65rem; padding: .65rem 1rem; border-radius: .75rem; font-size: .78rem; font-weight: 800; }
  .snake-arcade__button--primary { border-color: #b8ff4f; color: #0a1102; background: #b8ff4f; box-shadow: 0 .55rem 1.5rem rgba(184, 255, 79, .16); }
  .snake-arcade__button--primary:hover { border-color: #d5ff96; background: #d0ff88; }
  .snake-arcade__side { padding: 1rem; }
  .snake-arcade__side-title { margin: 0; font-size: .86rem; }
  .snake-arcade__side-copy { margin: .4rem 0 1rem; color: var(--snake-muted); font-size: .7rem; line-height: 1.5; }
  .snake-arcade__pad { display: grid; grid-template-columns: repeat(3, 3.15rem); grid-template-rows: repeat(2, 3.15rem); justify-content: center; gap: .42rem; margin: .4rem auto 1rem; }
  .snake-arcade__pad-button { display: grid; place-items: center; border-radius: .8rem; font-size: 1.05rem; font-weight: 900; user-select: none; -webkit-user-select: none; }
  .snake-arcade__pad-button[data-direction="up"] { grid-column: 2; }
  .snake-arcade__pad-button[data-direction="left"] { grid-column: 1; grid-row: 2; }
  .snake-arcade__pad-button[data-direction="down"] { grid-column: 2; grid-row: 2; }
  .snake-arcade__pad-button[data-direction="right"] { grid-column: 3; grid-row: 2; }
  .snake-arcade__controls { display: grid; gap: .5rem; }
  .snake-arcade__controls .snake-arcade__button { width: 100%; }
  .snake-arcade__tip { margin: 1rem 0 0; padding-top: .8rem; border-top: 1px solid rgba(133, 136, 169, .16); color: var(--snake-muted); font-size: .67rem; line-height: 1.55; }
  .snake-arcade__key { display: inline-grid; min-width: 1.3rem; min-height: 1.3rem; place-items: center; padding: 0 .25rem; border: 1px solid var(--snake-line); border-radius: .3rem; color: var(--snake-ink); background: rgba(4, 4, 10, .4); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .59rem; }
  .snake-arcade__status { margin: .7rem 0 0; color: var(--snake-muted); font-size: .68rem; text-align: center; }
  .snake-arcade__rules { max-width: 44rem; margin: 3rem auto; padding: clamp(1.2rem, 4vw, 2rem); }
  .snake-arcade__rules h2 { margin: 0; font-size: clamp(1.5rem, 5vw, 2.2rem); letter-spacing: -.04em; }
  .snake-arcade__rules p, .snake-arcade__rules li { color: var(--snake-muted); font-size: .82rem; line-height: 1.65; }
  .snake-arcade__rules ol { margin: 1rem 0 1.5rem; padding-left: 1.2rem; }
  .snake-arcade__rules li + li { margin-top: .45rem; }
  @media (max-width: 760px) {
    .snake-arcade__layout { grid-template-columns: 1fr; }
    .snake-arcade__side { display: grid; grid-template-columns: minmax(12rem, .8fr) minmax(12rem, 1fr); gap: 1rem; align-items: center; }
    .snake-arcade__side-copy, .snake-arcade__tip { grid-column: 1 / -1; }
  }
  @media (max-width: 520px) {
    .snake-arcade { padding: .75rem; }
    .snake-arcade__header { align-items: center; }
    .snake-arcade__mark { width: 2.35rem; height: 2.35rem; }
    .snake-arcade__side { display: block; }
    .snake-arcade__stat { padding: .58rem; }
  }
  @media (prefers-reduced-motion: reduce) {
    .snake-arcade__header-action, .snake-arcade__button, .snake-arcade__pad-button { transition: none; }
  }
`;

function element(tagName, className, text) {
  const node = document.createElement(tagName);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function sameCell(a, b) {
  return a.x === b.x && a.y === b.y;
}

function isOpposite(first, second) {
  const a = DIRECTIONS[first];
  const b = DIRECTIONS[second];
  return a.x + b.x === 0 && a.y + b.y === 0;
}

function placeSnack(snake, random = Math.random) {
  const occupied = new Set(snake.map(({ x, y }) => `${x}:${y}`));
  const open = [];
  for (let y = 0; y < GRID_SIZE; y += 1) {
    for (let x = 0; x < GRID_SIZE; x += 1) {
      if (!occupied.has(`${x}:${y}`)) open.push({ x, y });
    }
  }
  if (!open.length) return null;
  const sample = Number(random());
  const normalized = Number.isFinite(sample)
    ? Math.min(Math.max(sample, 0), 0.999999999)
    : 0;
  return open[Math.floor(normalized * open.length)];
}

function createInitialGame(random = Math.random) {
  const snake = [
    { x: 11, y: 11 },
    { x: 10, y: 11 },
    { x: 9, y: 11 },
    { x: 8, y: 11 },
  ];
  return {
    snake,
    snack: placeSnack(snake, random),
    direction: "right",
    queuedDirection: "right",
    score: 0,
    status: "idle",
  };
}

function queueDirection(game, direction) {
  if (!DIRECTIONS[direction] || isOpposite(game.direction, direction)) {
    return game;
  }
  return { ...game, queuedDirection: direction };
}

function advanceGame(game, random = Math.random) {
  if (game.status !== "playing") return game;
  const direction = game.queuedDirection;
  const vector = DIRECTIONS[direction];
  const head = {
    x: game.snake[0].x + vector.x,
    y: game.snake[0].y + vector.y,
  };
  const hitWall =
    head.x < 0 || head.x >= GRID_SIZE || head.y < 0 || head.y >= GRID_SIZE;
  const ateSnack = game.snack && sameCell(head, game.snack);
  const collisionBody = ateSnack ? game.snake : game.snake.slice(0, -1);
  const hitSelf = collisionBody.some((cell) => sameCell(cell, head));
  if (hitWall || hitSelf) {
    return { ...game, direction, status: "over" };
  }

  const snake = [head, ...game.snake];
  if (!ateSnack) snake.pop();
  const score = game.score + (ateSnack ? SCORE_PER_SNACK : 0);
  const snack = ateSnack ? placeSnack(snake, random) : game.snack;
  return {
    ...game,
    snake,
    snack,
    score,
    direction,
    status: snack ? "playing" : "won",
  };
}

function speedForScore(score) {
  return Math.max(MIN_DELAY_MS, START_DELAY_MS - Math.floor(score / 40) * 10);
}

function storageKey(host) {
  const backend = String(host.backend?.id || "unknown").replace(/[^a-zA-Z0-9._-]/g, "_");
  return `agent-canvas:snake-arcade:${backend}:high-score`;
}

function loadHighScore(host) {
  try {
    const value = Number(globalThis.localStorage?.getItem(storageKey(host)));
    return Number.isFinite(value) && value >= 0 ? Math.floor(value) : 0;
  } catch {
    return 0;
  }
}

function saveHighScore(host, score) {
  try {
    globalThis.localStorage?.setItem(storageKey(host), String(score));
  } catch {
    // Storage may be unavailable in privacy modes; the current game still works.
  }
}

function roundedRect(context, x, y, width, height, radius) {
  if (typeof context.roundRect === "function") {
    context.beginPath();
    context.roundRect(x, y, width, height, radius);
    return;
  }
  context.beginPath();
  context.rect(x, y, width, height);
}

function drawGame(canvas, game) {
  const context = canvas.getContext("2d");
  if (!context) return;
  const cssSize = Math.max(280, Math.round(canvas.clientWidth || 560));
  const pixelRatio = Math.min(globalThis.devicePixelRatio || 1, 2);
  const targetSize = Math.round(cssSize * pixelRatio);
  if (canvas.width !== targetSize || canvas.height !== targetSize) {
    canvas.width = targetSize;
    canvas.height = targetSize;
  }
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  const cell = cssSize / GRID_SIZE;

  context.fillStyle = "#090a12";
  context.fillRect(0, 0, cssSize, cssSize);
  context.fillStyle = "rgba(255,255,255,.018)";
  for (let y = 0; y < GRID_SIZE; y += 1) {
    for (let x = (y % 2); x < GRID_SIZE; x += 2) {
      context.fillRect(x * cell, y * cell, cell, cell);
    }
  }

  if (game.snack) {
    const centerX = (game.snack.x + 0.5) * cell;
    const centerY = (game.snack.y + 0.5) * cell;
    context.shadowColor = "#ff55b8";
    context.shadowBlur = cell * 0.8;
    context.fillStyle = "#ff75c3";
    context.beginPath();
    context.arc(centerX, centerY, cell * 0.29, 0, Math.PI * 2);
    context.fill();
    context.shadowBlur = 0;
    context.fillStyle = "rgba(255,255,255,.75)";
    context.beginPath();
    context.arc(centerX - cell * 0.08, centerY - cell * 0.09, cell * 0.065, 0, Math.PI * 2);
    context.fill();
  }

  game.snake.forEach((segment, index) => {
    const inset = Math.max(1.4, cell * 0.1);
    const x = segment.x * cell + inset;
    const y = segment.y * cell + inset;
    const size = cell - inset * 2;
    context.fillStyle = index === 0 ? "#d4ff8a" : `hsl(${105 + Math.min(index, 18) * 2} 92% ${64 - Math.min(index, 24) * 0.65}%)`;
    if (index === 0) {
      context.shadowColor = "rgba(184,255,79,.55)";
      context.shadowBlur = cell * 0.45;
    }
    roundedRect(context, x, y, size, size, cell * 0.24);
    context.fill();
    context.shadowBlur = 0;
  });

  const head = game.snake[0];
  if (head) {
    const vector = DIRECTIONS[game.direction];
    const perpendicular = { x: -vector.y, y: vector.x };
    const center = { x: (head.x + 0.5) * cell, y: (head.y + 0.5) * cell };
    for (const side of [-1, 1]) {
      const eyeX = center.x + vector.x * cell * 0.17 + perpendicular.x * cell * 0.17 * side;
      const eyeY = center.y + vector.y * cell * 0.17 + perpendicular.y * cell * 0.17 * side;
      context.fillStyle = "#152007";
      context.beginPath();
      context.arc(eyeX, eyeY, Math.max(1.2, cell * 0.055), 0, Math.PI * 2);
      context.fill();
    }
  }
}

function stat(label, initialValue) {
  const card = element("div", "snake-arcade__stat");
  const value = element("strong", "snake-arcade__stat-value", initialValue);
  card.append(element("span", "snake-arcade__stat-label", label), value);
  return { card, value };
}

function renderRules(root, navigate) {
  const rules = element("section", "snake-arcade__rules");
  rules.setAttribute("aria-labelledby", "snake-rules-title");
  const title = element("h2", "", "How to be a tiny legend");
  title.id = "snake-rules-title";
  const intro = element("p", "", "Collect every pink snack, grow longer, and keep your neon noodle away from walls and itself.");
  const steps = element("ol");
  for (const copy of [
    "Press Enter or Space to start, then steer with the arrow keys or WASD.",
    "On touch devices, use the direction pad. You can change direction once per game tick.",
    "Every snack is worth 10 points. The pace increases as your score climbs.",
    "Press Space or P to pause. Your best score is saved on this browser for the active backend.",
  ]) steps.append(element("li", "", copy));
  const back = element("button", "snake-arcade__button snake-arcade__button--primary", "← Back to the game");
  back.type = "button";
  back.addEventListener("click", () => navigate(ROOT_ROUTE));
  rules.append(title, intro, steps, back);
  root.append(rules);
}

function renderGame(root, host, navigate, addCleanup) {
  let game = createInitialGame();
  let highScore = loadHighScore(host);
  let highScoreAtStart = highScore;
  let timer = null;
  let disposed = false;
  let pointerStart = null;

  const layout = element("div", "snake-arcade__layout");
  const gamePanel = element("section", "snake-arcade__game");
  gamePanel.setAttribute("aria-label", "Snake game");
  gamePanel.tabIndex = 0;
  const stats = element("div", "snake-arcade__stats");
  const scoreStat = stat("Score", "0");
  const bestStat = stat("Best", String(highScore));
  const speedStat = stat("Pace", "1×");
  stats.append(scoreStat.card, bestStat.card, speedStat.card);

  const boardWrap = element("div", "snake-arcade__board-wrap");
  const canvas = element("canvas", "snake-arcade__canvas");
  canvas.width = 560;
  canvas.height = 560;
  canvas.setAttribute("aria-label", "Snake game board");
  canvas.textContent = "Your browser needs canvas support to display the Snake board.";
  const overlay = element("div", "snake-arcade__overlay");
  const overlayCard = element("div", "snake-arcade__overlay-card");
  const overlayKicker = element("p", "snake-arcade__overlay-kicker", "Ready player one");
  const overlayTitle = element("h2", "snake-arcade__overlay-title", "Feed the neon noodle");
  const overlayCopy = element("p", "snake-arcade__overlay-copy", "Grab pink snacks. Dodge walls. Look extremely cool doing it.");
  const overlayButton = element("button", "snake-arcade__button snake-arcade__button--primary", "Start game");
  overlayButton.type = "button";
  overlayCard.append(overlayKicker, overlayTitle, overlayCopy, overlayButton);
  overlay.append(overlayCard);
  boardWrap.append(canvas, overlay);
  const liveStatus = element("p", "snake-arcade__status", "Ready to play.");
  liveStatus.setAttribute("role", "status");
  liveStatus.setAttribute("aria-live", "polite");
  gamePanel.append(stats, boardWrap, liveStatus);

  const side = element("aside", "snake-arcade__side");
  side.append(
    element("h2", "snake-arcade__side-title", "Controls"),
    element("p", "snake-arcade__side-copy", "Arrow keys, WASD, or the direction pad all work."),
  );
  const pad = element("div", "snake-arcade__pad");
  pad.setAttribute("aria-label", "Direction controls");
  const labels = { up: ["↑", "Move up"], left: ["←", "Move left"], down: ["↓", "Move down"], right: ["→", "Move right"] };
  for (const [direction, [glyph, label]] of Object.entries(labels)) {
    const button = element("button", "snake-arcade__pad-button", glyph);
    button.type = "button";
    button.dataset.direction = direction;
    button.setAttribute("aria-label", label);
    pad.append(button);
  }
  const controls = element("div", "snake-arcade__controls");
  const primaryButton = element("button", "snake-arcade__button snake-arcade__button--primary", "New game");
  const pauseButton = element("button", "snake-arcade__button", "Pause");
  primaryButton.type = "button";
  pauseButton.type = "button";
  pauseButton.disabled = true;
  controls.append(primaryButton, pauseButton);
  const tip = element("p", "snake-arcade__tip");
  tip.append(
    document.createTextNode("Quick keys: "),
    element("span", "snake-arcade__key", "P"),
    document.createTextNode(" pause · "),
    element("span", "snake-arcade__key", "Space"),
    document.createTextNode(" start/pause"),
  );
  side.append(pad, controls, tip);
  layout.append(gamePanel, side);
  root.append(layout);

  function cancelTick() {
    if (timer !== null) globalThis.clearTimeout(timer);
    timer = null;
  }

  function announce(message) {
    liveStatus.textContent = message;
  }

  function updateUi() {
    scoreStat.value.textContent = String(game.score);
    bestStat.value.textContent = String(highScore);
    const speed = START_DELAY_MS / speedForScore(game.score);
    speedStat.value.textContent = `${speed.toFixed(speed < 1.05 ? 0 : 1)}×`;
    pauseButton.disabled = !["playing", "paused"].includes(game.status);
    pauseButton.textContent = game.status === "paused" ? "Resume" : "Pause";
    drawGame(canvas, game);

    if (game.status === "playing") {
      overlay.hidden = true;
    } else {
      overlay.hidden = false;
      if (game.status === "idle") {
        overlayKicker.textContent = "Ready player one";
        overlayTitle.textContent = "Feed the neon noodle";
        overlayCopy.textContent = "Grab pink snacks. Dodge walls. Look extremely cool doing it.";
        overlayButton.textContent = "Start game";
      } else if (game.status === "paused") {
        overlayKicker.textContent = "Intermission";
        overlayTitle.textContent = "Game paused";
        overlayCopy.textContent = "The noodle is holding very, very still.";
        overlayButton.textContent = "Resume";
      } else if (game.status === "won") {
        overlayKicker.textContent = "Perfect run";
        overlayTitle.textContent = "You filled the board!";
        overlayCopy.textContent = `A flawless ${game.score}-point masterpiece.`;
        overlayButton.textContent = "Play again";
      } else {
        overlayKicker.textContent = game.score > highScoreAtStart ? "New high score" : "Run complete";
        overlayTitle.textContent = `${game.score} points`;
        overlayCopy.textContent = "The noodle gave it everything. Another round?";
        overlayButton.textContent = "Play again";
      }
    }
  }

  function scheduleTick() {
    cancelTick();
    if (disposed || game.status !== "playing") return;
    timer = globalThis.setTimeout(() => {
      if (disposed) return;
      game = advanceGame(game);
      if (game.score > highScore) {
        highScore = game.score;
        saveHighScore(host, highScore);
        announce(`New high score: ${highScore}.`);
      }
      if (game.status === "over") announce(`Game over. Final score: ${game.score}.`);
      if (game.status === "won") announce(`You won with ${game.score} points.`);
      updateUi();
      scheduleTick();
    }, speedForScore(game.score));
  }

  function startNewGame() {
    highScoreAtStart = highScore;
    game = { ...createInitialGame(), status: "playing" };
    announce("Game started.");
    updateUi();
    scheduleTick();
    gamePanel.focus({ preventScroll: true });
  }

  function togglePause() {
    if (game.status === "playing") {
      game = { ...game, status: "paused" };
      cancelTick();
      announce("Game paused.");
    } else if (game.status === "paused") {
      game = { ...game, status: "playing" };
      announce("Game resumed.");
      scheduleTick();
    } else if (["idle", "over", "won"].includes(game.status)) {
      startNewGame();
      return;
    }
    updateUi();
    gamePanel.focus({ preventScroll: true });
  }

  function steer(direction) {
    if (["idle", "over", "won"].includes(game.status)) startNewGame();
    game = queueDirection(game, direction);
    updateUi();
  }

  function onKeyDown(event) {
    const direction = KEY_DIRECTIONS[event.key];
    if (direction) {
      event.preventDefault();
      steer(direction);
      return;
    }
    if (event.key === " " || event.key === "p" || event.key === "P") {
      event.preventDefault();
      togglePause();
      return;
    }
    if (event.key === "Enter" && game.status !== "playing") {
      event.preventDefault();
      togglePause();
    }
  }

  function onPointerDown(event) {
    pointerStart = { x: event.clientX, y: event.clientY };
  }

  function onPointerUp(event) {
    if (!pointerStart) return;
    const x = event.clientX - pointerStart.x;
    const y = event.clientY - pointerStart.y;
    pointerStart = null;
    if (Math.max(Math.abs(x), Math.abs(y)) < 24) return;
    steer(Math.abs(x) > Math.abs(y) ? (x > 0 ? "right" : "left") : (y > 0 ? "down" : "up"));
  }

  overlayButton.addEventListener("click", togglePause);
  primaryButton.addEventListener("click", startNewGame);
  pauseButton.addEventListener("click", togglePause);
  gamePanel.addEventListener("keydown", onKeyDown);
  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointerup", onPointerUp);
  canvas.addEventListener("pointercancel", () => { pointerStart = null; });
  pad.addEventListener("click", (event) => {
    const direction = event.target?.dataset?.direction;
    if (direction) steer(direction);
  });

  const ResizeObserverClass = globalThis.ResizeObserver;
  const resizeObserver = ResizeObserverClass ? new ResizeObserverClass(() => drawGame(canvas, game)) : null;
  resizeObserver?.observe(canvas);
  const onResize = () => drawGame(canvas, game);
  if (!resizeObserver) globalThis.addEventListener?.("resize", onResize);

  addCleanup(() => {
    disposed = true;
    cancelTick();
    resizeObserver?.disconnect();
    if (!resizeObserver) globalThis.removeEventListener?.("resize", onResize);
  });
  updateUi();
}

function mountArcade(host, { container, path, navigate }) {
  const cleanups = [];
  const style = element("style");
  style.textContent = STYLE;
  const root = element("main", "snake-arcade");
  root.setAttribute("aria-label", "Snake Arcade");
  const shell = element("div", "snake-arcade__shell");
  const header = element("header", "snake-arcade__header");
  const brand = element("div", "snake-arcade__brand");
  const mark = element("span", "snake-arcade__mark", "◉");
  mark.setAttribute("aria-hidden", "true");
  const brandCopy = element("div");
  brandCopy.append(
    element("p", "snake-arcade__eyebrow", "Pocket arcade"),
    element("h1", "snake-arcade__title", "Snake Arcade"),
  );
  brand.append(mark, brandCopy);
  const routeButton = element("button", "snake-arcade__header-action", path === "how-to-play" ? "Play now" : "How to play");
  routeButton.type = "button";
  routeButton.addEventListener("click", () => navigate(path === "how-to-play" ? ROOT_ROUTE : `${ROOT_ROUTE}/how-to-play`));
  header.append(brand, routeButton);
  shell.append(header);
  root.append(shell);
  container.append(style, root);

  if (path === "how-to-play") {
    renderRules(shell, navigate);
  } else {
    renderGame(shell, host, navigate, (cleanup) => cleanups.push(cleanup));
  }

  return () => {
    for (const cleanup of cleanups.reverse()) cleanup();
    root.remove();
    style.remove();
  };
}

export function activate(host) {
  if (host.apiVersion !== "1") {
    throw new Error("Snake Arcade requires Canvas host API 1.");
  }
  return host.registerPage("arcade", (context) => mountArcade(host, context));
}

export const __testing = Object.freeze({
  GRID_SIZE,
  advanceGame,
  createInitialGame,
  placeSnack,
  queueDirection,
  speedForScore,
  storageKey,
});
