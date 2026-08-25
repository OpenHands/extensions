---
name: code-review-calibration
description: >-
  Investigates a repository end to end - commit history, bug fixes, reverts,
  house conventions, testing strategy, CI coverage, and past PR review
  comments - to learn how that specific codebase works and how it actually
  breaks, then writes or updates `.agents/skills/code-review.md` with the
  resulting failure patterns, conventions, and review rules. Use this
  whenever the user wants a code review skill for their repo, wants the
  reviewer calibrated or recalibrated, asks what this repo's recurring bugs,
  conventions, or problem areas are, asks where bugs cluster, asks what the
  testing norms are, or says the current review skill gives generic
  feedback. Also use when onboarding to an unfamiliar codebase and needing
  to know its idioms and dangerous areas. Prefer this over writing review
  guidelines from general principles - the entire point is that every rule
  comes from evidence in this repository.
---

# Code Review Calibration

Investigate this repository twice over: **how it breaks** (history) and
**how it works** (conventions). Encode both as a review skill at
`.agents/skills/code-review.md`.

**The output is a file, not a report.** Analysis that ends in the chat
window is wasted. Finish by writing the file.

## Why both halves matter

Defect history tells a reviewer what to fear. Conventions tell a reviewer
what "correct" looks like here, which is what lets them say "use
`scopedQuery()`" instead of "consider filtering by tenant." A reviewer
armed only with bug patterns produces suspicion; one that also knows the
house style produces fixes.

## Ground rules

**Statistics narrow the search; reading is the work.** The commands below
tell you which twenty commits and which six files to read out of thousands.
They do not tell you what the patterns are. A generated file full of
rankings and no named failure modes is a failed run.

**Two occurrences minimum for a failure pattern.** One is an anecdote.
Encoding it produces false positives forever and teaches the author to
ignore the reviewer. Conventions are different - an idiom followed
consistently across the codebase counts even without a bug behind it.

**Cite everything.** Failure patterns cite commit SHAs. Conventions cite
file paths where the idiom is visible. "This matches the bug in `9f2a1bc`"
and "the codebase does this in `db/query.ts:44`" both survive a skeptical
author. "Consider adding a null check" does not.

**Six to twelve failure patterns.** Past fifteen the review loses focus.
Keep the ones that were most *expensive* - reached production, caused
reverts, took several attempts - not the most frequent.

**Non-interactive gotcha:** several git commands read stdin when not
attached to a terminal and silently return nothing. Always pass an explicit
rev: `git shortlog -sn HEAD -- path`, never `git shortlog -sn -- path`.

---

# PART I - Orientation

## Phase 0 - Get your bearings

```bash
git rev-parse --show-toplevel && git log --oneline | wc -l
git log -1 --format=%ad --date=short && git log --reverse -1 --format=%ad --date=short
ls .agents/skills/ 2>/dev/null
```

If `.agents/skills/code-review.md` exists, read it now. You are updating
it, not replacing it - see **Update mode**.

Read whatever the project already says about itself. Anything documented
here is a convention you can confirm rather than infer:

```bash
cat CLAUDE.md AGENTS.md CONTRIBUTING.md ARCHITECTURE.md 2>/dev/null | head -120
ls .github/PULL_REQUEST_TEMPLATE* .github/pull_request_template* 2>/dev/null
```

Note the default branch; commands below assume `main`.

Get the shape of the codebase - languages, size, layout:

```bash
git ls-files | sed -n 's/.*\.\([a-zA-Z0-9]\+\)$/\1/p' | sort | uniq -c | sort -rn | head -12
git ls-files | awk -F/ 'NF>1{print $1"/"$2}' | sort | uniq -c | sort -rn | head -20
```

## Phase 1 - Calibrate fix detection (do not skip)

Everything in Part II depends on correctly identifying bug fixes. Get this
wrong and the run is noise. Find out how the team writes commit messages:

```bash
git log --no-merges --pretty=format:%s -800 \
  | grep -oiE '^[a-z]+(\([a-z0-9 _-]+\))?:' | sort | uniq -c | sort -rn | head
```

- **Shows `fix:`, `feat:`, `chore:`** → conventional commits. Use
  `--grep='^fix'` alone. Precise.
- **Empty or scattered** → prose messages. Use the broad pattern, then
  check the rate below.
- **Ticket refs** (`JIRA-123`, `#456`) → prefer matching the ticket
  pattern; if `gh` is available, cross-reference which issues were labeled
  as bugs.

