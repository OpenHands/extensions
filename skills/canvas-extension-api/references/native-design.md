# Native OpenHands App design

Build Apps for Agent Canvas that visually belong in the host while remaining a self-contained, safe extension package. Use this reference together with the main `SKILL.md` workflow before changing an App's UI.

## Core rule: reuse tokens, not host internals

Treat an App bundle as an independent frontend. Do not import Agent Canvas React components, utility modules, CSS files, font files, Tailwind configuration, aliases, or private DOM classes. The host imports the App as a self-contained Blob ESM module, so those imports will fail or create fragile coupling.

Reuse the host's stable CSS custom properties instead. Scope every selector under a unique App root class and provide literal fallbacks so the page stays legible outside a current Canvas build. Tailwind utility names such as `bg-base` or `text-contrast` are **not globally available** to an App: they work only after the App's own Tailwind build maps them to the host variables.

Use semantic names (`surface`, `foreground`, `border`, `primary`) rather than copying cool-grey hex values.

## Choose the implementation path

Choose the smallest path that matches the App package:

| App implementation | Recommended styling approach |
| --- | --- |
| Dependency-free JavaScript | Inject one scoped CSS string from the entrypoint. Use host custom properties directly. |
| React/TypeScript with Tailwind | Add an App-local Tailwind theme mapping to the host variables, then compile every class into the single `extension.js` artifact. |
| Existing CSS module or CSS-in-JS setup | Define the semantic colors and component recipes in the App's own scoped stylesheet. |

Never expect the host Tailwind compiler to scan or compile App source. Never use a CDN Tailwind runtime. Never attach App styles to `:root`, `html`, `body`, or global element selectors.

## Tailwind setup for a bundled App

For Tailwind v4, place an App-local mapping in the App stylesheet. This lets the App use Canvas-like classes while preserving portability:

```css
@import "tailwindcss";

@theme inline {
  --color-base: var(--oh-color-base);
  --color-base-secondary: var(--oh-color-base-secondary);
  --color-surface: var(--oh-surface);
  --color-surface-raised: var(--oh-surface-raised);
  --color-foreground: var(--oh-foreground);
  --color-contrast: var(--oh-contrast);
  --color-muted: var(--oh-muted);
  --color-tertiary-alt: var(--oh-text-dim);
  --color-border: var(--oh-border);
  --color-border-subtle: var(--oh-border-subtle);
  --color-focus: var(--oh-focus);
  --color-interactive-hover: var(--oh-interactive-hover);
  --color-primary: var(--oh-color-primary);
  --color-on-primary: var(--oh-accent-foreground);
  --color-danger: var(--oh-danger);
}
```

Compile this stylesheet into `extension.js`; do not leave a linked CSS asset. For an App without Tailwind, use the matching raw CSS below instead. Use utility recipes only after adding this mapping.

## Layout and density

Let Canvas own the outer page and scrolling region. Do not add a second page shell, `h-screen`, global background, sidebar, or top navigation. Start with `min-h-full`, use `p-4 sm:p-6 lg:p-8`, and constrain dense content with `mx-auto w-full max-w-5xl`. Use `gap-4` for related controls, `gap-6` within sections, and `gap-8` between major sections. Use `rounded-lg` for controls and `rounded-xl` for cards and messages.

Avoid gradients, glass effects, oversize headings, floating shadows, dense borders, and hard-coded dark greys. The native visual language is restrained: dark layered surfaces, cool-grey borders, warm primary actions, direct typography, and short transitions.

## Interaction and state checklist

- Apply `text-contrast` to headings and key labels; use `text-muted` or `text-tertiary-alt` for supporting copy.
- Use the primary recipe for one dominant action. Use a bordered secondary action for alternatives. Do not make every button primary.
- Use a 36px (`h-9`) control height and `rounded-lg` for input, select, and standard button controls.
- Use `focus-visible` rather than removing outlines. Preserve disabled affordance with `disabled:cursor-not-allowed disabled:opacity-60`.
- Animate only background, border, box-shadow, opacity, or transforms and include `motion-reduce:transition-none`.
- Scope icon sizing and color within the App. Do not assume HeroUI, Lucide, or host icon packages exist.
- Use `textContent`, framework escaping, or safe DOM creation for data from requests. Never inject response text with `innerHTML`.

## Semantic token map

| Intent | Host variable | Fallback |
| --- | --- | --- |
| Deep page base | `--oh-color-base` | `#0B0E14` |
| Standard panel | `--oh-color-base-secondary` | `#21252F` |
| Raised surface | `--oh-surface-raised` | `#2C313F` |
| Main text | `--oh-contrast` | `#FFFFFF` |
| Standard text | `--oh-foreground` | `#EEF2F7` |
| Secondary text | `--oh-muted` | `#A3B0C4` |
| Muted placeholder text | `--oh-text-dim` | `#7E8A9E` |
| Standard border | `--oh-border` | `#4B5468` |
| Subtle divider | `--oh-border-subtle` | `#383F50` |
| Focus ring | `--oh-focus` | `#FFFFFF` |
| Primary surface | `--oh-color-primary` | `#C9B974` |
| Primary text | `--oh-accent-foreground` | `#0B0E14` |
| Danger | `--oh-danger` | `#E76A5E` |
| Success | `--oh-success` | `#A5E75E` |

## Copy-ready Tailwind recipes

Use these recipes only after mapping the semantic colors in the App-local Tailwind configuration above.

### Content shell

```tsx
<div className="min-h-full p-4 sm:p-6 lg:p-8 text-foreground">
  <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">...</div>
</div>
```

Do not use `h-screen`, `min-h-screen`, a host-like global background, or a nested `<main>`; Canvas supplies the page landmark and scroll context.

### Page heading

