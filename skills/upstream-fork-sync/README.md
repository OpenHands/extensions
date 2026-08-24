# Upstream Fork Sync Skill

An OpenHands skill that creates a cron automation to keep a long-lived
fork synchronized with its upstream source.

## What it does

1. **Fetches** the latest upstream changes for the fork on a schedule.
2. **Rebases** the fork's local customizations on top of the newest
   upstream HEAD.
3. **Verifies** the software still works (using a configured command or an
   inferred build check).
4. **Replaces** the deployed version when verification passes, or
   **fails safe** and reports the problem when it does not.

## When to use

Use this skill when a user wants to maintain customizations on top of an
upstream project over time — the "long-lived fork" pattern — without
manually redoing the work after every upstream release.

## Files

```
upstream-fork-sync/
├── SKILL.md   ← agent instructions (loaded automatically)
└── README.md  ← this file
```

## Quick start

Just tell OpenHands:

> *"Set up an upstream fork sync for `owner/repo`"*

The skill will walk through token verification, upstream-remote selection,
local-changes description, verification command, and schedule, then create
the automation automatically.