```bash
TOT=$(git log --no-merges --oneline | wc -l)
FIX=$(git log --no-merges --oneline -i --grep='fix' --grep='bug' --grep='revert' | wc -l)
echo "total=$TOT fix=$FIX rate=$(( 100 * FIX / TOT ))%"
```

**A plausible fix rate is 10-25%.** Over 30% means over-matching - probably
catching "fix up", "prefix", "suffix". Tighten and re-run. Under 5% means
under-matching; widen. Record the pattern you settle on; the generated file
must document it so the next run is reproducible.

Set the exclusion list once and reuse it throughout. Add repo-specific
noise you spot (generated clients, docs sites, fixtures):

```bash
EXCL='(^|/)(vendor|node_modules|third_party|dist|build|target)/|\.(lock|sum|min\.js|min\.css|map|svg|png|jpg|woff2?)$|(package-lock|yarn\.lock|Cargo\.lock|poetry\.lock)'
```

---

# PART II - How this codebase breaks

## Phase 2 - Hotspots

Rank by *bug-fix* touches, not raw churn. Churn surfaces your router and
your config file; fix-density surfaces code people keep getting wrong.

```bash
git log --no-merges -i --grep='fix' --grep='bug' --grep='revert' \
    --since="18 months ago" --pretty=format: --name-only \
  | grep -vE "^$|$EXCL" | sort | uniq -c | awk '{print $2" "$1}' | sort > /tmp/fix.txt

git log --no-merges --since="18 months ago" --pretty=format: --name-only \
  | grep -vE "^$|$EXCL" | sort | uniq -c | awk '{print $2" "$1}' | sort > /tmp/all.txt

join /tmp/fix.txt /tmp/all.txt \
  | awk '$3>=5 {printf "%-4d %3d%% %-5d %s\n", $2, 100*$2/$3, $3, $1}' \
  | sort -rn | head -25
```

Columns: fixes, fix-ratio, total commits, path.

Read with judgment. 30 fixes out of 200 commits is a *busy* file. 12 out of
20 is a *broken* file - more interesting despite ranking lower. Weight
high-ratio files when choosing what to investigate. Drop files that no
longer exist (`git ls-files` to check).

## Phase 3 - Reverts and fix-inducing commits

### Reverts

Small sample, highest signal per item: something shipped, got through
review, and had to be pulled.

```bash
git log --no-merges -i --grep='^revert' --pretty=format:'%h %ad %s' --date=short | head -20
```

`git show` every one. Ask what a reviewer could plausibly have caught. If
the answer is "nothing, it was an infra failure," discard it.

### Fix-inducing commits (SZZ)

For each bug fix, blame the lines it *deleted* against the parent. That
points at what introduced the defect, so you read the change that caused
the problem rather than the one that cleaned it up.

```bash
git log --no-merges -i --grep='fix' --grep='bug' --since="18 months ago" \
    --pretty=format:%H | head -150 > /tmp/fixshas.txt
: > /tmp/introducers.txt

while read sha; do
  nf=$(git show --format= --name-only "$sha" | grep -c .)
  [ "$nf" -gt 25 ] && continue          # skip sweeps: reformats, mass renames
  git show -U0 --format= --no-renames --diff-filter=M "$sha" 2>/dev/null | awk '
    /^--- a\// { f=substr($0,7); next }
    /^@@ / && f { split($2,h,","); s=substr(h[1],2); c=(h[2]==""?1:h[2]);
                  if (c>0) print f" "s" "c }
  ' | while read f s c; do
      git blame -w --porcelain -L "$s,+$c" "$sha^" -- "$f" 2>/dev/null \
        | grep -oE '^[0-9a-f]{40}'
    done
done < /tmp/fixshas.txt >> /tmp/introducers.txt

sort /tmp/introducers.txt | uniq -c | sort -rn | head -20 | while read n s; do
  echo "$n  $(git show -s --format='%h %ad %s' --date=short $s | cut -c1-90)"
done
```

**Expect about half to be noise.** Blame credits whoever last rewrote a
line, so refactors float up without having caused anything. Published SZZ
benchmarks put precision near 0.6 - fine for "give me twenty commits to
read," useless as a verdict. Treat as leads.

Then do the actual work:

```bash
git show <introducing-sha>
git log --oneline --since=<its date> -- <the file it broke>
```

Read each introducing commit next to the fix that followed. **This is where
patterns come from.** Look for the shape of the mistake, not the mistake.

## Phase 4 - Temporal coupling

