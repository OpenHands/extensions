# Frontend Slides

An [Agent Skills](https://agentskills.io/) skill for creating stunning, animation-rich HTML presentations — from scratch or by converting PowerPoint files.

This skill is published in the OpenHands extensions registry and can be used by OpenHands (CLI/GUI/Cloud) and other AgentSkills-compatible runtimes.

## What This Does

**Frontend Slides** helps non-designers create beautiful web presentations without knowing CSS or JavaScript. It uses a "show, don't tell" approach: instead of asking you to describe your aesthetic preferences in words, it generates visual previews and lets you pick what you like.

### Key Features

- **Zero Dependencies** — Single HTML files with inline CSS/JS. No npm, no build tools, no frameworks.
- **Visual Style Discovery** — Can't articulate design preferences? No problem. Pick from generated visual previews.
- **PPT Conversion** — Convert existing PowerPoint files to web, preserving all images and content.
- **Anti-AI-Slop** — Curated distinctive styles that avoid generic AI aesthetics (bye-bye, purple gradients on white).
- **Production Quality** — Accessible, responsive, well-commented code you can customize.

## Installation

### OpenHands (CLI / Local GUI)

This skill uses the AgentSkills directory format. The **directory name must be `frontend-slides/`** and it must contain `SKILL.md` (plus the `references/` folder).

- **Repository-level (recommended):** `.agents/skills/frontend-slides/`
- **User-level:** `~/.agents/skills/frontend-slides/`

```bash
# Repository-level
mkdir -p .agents/skills
cp -R frontend-slides .agents/skills/frontend-slides

# User-level
mkdir -p ~/.agents/skills
cp -R frontend-slides ~/.agents/skills/frontend-slides
```

### OpenHands Software Agent SDK

- To auto-load skills from the public registry (https://github.com/OpenHands/extensions):

```python
from openhands.sdk import AgentContext

agent_context = AgentContext(load_public_skills=True)
```

- To load this skill from a local directory (for example, `.agents/skills/`):

```python
from openhands.sdk import AgentContext
from openhands.sdk.context.skills import load_skills_from_dir

_, _, agent_skills = load_skills_from_dir(".agents/skills")
agent_context = AgentContext(skills=list(agent_skills.values()))
```

References: https://docs.openhands.dev/overview/skills and https://docs.openhands.dev/sdk/guides/skill

## Usage

### Create a New Presentation

```
Create a pitch deck for my AI startup.

Use the frontend-slides skill.
```

The skill will:
1. Ask about your content (slides, messages, images)
2. Ask about the feeling you want (impressed? excited? calm?)
3. Generate 3 visual style previews for you to compare
4. Create the full presentation in your chosen style
5. Open it in your browser

### Convert a PowerPoint

```
Convert my presentation.pptx to a web slideshow (HTML). Preserve text, images, and speaker notes.

Use the frontend-slides skill.
```

The skill will:
1. Extract all text, images, and notes from your PPT
2. Show you the extracted content for confirmation
3. Let you pick a visual style
4. Generate an HTML presentation with all your original assets

## Included Styles

### Dark Themes
- **Neon Cyber** — Futuristic, techy, particle effects
- **Midnight Executive** — Premium, corporate, trustworthy
- **Deep Space** — Cinematic, inspiring, vast
- **Terminal Green** — Developer-focused, hacker aesthetic

### Light Themes
- **Paper & Ink** — Editorial, literary, refined
- **Swiss Modern** — Clean, Bauhaus-inspired, geometric
- **Soft Pastel** — Friendly, playful, creative
- **Warm Editorial** — Magazine-style, photographic

### Specialty
- **Brutalist** — Raw, bold, attention-grabbing
- **Gradient Wave** — Modern SaaS aesthetic

## Output Example

Each presentation is a single, self-contained HTML file:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <!-- Fonts, CSS variables, all styles inline -->
</head>
<body>
    <section class="slide title-slide">
        <h1 class="reveal">Your Title</h1>
    </section>

    <section class="slide">
        <h2 class="reveal">Slide Content</h2>
    </section>

    <!-- Navigation: Arrow keys, scroll, swipe, or click dots -->
    <script>
        // SlidePresentation controller, animations, interactions
    </script>
</body>
</html>
```

Features included:
- Keyboard navigation (arrows, space)
- Touch/swipe support
- Mouse wheel scrolling
- Progress bar
- Navigation dots
- Scroll-triggered animations
- Responsive design
- Reduced motion support

## Philosophy

This skill was born from the belief that:

1. **You don't need to be a designer to make beautiful things.** You just need to react to what you see.

2. **Dependencies are debt.** A single HTML file will work in 10 years. A React project from 2019? Good luck.

3. **Generic is forgettable.** Every presentation should feel custom-crafted, not template-generated.

4. **Comments are kindness.** Code should explain itself to future-you (or anyone else who opens it).

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Skill definition (AgentSkills format) |
| `references/STYLE_PRESETS.md` | Reference file with curated visual styles |

## Requirements

- OpenHands (CLI/GUI/Cloud) or the OpenHands Software Agent SDK (AgentSkills-compatible runtime)
- For PPT conversion: Python with `python-pptx` library

## Credits

Originally created by [@zarazhangrui](https://github.com/zarazhangrui).

Inspired by the "Vibe Coding" philosophy — building beautiful things without being a traditional software engineer.

## License

MIT — Use it, modify it, share it.
