#!/usr/bin/env bash
# Scan for Workflows & Automation signals (Pillar 3)
# Helps the agent find relevant files — not a substitute for judgment.

REPO="${1:-.}"
cd "$REPO" 2>/dev/null || { echo "Cannot access $REPO"; exit 1; }

echo "=== Pillar 3: Workflows & Automation ==="
echo ""

echo "-- Issue templates --"
if [ -d .github/ISSUE_TEMPLATE ]; then
  echo ".github/ISSUE_TEMPLATE/:"
  ls -1 .github/ISSUE_TEMPLATE/ 2>/dev/null | while read f; do echo "  $f"; done
else
  echo "  (not found)"
fi

echo ""
echo "-- PR template --"
find . -maxdepth 3 -iname 'pull_request_template*' 2>/dev/null | sort
[ -f .github/pull_request_template.md ] || echo "  (not found)"

echo ""
echo "-- Dependency update automation --"
for f in .github/dependabot.yml .github/dependabot.yaml renovate.json .renovaterc \
         .renovaterc.json renovate.json5; do
  [ -f "$f" ] && echo "./$f"
done

echo ""
echo "-- Release automation --"
if [ -d .github/workflows ]; then
  grep -ril 'release\|publish\|deploy' .github/workflows/ 2>/dev/null | while read f; do
    echo "  $(basename "$f")"
  done
fi
for f in .releaserc .releaserc.json .releaserc.yml release-please-config.json \
         .goreleaser.yml .goreleaser.yaml; do
  [ -f "$f" ] && echo "./$f"
done

echo ""
echo "-- Branch protection signals --"
# Can't check GitHub settings from filesystem, but look for merge queue triggers
if [ -d .github/workflows ]; then
  grep -rl 'merge_group' .github/workflows/ 2>/dev/null | while read f; do
    echo "  merge_group trigger in $(basename "$f")"
  done
fi

echo ""
echo "-- Merge automation --"
find . -maxdepth 2 -name '.mergify.yml' -o -name 'mergify.yml' 2>/dev/null | sort
if [ -d .github/workflows ]; then
  grep -rl 'auto-merge\|automerge\|gh pr merge' .github/workflows/ 2>/dev/null | head -3
fi

echo ""
echo "-- Task runner --"
for f in Makefile GNUmakefile makefile Justfile justfile Taskfile.yml taskfile.yml \
         Rakefile Earthfile; do
  [ -f "$f" ] && echo "./$f"
done
if [ -f package.json ]; then
  script_count=$(python3 -c "import json; d=json.load(open('package.json')); print(len(d.get('scripts',{})))" 2>/dev/null)
  [ -n "$script_count" ] && echo "  package.json: $script_count scripts"
fi

echo ""
echo "-- Structured change tracking --"
[ -d .changeset ] && echo ".changeset/ ($(ls .changeset/*.md 2>/dev/null | wc -l | tr -d ' ') pending changesets)"
find . -maxdepth 2 -name 'commitlint.config.*' -o -name '.commitlintrc*' 2>/dev/null | sort
if [ -d .github/workflows ]; then
  grep -rl 'conventional-commits\|commitlint\|semantic-pull-request' .github/workflows/ 2>/dev/null | head -3
fi

echo ""
echo "-- CI concurrency control --"
if [ -d .github/workflows ]; then
  concurrency_count=$(grep -rl 'concurrency:' .github/workflows/ 2>/dev/null | wc -l | tr -d ' ')
  cancel_count=$(grep -rl 'cancel-in-progress' .github/workflows/ 2>/dev/null | wc -l | tr -d ' ')
  echo "  $concurrency_count workflows with concurrency groups, $cancel_count with cancel-in-progress"
fi

echo ""
echo "-- Automated release notes --"
for f in release-please-config.json .github/release.yml cliff.toml .cliff.toml; do
  [ -f "$f" ] && echo "./$f"
done
if [ -d .github/workflows ]; then
  grep -rl 'auto-changelog\|conventional-changelog\|git-cliff\|release-please' .github/workflows/ 2>/dev/null | head -3
fi

echo ""
echo "-- Stale issue management --"
if [ -d .github/workflows ]; then
  grep -rl 'stale' .github/workflows/ 2>/dev/null | while read f; do
    echo "  $(basename "$f")"
  done
fi
[ -f .github/stale.yml ] && echo ".github/stale.yml"

echo ""
echo "-- Label automation --"
find . -maxdepth 3 -name 'labeler.yml' -o -name '.github/labeler.yml' -o -name 'label-sync*' 2>/dev/null | sort

echo ""
echo "-- Multi-platform CI --"
if [ -d .github/workflows ]; then
  grep -rl 'matrix:' .github/workflows/ 2>/dev/null | while read f; do
    os_line=$(grep -A5 'matrix:' "$f" | grep -i 'os:' | head -1)
    [ -n "$os_line" ] && echo "  $(basename "$f"): $os_line"
  done
fi

echo ""
echo "-- Deployment automation --"
if [ -d .github/workflows ]; then
  grep -ril 'deploy' .github/workflows/ 2>/dev/null | while read f; do
    echo "  $(basename "$f")"
  done
fi
[ -f vercel.json ] && echo "./vercel.json"
[ -f netlify.toml ] && echo "./netlify.toml"
[ -f fly.toml ] && echo "./fly.toml"
[ -f render.yaml ] && echo "./render.yaml"