Files that keep changing together encode an invariant the codebase does not
enforce. Cross-module pairs are the useful ones.

```bash
git log --no-merges --since="18 months ago" --pretty=format:'@%H' --name-only | awk '
  /^@/ { if (n>1 && n<=25) for(i=1;i<n;i++) for(j=i+1;j<n;j++) {
           a=f[i]; b=f[j]; if(a>b){t=a;a=b;b=t} print a" "b }
         n=1; next }
  NF   { f[n++]=$0 }
' | grep -vE "$EXCL" | sort | uniq -c | sort -rn | head -30
```

Discard the uninformative - a file and its own test, a file and its
snapshot. Keep pairs crossing a module boundary, and pairs where one side
is generated from the other. These become "you touched X, did you update
Y?" rules.

---

# PART III - How this codebase works

This half is what lets the reviewer prescribe rather than merely suspect.

## Phase 5 - Conventions and idioms

Grepping for conventions across arbitrary languages does not generalize.
**Reading exemplars does.** Pick changes the team evidently considered
good - substantial, merged, not reverted, not later bug-fixed - and read
them as style specimens.

```bash
git log --no-merges --since="6 months ago" --pretty=format:'%h %ad %s' --date=short \
    --shortstat | grep -B1 -E '[0-9]+ files? changed' | head -60
```

Pick 5-8 with meaningful size (roughly 3-15 files) that are *not* in your
fix list, and read them in full: `git show <sha>`. Extract:

- **Error handling.** Exceptions or result types? Wrapped with context or
  bubbled raw? Is there a house error type? What happens at the boundary?
- **Logging and observability.** Which logger, what structure, what gets a
  trace or metric. Any rule about logging PII?
- **Config and secrets.** Env vars, a config object, injection?
- **Async and concurrency.** Which primitives are blessed, which avoided.
- **Boundaries.** Do handlers hit the DB directly or go through a
  repository layer? Where does validation live?

Then find the **blessed abstractions** - the internal helpers everything
imports. Adapt to the language, and filter to first-party prefixes or
stdlib imports will dominate:

```bash
# adjust glob + regex per language; filter to your own module prefix
git ls-files '*.ts' '*.tsx' | head -400 | tr '\n' '\0' \
  | xargs -0 grep -hoE "from ['\"][@~./][^'\"]*['\"]" 2>/dev/null \
  | sort | uniq -c | sort -rn | head -20
```

High-gravity internal modules are what a reviewer should redirect people
toward. If `lib/db/scoped.ts` has 90 importers and a new file queries the
ORM directly, that is a finding.

### Direction of travel

The most useful convention data is what the codebase is moving *away*
from. New code using a deprecated approach is a real, checkable defect -
and invisible without this step.

```bash
git log --no-merges -i --grep='migrat' --grep='refactor' --grep='deprecat' \
    --grep='replace' --grep='rewrite' --grep='switch to' --grep='move to' \
    --pretty='%h %ad %s' --date=short | head -25
```

Read the promising ones. Subjects like "consumer API is now deprecated" or
"use open_doc instead" hand you the rule directly. Also check for an
*unfinished* migration - if both old and new patterns exist in the tree,
the reviewer needs to know which side is which and that new code belongs on
the new side.

## Phase 6 - Testing strategy

Locate tests and identify the framework:

```bash
TESTPAT='(^|/)(tests?|spec|specs|__tests__)/|[._-](test|spec)\.[a-z]+$|(^|/)test_[^/]*$|_test\.[a-z]+$'
git ls-files | grep -E "$TESTPAT" | head -20
git ls-files | grep -cE "$TESTPAT"
cat package.json pyproject.toml Cargo.toml go.mod 2>/dev/null | grep -iE 'test|jest|vitest|pytest|mocha|rspec' | head
```

Read two or three test files near your hotspots. Note the idioms: fixtures
vs factories vs inline setup, what gets mocked and what runs for real, how
the database is handled, whether integration or e2e tiers exist and what
distinguishes them.

### Regression-test discipline

Measurable, and it tells you whether "add a test" is a real norm here or an
aspiration nobody enforces:

```bash
tot=0; wt=0
for sha in $(git log --no-merges -i --grep='fix' --grep='bug' --pretty=%H | head -150); do
  tot=$((tot+1))
  if git show --format= --name-only "$sha" | grep -qE "$TESTPAT"; then wt=$((wt+1)); fi
done
echo "fix commits=$tot  shipped with test changes=$wt  ($(( 100*wt/tot ))%)"
```

