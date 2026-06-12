#!/usr/bin/env bash
# Deterministic eval for reference/handoff.sh — guards and STATE.md parsing.
# No agents are spawned: a no-op `codex` shim is put on PATH so the only
# side effects are log files inside a throwaway temp dir.
#
# Run:  bash evals/handoff-parsing.sh
# Exit: 0 = all checks pass, 1 = at least one failure (failures printed).

SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK" || exit 1

# No-op peer CLI so `command -v codex` passes without anything real running.
mkdir -p bin
printf '#!/bin/sh\nexit 0\n' > bin/codex
chmod +x bin/codex
export PATH="$WORK/bin:$PATH"

# shellcheck source=../reference/handoff.sh
source "$SKILL_DIR/reference/handoff.sh"

pass=0 fail=0
check() { # <desc> <expected-rc> <actual-rc>
  if [[ "$2" == "$3" ]]; then
    echo "ok   - $1"; pass=$((pass + 1))
  else
    echo "FAIL - $1 (expected rc=$2, got rc=$3)"; fail=$((fail + 1))
  fi
}

mkdir -p .optimize

# 1. A STATE.md copied verbatim from the file-formats template — inline
#    '# ...' comments included — must pass the status guard.
cat > .optimize/STATE.md <<'EOF'
# Optimize Session: eval

STATUS: WAITING: codex     # ACTIVE: <name> (init/R1 only) | WAITING: claude | WAITING: codex | AWAITING_USER | BLOCKED: <reason>
ROUND: 2
ROUNDS: 5                  # round cap (max) this session — odd, >=3, default 5; fixed for the session
A: claude                  # whoever measured the baseline in R1 — fixed for the session
B: codex                   # the peer — fixed for the session
EFFORT:                    # optional peer reasoning effort (high|xhigh); empty = each CLI's default
EOF
optimize_handoff codex >/dev/null 2>&1
check "template-faithful STATE.md (inline comments) passes the status guard" 0 $?
sleep 0.3   # let the no-op peer pipeline drain before the next test rewrites STATE.md

# 2. Stale STATUS (waiting on the other CLI) → refused, rc 5.
sed -i.bak 's/^STATUS: .*/STATUS: WAITING: claude/' .optimize/STATE.md
optimize_handoff codex >/dev/null 2>&1
check "stale STATUS (WAITING: claude vs handoff to codex) refused" 5 $?

# 3. The role letter is not a legal STATUS value → refused, rc 5.
sed -i.bak 's/^STATUS: .*/STATUS: WAITING: A/' .optimize/STATE.md
optimize_handoff codex >/dev/null 2>&1
check "role-letter STATUS (WAITING: A) refused" 5 $?

# 4. Final round (ROUND == ROUNDS) → handoff refuses, rc 4.
sed -i.bak -e 's/^STATUS: .*/STATUS: WAITING: codex/' -e 's/^ROUND: .*/ROUND: 5/' .optimize/STATE.md
optimize_handoff codex >/dev/null 2>&1
check "final-round handoff refused" 4 $?

# 5. optimize_wait fast path: STATUS not WAITING (with an inline comment)
#    → "nothing to wait for", rc 0, no polling.
sed -i.bak 's/^STATUS: .*/STATUS: AWAITING_USER          # session done/' .optimize/STATE.md
optimize_wait --interval 1 --timeout 3 >/dev/null 2>&1
check "wait returns immediately when STATUS is not WAITING" 0 $?

echo
echo "$pass passed, $fail failed"
[[ $fail -eq 0 ]]