```tsx
<header className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
  <div className="min-w-0">
    <h1 className="text-xl font-semibold tracking-tight text-contrast">Page title</h1>
    <p className="mt-1 text-sm text-muted">Short supporting description.</p>
  </div>
</header>
```

### Card or section

```tsx
<section className="rounded-xl border border-border bg-base-secondary p-4 sm:p-6">
  <h2 className="text-base font-medium text-contrast">Section title</h2>
  <p className="mt-1 text-sm text-muted">Explain the section briefly.</p>
  <div className="mt-5 flex flex-col gap-4">...</div>
</section>
```

Use `border-border-subtle` for dividers inside an existing card. Avoid default card shadows.

### Controls and buttons

```tsx
const control =
  "h-9 min-h-9 rounded-lg transition-[background-color,border-color,box-shadow,opacity] duration-75 motion-reduce:transition-none";

const field = `${control} w-full min-w-0 border border-border bg-base-secondary px-3 text-sm text-contrast placeholder:text-tertiary-alt focus:border-contrast/40 focus:ring-1 focus:ring-contrast/20 focus:outline-none disabled:cursor-not-allowed disabled:opacity-60`;

const primaryButton = `${control} inline-flex w-fit items-center justify-center gap-2 bg-primary px-3 text-sm font-normal text-on-primary hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-30`;

const secondaryButton = `${control} inline-flex w-fit items-center justify-center gap-2 border border-border bg-base-secondary px-3 text-sm font-normal text-contrast hover:bg-surface-raised disabled:cursor-not-allowed disabled:opacity-30`;
```

Use `label` plus `htmlFor`, keep field hints in `text-xs text-muted`, and express validation with `aria-invalid`, a `border-red-500`, and a linked `role="alert"` message using `text-xs text-red-400`.

### Toolbar and responsive grid

```tsx
<div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
  <div className="min-w-0">...</div>
  <div className="flex flex-wrap items-center gap-2">...</div>
</div>

<div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">...</div>
```

### Informational, error, and empty state

```tsx
<div className="rounded-xl border border-border bg-base-secondary p-6 text-center">
  <h2 className="text-base font-medium text-contrast">Nothing here yet</h2>
  <p className="mt-2 text-sm text-muted">Describe the next useful action.</p>
  <button className={`${primaryButton} mt-4`}>Create item</button>
</div>

<div role="alert" className="rounded-xl border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
  The request could not be completed.
</div>
```

Use `animate-pulse` with `motion-reduce:animate-none` only for short loading placeholders; reserve space with shapes matching loaded cards or rows.

### Compact tabs

```tsx
<div role="tablist" aria-label="View options" className="flex w-fit gap-1 rounded-lg border border-border bg-base-secondary p-1">
  <button role="tab" aria-selected="true" className="rounded-md bg-interactive-hover px-3 py-1.5 text-sm text-contrast">Overview</button>
  <button role="tab" aria-selected="false" className="rounded-md px-3 py-1.5 text-sm text-muted hover:bg-surface-raised hover:text-contrast">Activity</button>
</div>
```

Implement keyboard tab behavior when tabs change content; use regular buttons for simple filters.

## Raw scoped CSS alternative

Use this approach for dependency-free Apps. Apply it only after inserting an App root such as `.acme-dashboard`.

```css
.acme-dashboard {
  color: var(--oh-foreground, #EEF2F7);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.acme-dashboard .card {
  border: 1px solid var(--oh-border, #4B5468);
  border-radius: 12px;
  background: var(--oh-color-base-secondary, #21252F);
  padding: 1.5rem;
}
.acme-dashboard .field,
.acme-dashboard .button {
  min-height: 2.25rem;
  border-radius: 8px;
  transition: background-color 75ms, border-color 75ms, box-shadow 75ms, opacity 75ms;
}
.acme-dashboard .field {
  width: 100%; border: 1px solid var(--oh-border, #4B5468);
  background: var(--oh-color-base-secondary, #21252F);
  color: var(--oh-contrast, #FFF); padding: 0 0.75rem;
}
.acme-dashboard .field:focus-visible,
.acme-dashboard .button:focus-visible {
  outline: none; border-color: color-mix(in srgb, var(--oh-contrast, #FFF) 40%, transparent);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--oh-contrast, #FFF) 20%, transparent);
}
.acme-dashboard .button--primary {
  border: 0; background: var(--oh-color-primary, #C9B974);
  color: var(--oh-accent-foreground, #0B0E14); padding: 0 0.75rem;
}
@media (prefers-reduced-motion: reduce) {
  .acme-dashboard .field, .acme-dashboard .button { transition: none; }
}
```

## Mount-safe injected style helper

Use one marker per mounted App root and remove the node during cleanup.

```js
function installStyles(css, marker) {
  const style = document.createElement("style");
  style.dataset.canvasAppStyle = marker;
  style.textContent = css;
  document.head.append(style);
  return () => style.remove();
}

// During mount:
const disposeStyles = installStyles(STYLES, "acme-dashboard");
const root = document.createElement("div");
root.className = "acme-dashboard";
container.append(root);
return () => {
  disposeStyles();
  root.remove();
};
```

If more than one page can mount concurrently, ref-count the marker or inject its stylesheet once in `activate` and remove it in the activation disposer.

## Verify before delivery

- Confirm extension markup uses a unique root class and no App CSS leaks outside it.
- Confirm styles survive a real Canvas mount, route remount, disable/re-enable cycle, and host dark surface backgrounds.
- Confirm `extension.js` has no unresolved CSS import, bare package import, extra CSS chunk, or Node global.
- Run the Canvas extension static validator plus the App's lint, tests, and build.
- Report whether the App uses direct host variables or an App-local Tailwind mapping, and list the tested states.