Interpretation:
- **60%+** → strong norm. A fix without a regression test is a legitimate,
  well-supported finding.
- **25-60%** → inconsistent. Worth raising, framed as a suggestion.
- **under 25%** → not a norm. Do *not* have the reviewer demand tests on
  every fix; it will be ignored and make the whole skill feel officious.
  Record the number honestly so the team can decide.

### Untested hotspots

The intersection of "breaks often" and "has no test" is the single
highest-value thing a reviewer can know. For each top hotspot, check
whether anything test-shaped ever changes alongside it:

```bash
for f in <top-hotspot-files>; do
  n=$(git log --no-merges --pretty=%H HEAD -- "$f" | head -60 | while read s; do
        git show --format= --name-only "$s" | grep -qE "$TESTPAT" && echo x
      done | wc -l)
  echo "$f -> co-changed with tests in $n of last 60 commits"
done
```

A hotspot that never co-changes with a test is a file where every change is
unverified. Say so explicitly.

## Phase 7 - What CI already enforces (the boundary)

**A reviewer that duplicates the linter is noise.** Establish what is
already automated so the generated skill can explicitly stay off it.

```bash
ls .github/workflows/ 2>/dev/null && cat .github/workflows/*.y*ml 2>/dev/null \
  | grep -E '^\s*-?\s*(run|uses|name):' | head -50
cat .pre-commit-config.yaml 2>/dev/null | grep -E 'repo:|id:' | head -20
ls .eslintrc* eslint.config.* .ruff.toml ruff.toml .rubocop.yml tsconfig.json 2>/dev/null
```

Check strictness too, because it changes what is worth flagging. A repo
with `strict: true` in tsconfig does not need a human watching nullability;
one without it very much does.

Write the list down. The generated file gets an explicit "already covered,
do not comment on" section. This is as important as anything in Part II -
it is what keeps reviews short enough to be read.

## Phase 8 - Ownership, stability, and blast radius

### Bus factor on hotspots

```bash
for f in <top-hotspot-files>; do
  echo "== $f"
  git log --no-merges --pretty=%an HEAD -- "$f" | sort | uniq -c | sort -rn | head -3
done
```

A single-author file with a high fix rate is dangerous in a specific way:
the person who understands it may not be the person reviewing the change.
Flag it so the reviewer can pull in the right human.

### Stability

```bash
git ls-files | head -500 | while read f; do
  echo "$(git log -1 --format=%ad --date=short HEAD -- "$f") $f"
done | sort | head -20
```

Code untouched for years is load-bearing and under-understood. A diff
touching it deserves more scrutiny than its size suggests, not less.

### Blast radius

Frequency-based analysis has a blind spot: code that rarely changes but is
catastrophic when wrong. Hotspots will never surface it. Find these by
inspection - auth and sessions, permission checks, payments and billing,
migrations, cryptography, anything touching PII, deletion paths, public API
contracts.

```bash
git ls-files | grep -iE 'auth|session|permission|billing|payment|migrat|crypto|secret|token|delete|purge' | head -30
```

These get their own list: **low frequency, high severity - scrutinize
regardless of diff size.**

---

# PART IV - What reviewers already say

## Phase 9 - GitHub PR reviews (optional)

Skip if `gh auth status` fails. When available it is valuable: the commit
log shows what broke, review comments show what the team *already knows* is
easy to get wrong. Patterns confirmed by both are the strongest you'll get.

```bash
REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

gh api "repos/$REPO/pulls/comments?per_page=100&sort=created&direction=desc" \
  --jq '.[] | [(.pull_request_url|split("/")|last), .user.login, .path, (.body|gsub("\n";" ")|.[0:180])] | @tsv' \
  > /tmp/review-comments.tsv
wc -l /tmp/review-comments.tsv
```

Find the **10 most recent substantial reviews** - where a reviewer engaged
rather than stamped. Group by PR, keep those with 3+ comments:

```bash
cut -f1 /tmp/review-comments.tsv | uniq -c | sort -rn | awk '$1>=3' | head -10
```

If that yields fewer than 10, paginate (`&page=2`) or fall back to PRs that
were sent back:

```bash
gh pr list --state merged --limit 40 --json number,title,reviewDecision \
  --jq '.[] | select(.reviewDecision=="CHANGES_REQUESTED") | "\(.number)\t\(.title)"'
```

Read each thread with its surrounding diff:

```bash
gh api "repos/$REPO/pulls/<N>/comments" \
  --jq '.[] | "--- \(.path):\(.line // .original_line) [\(.user.login)]\n\(.diff_hunk)\n>> \(.body)\n"'
```

