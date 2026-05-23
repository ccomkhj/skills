#!/usr/bin/env bash
# smoke.sh — driver for the pair-coding skill.
#
# --lint   Free, no LLM. Verifies the skill's frontmatter, that the pair-coding
#          SKILL.md still parses, and that the two peer CLIs (claude, codex)
#          are on PATH.
# --smoke  Costs ~10¢ in codex API. Sets up a throwaway repo with a
#          pre-staged spec, then invokes `codex exec` to perform one real turn
#          of the pair-coding loop. Verifies codex correctly read PROGRESS.md,
#          reviewed the spec, advanced TURN, and handed back to claude.
# default  --smoke
#
# Exit code 0 = pass, non-zero = fail.

set -euo pipefail

SKILL_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PAIR_SKILL_DIR="$( cd "$SKILL_DIR/../../.." && pwd )"
PAIR_SKILL_MD="$PAIR_SKILL_DIR/SKILL.md"

mode="${1:---smoke}"

lint() {
  echo "[lint] pair-coding SKILL.md at: $PAIR_SKILL_MD"
  [[ -f "$PAIR_SKILL_MD" ]] || { echo "FAIL: SKILL.md not found"; exit 1; }

  head -10 "$PAIR_SKILL_MD" | grep -qE '^name: pair-coding$' \
    || { echo "FAIL: frontmatter missing 'name: pair-coding'"; exit 1; }
  head -10 "$PAIR_SKILL_MD" | grep -qE '^description:' \
    || { echo "FAIL: frontmatter missing 'description:'"; exit 1; }
  echo "[lint] frontmatter OK"

  for bin in codex claude; do
    if command -v "$bin" >/dev/null 2>&1; then
      echo "[lint] $bin: $(command -v "$bin")"
    else
      echo "FAIL: $bin CLI not on PATH"
      exit 1
    fi
  done

  echo "PASS: lint"
}

smoke() {
  lint

  local test_dir="/tmp/pair-coding-smoke-$$-$(date +%s)"
  echo "[smoke] test dir: $test_dir"
  mkdir -p "$test_dir"
  cd "$test_dir"
  git init -q
  echo '.pair/' > .gitignore

  mkdir -p .pair

  cat > .pair/CONTEXT.md <<'EOF'
# Context

## Task
Implement `add(a, b)` in `mathlib.py` returning `a + b`, plus one pytest test for two positive ints.

## Constraints
- Single-file module, stdlib + pytest only.

## Glossary
(none)

## Resolved decisions
(none)
EOF

  cat > .pair/PROGRESS.md <<'EOF'
# Pair Session: smoke

STATUS: WAITING: codex
TURN: 1
PHASE: spec
STEP: n/a
NEXT_PROPOSER: codex

## Sign-offs
- [ ] spec — proposed by claude (T1), awaiting codex review
- [ ] plan
- [ ] code/1

## Turn log
| Turn | Actor  | Action                                   |
|------|--------|------------------------------------------|
| 1    | claude | Initialized .pair/, proposed SPEC.md     |
EOF

  cat > .pair/DISCUSSION.md <<'EOF'
# Open discussion items

(none)
EOF

  cat > .pair/SPEC.md <<'EOF'
# SPEC — mathlib.add (smoke)

## Problem
Provide a minimal `add` function.

## Scope
- `mathlib.py` exposing `add(a, b)` returning `a + b`.
- pytest test in `test_mathlib.py` for two positive ints.

## Out of scope
- Other arithmetic operations.
- Type hint enforcement.

## Acceptance
- `pytest -q` exits 0.
EOF

  echo "[smoke] invoking codex (this calls the real API; ~10c)..."
  codex exec \
    -s workspace-write \
    -C "$(pwd)" \
    --skip-git-repo-check \
    "Resume the pair-coding skill (~/.agents/skills/pair-coding/SKILL.md). Read .pair/PROGRESS.md and continue from STATUS: WAITING: codex." \
    > .pair/turn-2-codex.log 2>&1 || {
      echo "FAIL: codex exec returned non-zero"
      tail -40 .pair/turn-2-codex.log
      exit 1
    }

  echo "[smoke] verifying PROGRESS.md transitions..."
  if ! grep -qE '^STATUS: WAITING: claude$' .pair/PROGRESS.md; then
    echo "FAIL: STATUS did not transition to 'WAITING: claude'"
    echo "--- PROGRESS.md ---"
    cat .pair/PROGRESS.md
    exit 1
  fi
  if ! grep -qE '^TURN: 2$' .pair/PROGRESS.md; then
    echo "FAIL: TURN did not advance to 2"
    cat .pair/PROGRESS.md
    exit 1
  fi
  if ! grep -qE '^- \[x\] spec' .pair/PROGRESS.md; then
    echo "FAIL: spec was not signed off"
    cat .pair/PROGRESS.md
    exit 1
  fi

  echo "[smoke] PROGRESS.md after codex turn 2:"
  sed 's/^/  /' .pair/PROGRESS.md

  if [[ -f .pair/PLAN.md ]]; then
    echo "[smoke] bonus: codex compressed and also proposed PLAN.md"
  fi

  echo ""
  echo "PASS: smoke (artifacts in $test_dir)"
}

case "$mode" in
  --lint)  lint ;;
  --smoke) smoke ;;
  *) echo "usage: $0 [--lint|--smoke]  (default: --smoke)"; exit 2 ;;
esac
