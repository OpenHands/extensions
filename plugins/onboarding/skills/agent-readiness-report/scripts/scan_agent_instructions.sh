#!/usr/bin/env bash
# Scan for Agent Instructions signals (Pillar 1)
# Helps the agent find relevant files — not a substitute for judgment.

REPO="${1:-.}"
cd "$REPO" 2>/dev/null || { echo "Cannot access $REPO"; exit 1; }

echo "=== Pillar 1: Agent Instructions ==="
echo ""

echo "-- Agent instruction files --"
find . -maxdepth 3 -iname 'AGENTS.md' -o -iname 'CLAUDE.md' -o -iname 'COPILOT.md' \
  -o -iname 'CONVENTIONS.md' -o -iname 'CODING_GUIDELINES.md' 2>/dev/null | sort

echo ""
echo "-- AI IDE configuration --"
for f in .cursor .cursor/rules .cursorrules .github/copilot-instructions.md \
         .github/instructions .claude .claude/settings.json; do
  [ -e "$f" ] && echo "./$f"
done

echo ""
echo "-- Agent skills --"
for d in .claude/skills .factory/skills; do
  [ -d "$d" ] && echo "./$d/ ($(find "$d" -type f | wc -l | tr -d ' ') files)"
done
find . -maxdepth 3 -iname 'skill.md' 2>/dev/null | sort

echo ""
echo "-- Tool server configuration --"
find . -maxdepth 2 -name '.mcp.json' -o -name 'mcp.config.*' 2>/dev/null | sort

echo ""
echo "-- Agent prompt library --"
for d in .github/prompts prompts; do
  [ -d "$d" ] && echo "./$d/ ($(find "$d" -type f | wc -l | tr -d ' ') files)"
done

echo ""
echo "-- README --"
[ -f README.md ] && echo "./README.md ($(wc -l < README.md) lines)" || echo "(not found)"

echo ""
echo "-- Contributing guide --"
find . -maxdepth 2 -iname 'CONTRIBUTING*' 2>/dev/null | sort

echo ""
echo "-- Architecture docs --"
find . -maxdepth 3 -iname 'ARCHITECTURE*' -o -iname 'DESIGN*' 2>/dev/null | sort
for d in doc/adr docs/adr decisions rfcs doc/design; do
  [ -d "$d" ] && echo "./$d/ ($(find "$d" -type f | wc -l | tr -d ' ') files)"
done

echo ""
echo "-- API documentation --"
find . -maxdepth 3 -name 'openapi.yaml' -o -name 'openapi.json' -o -name 'swagger.yaml' \
  -o -name 'swagger.json' 2>/dev/null | sort
find . -maxdepth 2 -name 'doc.go' 2>/dev/null | head -5
api_doc_count=$(find . -maxdepth 2 -name 'doc.go' 2>/dev/null | wc -l | tr -d ' ')
[ "$api_doc_count" -gt 5 ] && echo "  ... and $((api_doc_count - 5)) more doc.go files"

echo ""
echo "-- Changelog --"
find . -maxdepth 1 -iname 'CHANGELOG*' -o -iname 'CHANGES*' -o -iname 'HISTORY*' 2>/dev/null | sort

echo ""
echo "-- Environment variable docs --"
find . -maxdepth 2 -name '.env.example' -o -name '.env.template' -o -name '.env.sample' 2>/dev/null | sort

echo ""
echo "-- Documentation site / directory --"
[ -d docs ] && echo "./docs/ ($(find docs -type f | wc -l | tr -d ' ') files)"
for f in docusaurus.config.* mkdocs.yml conf.py .vitepress/config.*; do
  find . -maxdepth 2 -name "$(basename "$f")" 2>/dev/null
done

echo ""
echo "-- Examples directory --"
for d in examples _examples; do
  [ -d "$d" ] && echo "./$d/ ($(find "$d" -type f | wc -l | tr -d ' ') files)"
done

echo ""
echo "-- Module-level READMEs --"
find . -mindepth 2 -maxdepth 3 -name 'README.md' 2>/dev/null | head -10
readme_count=$(find . -mindepth 2 -maxdepth 3 -name 'README.md' 2>/dev/null | wc -l | tr -d ' ')
[ "$readme_count" -gt 10 ] && echo "  ... and $((readme_count - 10)) more"
echo "  Total: $readme_count module READMEs"