Sort what you find into three buckets:

- **Substantive** - "needs the tenant filter", "this migration will lock",
  "you're swallowing the error". These become review patterns.
- **Conventional** - "use the `X` helper", "validation goes in the schema".
  These confirm or extend Phase 5, often more reliably than inference did.
- **Procedural** - nits, naming, changelog reminders. These belong in a
  linter or PR template, *not* a review skill. List them separately as
  automation candidates; that turns noise into a useful byproduct.

Note **who** raises what. A reviewer who consistently catches one class of
issue is institutional knowledge currently dependent on their availability.

---

# PART V - Synthesize and write

## Phase 10 - Synthesize

For each **failure pattern**:

1. **Trigger** - what must be in a diff to make this worth checking.
   Specific paths or constructs, not "when reviewing backend code."
2. **Failure** - what goes wrong, and *why it survived review last time*.
   If tests and review both passed, say what made it invisible.
3. **Tell** - what a reviewer can literally look for in the diff.
4. **Citations** - two or more SHAs. Non-negotiable.

For each **convention**: the rule, the blessed helper, and a file path
where it is visible.

Be specific to the point of discomfort. "Null pointer bugs" is not a
pattern. "New handlers under `api/` query the ORM directly instead of
through `scopedQuery()`, losing the tenant filter, and single-tenant test
fixtures never catch it" is - and note how it fuses a defect pattern with a
convention and a testing gap. Those fusions are the best output this
process produces; look for them deliberately.

Discard candidates whose cause was designed away. If a type change or new
helper made a bug class unrepresentable, that pattern is dead - record it
in Retired so nobody re-adds it.

Cross-check the halves against each other:

- A convention nobody follows *in the hotspot files* is worth flagging
  hard - that gap is likely causing the bugs.
- A failure pattern that CI now catches should be deleted, not documented.
- A hotspot that is also blast-radius and also untested is your headline
  finding. Lead with it.

## Phase 11 - Write the file

Write `.agents/skills/code-review.md`, creating `.agents/skills/` if
needed. The HTML comment markers matter - they let future runs regenerate
evidence sections without destroying human edits.

````markdown
---
name: code-review
description: >-
  Reviews changes against <REPO>'s own history and conventions - its
  documented failure patterns, hotspot files, house idioms, testing norms,
  and coupling rules, all derived from mining this repository. Use whenever
  the user asks for a code review, asks you to look over a diff, branch, PR,
  or staged changes, asks "does this look right" or "what could break", or
  is about to commit or open a pull request. Also use proactively after
  writing or modifying code in this repo, before reporting work as done.
---

# Code Review - <REPO>

Review against what has actually broken here and how this codebase is
actually written. Every finding cites a commit or a file path; findings
that cite nothing are nits and belong in the linter.

## Scope

1. User named a scope → use it.
2. Staged changes exist (`git diff --cached --stat`) → review those.
3. On a feature branch → `git diff $(git merge-base HEAD main)...HEAD`
4. Otherwise → `git show HEAD`

## Before reviewing

Check whether the diff touches a hotspot or blast-radius file below. If so,
say which, and raise scrutiny. Then per modified file:

```bash
git log --oneline -12 HEAD -- <file>
```

A hunk sitting on lines a recent fix touched is worth flagging on its own -
code just fixed and being changed again is code not well understood.

## Already covered by CI - do not comment on

<!-- BEGIN GENERATED: ci -->
<automated checks: linter, formatter, type checker, test suite, security
scan, and what each covers>

Raise these only when the diff would *disable* or *bypass* a check.
<!-- END GENERATED: ci -->

## Failure patterns

<!-- BEGIN GENERATED: patterns -->
### P1 - <name>

**Check when:** <specific trigger - paths, constructs>
**Failure:** <what breaks, and why review missed it last time>
**Tell:** <what to look for in the diff>
**Instead:** <the blessed approach, with the helper to use>
**Seen in:** `<sha>` (<date>, <context>), `<sha>` (...)
<!-- END GENERATED: patterns -->

## House conventions

Deviations are findings - cite the convention, not personal preference.

<!-- BEGIN GENERATED: conventions -->
**Error handling:** <rule> - see `<path>`
**Logging:** <rule> - see `<path>`
**Data access:** <rule> - see `<path>`
**Validation:** <rule> - see `<path>`
**Blessed helpers:** `<module>` (<n> importers) for <purpose>

