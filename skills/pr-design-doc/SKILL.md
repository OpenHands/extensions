---
name: pr-design-doc
description: >
  For a non-trivial pull request, write a self-contained HTML design doc under the
  temporary `.pr/` directory and link it in the PR description via htmlpreview, so
  maintainers grasp the proposal at a glance — code/API design, and the before/after of
  the change, grounded to real code. Use when opening or updating a non-trivial PR, or
  when the user says "add a design doc", "document this PR for reviewers", "show the
  before/after", "make the design reviewable", or "write the .pr/ page".
triggers:
- /pr-design-doc
- /design-doc
license: MIT
metadata:
  tags: pull-request, design-doc, html, review, before-after, htmlpreview
---

# pr-design-doc — a reviewable design doc for a non-trivial PR

A diff shows *what changed line by line*. It does not show *the design*: the shape of the
change, the API before and after, and why this approach. Reviewers reconstruct that by
hand, slowly. The scarce resource is the maintainer's attention and trust budget — not the
agent's effort. Spend extra effort to hand them **one self-contained HTML page** that
conveys the **big picture** and the **before → after core difference**, with every claim
**clickable back to the real code**, then link it from the PR description.

This is the same craft as a "show me this change" explainer, aimed at one job: making a
non-trivial PR easy to review.

## When to use it

- Opening or updating a **non-trivial** PR: new/changed public API, a new module or
  subsystem, a behavior change in core logic, a migration, or anything a reviewer can't
  fully judge from the diff in a couple of minutes.
- **Skip it** for trivial PRs — a typo, a one-line guard, a dependency bump, a docs tweak.
  A design doc there is noise. Use judgment; if the diff *is* the explanation, don't add a
  page.

## The `.pr/` workflow (why this is safe to commit)

OpenHands repos use a temporary **`.pr/`** directory for PR-only artifacts. It is
**removed automatically when the PR is approved** (see `.github/workflows/pr-artifacts.yml`
in `OpenHands/OpenHands`), so the design doc never lands in `main`. That makes `.pr/` the
right home for a review aid: it lives with the branch, renders while the PR is open, and
disappears on approval.

## Workflow

1. **Get the change.** You usually already have the branch. Otherwise:
   ```bash
   gh pr view <n> --json title,body,baseRefName,headRefName,files,additions,deletions
   gh pr diff <n>                 # or: git diff <base>...<head>  /  git diff
   gh repo view --json url        # for clickable blob links; pin the head SHA
   ```
   Group changed files by area; note the merge base and head SHA for source links.

2. **Read both sides of each logical file.** `git show <base>:<path>` vs head. Capture the
   **function-level** behavioral difference — what the code *did* vs *does now*.
   - new file → no "before"; one "after" diagram + a line on the role it adds.
   - deleted file → "before" diagram + who/what takes over.
   - edited file → a before/after pair, with the delta highlighted.

3. **Classify each file.** *Logic* change (behavior moved) → draw before/after. *Mechanical*
   change (rename, constant, config, import move) → a one-line `before → after` row, no
   diagram. Don't dilute the signal by drawing mechanical edits.

4. **If the change is an API change, lead with the API.** Show the signature/schema/type
   **before and after** side by side (function signature, endpoint + payload, config field,
   event shape). Name the compatibility impact plainly: additive, breaking, or behind a flag.

5. **Find the cross-file story.** If one call chain threads several files, draw a single
   **overview** before/after at the top; per-file cards drill in.

6. **Build the page** per [`references/html-craft.md`](references/html-craft.md) — one
   self-contained, offline, editorial HTML file with hand-drawn SVG figures. Save it to
   the repo's `.pr/` directory, e.g. `.pr/design.html` (or `.pr/<topic>.html`).

7. **Commit under `.pr/`, push, and link it.**
   ```bash
   git add .pr/design.html
   git commit -m "docs(.pr): design doc for <PR topic>"
   git push <your-fork> <pr-branch>
   ```
   Then add the htmlpreview link near the top of the PR description, pointing at the **fork
   and branch the PR is opened from** (it renders before merge):
   ```
   📄 Design doc: https://htmlpreview.github.io/?https://github.com/<fork-owner>/<repo>/blob/<pr-branch>/.pr/design.html
   ```

## What the page contains

1. **What changed (decision first)** — one paragraph: the intent, net effect, and why the
   reviewer should care. Put the highest-impact conclusion, risk, or API-compat note in a
   `★` callout, with the most important changed `path:line` nearby. Stats (`N files ·
   +A / −D`) are context, not the lead. If there's a cross-file flow, the **overview
   before/after SVG** goes here.
2. **API before → after** (when the PR changes an interface) — signatures/schemas/types side
   by side, with the compatibility verdict stated.
3. **Left rail / index** — changed files grouped by area, each tagged (🟢 added · 🔴 removed ·
   ✏️ changed · ⚙️ mechanical) with +/− counts; click to jump.
4. **Per-file cards** — for each logical file: a claim-carrying title, a one-line summary of
   how its behavior changed, **before/after** diagrams with real symbol names + `file:line`
   (changed nodes in orange), and the diff in a collapsed `<details>`. Mechanical files get a
   small `before → after` table, no diagram.
5. **(optional) Risk / follow-ups** — only if grounded in what you read.

## Non-negotiable principles

1. **Optimize for scarce reviewer attention.** The first screen answers, in ~15 seconds:
   what this PR does, whether it's risky, where to look first, and what evidence backs the
   claim. Lead with the conclusion, not your process.
2. **Show the difference, not just the after.** For any logic or API change, draw **before**
   and **after** and make the *delta* visually loud (color + line style). The contrast is
   the product.
3. **Ground everything to code, beside the claim.** Every box, node, and sentence names a
   real symbol + `path:line`, and links to the source (GitHub blob URL at the head SHA)
   where possible. One click from "this changed" to the exact code.
4. **Hand-draw the carrying diagrams.** Prefer bespoke inline SVG for the before/after that
   makes the argument; Mermaid is fine only for quick auxiliary graphs.
5. **Self-contained & offline.** One HTML file, inline CSS/SVG, opens by double-click,
   survives being copied to another machine (htmlpreview needs this).
6. **`.pr/` only, and temporary.** The doc is a review aid, not project docs. Keep it in
   `.pr/`; it is removed on approval. Do not move design HTML into `docs/` or ship it in the
   merged tree.

## Anti-patterns

- ❌ Dumping the raw diff / file tree and calling it a "design doc" — adds nothing over the
  PR page.
- ❌ Empty nodes ("process data", "handle request") — every node is a real symbol +
  location.
- ❌ Only the after-state when something changed — reviewers want the *contrast*.
- ❌ A design doc on a trivial PR — noise. Skip it.
- ❌ Committing the HTML outside `.pr/` (e.g. `docs/`), where it would merge into `main`.
- ❌ A private-repo htmlpreview link — htmlpreview can't fetch private raw content (auth +
  CORS). Use GitHub Pages or the local-serve fallback in the craft reference instead.