**Direction of travel** - new code belongs on the new side:

| Deprecated | Current | Since |
|---|---|---|
| `<old>` | `<new>` | `<sha>` |
<!-- END GENERATED: conventions -->

## Testing expectations

<!-- BEGIN GENERATED: testing -->
**Framework:** <what> - tests in `<where>`, named `<pattern>`
**Idioms:** <fixtures/factories/mocking> - see `<path>`
**Regression discipline:** <n>% of bug fixes ship with test changes.
<Given that number: demand / suggest / do not raise regression tests.>
**Untested hotspots:** `<path>` - changes here are effectively unverified;
flag any non-trivial modification.
<!-- END GENERATED: testing -->

## Coupling rules

Touching one side without the other → ask why.

<!-- BEGIN GENERATED: coupling -->
| If the diff touches | It probably also needs | Co-changed |
|---|---|---:|
<!-- END GENERATED: coupling -->

## Hotspot files

<!-- BEGIN GENERATED: hotspots -->
| File | Bug fixes | Commits | Fix ratio | Primary author |
|---|---:|---:|---:|---|
<!-- END GENERATED: hotspots -->

## Blast radius

Rarely changed, expensive when wrong. Scrutinize regardless of diff size.

<!-- BEGIN GENERATED: blast -->
- `<path>` - <why it's severe>
<!-- END GENERATED: blast -->

## Reviewer conventions

<!-- BEGIN GENERATED: reviewers -->
Recurring substantive concerns from past reviews:
- <concern> - raised on #<pr>, #<pr>

Recurring procedural nits - should be automated, do not raise manually:
- <nit> - candidate for lint rule / PR template
<!-- END GENERATED: reviewers -->

## Output format

Group by confidence, highest first. Each finding: location, pattern or
convention matched, the evidence, the concrete fix.

```
### High confidence

**`src/billing/invoice.ts:142` - missing tenant scope on new query**
Matches P1. Same omission caused the leak fixed in `9f2a1bc` and again in
`44de0a1`. Use `scopedQuery()` (see `src/lib/db/scoped.ts`).
```

Close with which hotspot or blast-radius files the diff touched.

## Rules

- **Cite or drop it.** No historical evidence, no convention, no concrete
  failure mode → it is a nit. A short review that is all signal beats a
  long one people learn to skim.
- **Do not duplicate CI.** See the covered list above.
- **Do not restyle.** Formatting and naming are the formatter's job.
- **Say when it's clean.** If the diff avoids every known trap, say so and
  stop. Manufacturing findings trains people to ignore this skill.
- **Absence of a pattern is not absence of a bug.** The catalog covers what
  has broken before, not everything that can break. Still raise things that
  look wrong - mark them as judgment rather than documented pattern, and
  flag them as candidates for the catalog.

## Retired patterns

<!-- BEGIN GENERATED: retired -->
Kept so nobody re-adds a rule a design change made moot.
- <pattern> - retired <date>, <what made it impossible>
<!-- END GENERATED: retired -->

---
<!-- BEGIN GENERATED: provenance -->
Generated by `code-review-calibration` on <date>.
Window: <since>. Commits: <n>. Fix commits: <n> (<n>%).
Fix-detection pattern: `<regex>`
Exemplar changes read: <n>. PR reviews sampled: <n>.
Regenerate quarterly, or after any significant incident.
<!-- END GENERATED: provenance -->
````

## Update mode

If the file already existed:

- **Regenerate only marked sections.** Everything outside
  `<!-- BEGIN GENERATED -->` is human-authored. Leave it.
- **Never silently drop a pattern.** A pattern absent from new evidence may
  have been fixed - or your fix-regex may have changed. Move it to Retired
  with a reason; do not delete.
- **Preserve hand-written entries.** A pattern with no SHAs may come from
  an incident predating your window. Keep it, mark `(manually added)`.
- **Report the delta.** What changed between runs: new and retired
  patterns, hotspots that entered or left, whether regression-test
  discipline moved, conventions that shifted. That delta is often more
  interesting than the file.

## Finally

Report briefly: commits analyzed, the fix-detection pattern you settled on
and why, patterns kept versus discarded, conventions found, and your honest
confidence in each half.

The two halves fail independently. A young repo may have too little history
for good failure patterns while still having perfectly legible conventions
- in that case say the conventions half is solid and the history half thin,
and write the file with a strong conventions section and few patterns.
**Name the weak parts rather than padding with speculation.** Four
well-evidenced patterns beat twelve invented ones.
