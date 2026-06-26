#!/usr/bin/env bash
# haul-bg.sh — detached background driver for long-haul's haul-loop.
#
# Lets the haul keep running after the terminal (or the whole login session)
# closes — submit it on a remote box and let it grind overnight. A setsid+nohup'd
# shell loop drives ONE headless `claude -p` round at a time, runs the goal's
# check between rounds, and stops when the goal holds or the round cap trips.
# Each round's agent appends a structured block to PROGRESS.log.
#
# Usage — source it, then call the helpers (all operate on ./.longhaul):
#   source .../reference/haul-bg.sh
#   haul_bg_start     # detach and run to completion; safe to close the terminal after
#   haul_bg_status    # is it alive? + tail PROGRESS.log
#   haul_bg_stop      # kill the run (PID-group scoped)
# It re-execs itself as the driver via `bash haul-bg.sh __driver`.
#
# Hazards handled here — do NOT hand-roll these:
#   - nohup (+ setsid where present) so SIGHUP on terminal close doesn't kill the run.
#     setsid (Linux) gives the run its own session => survives full logout / remote
#     disconnect AND lets stop kill the whole process group. macOS has no setsid, so
#     it falls back to nohup+disown: survives terminal close but NOT logout, and stop
#     can only reap the leader + its direct `claude` child (see haul_bg_stop).
#   - stop is PID-scoped — NEVER `killall claude` (that kills the user's own session).
#   - `claude` flags BEFORE the prompt and a `--` terminator before it
#     (flags-after-prompt hangs; variadic flags otherwise eat the prompt)
#   - unattended => --permission-mode bypassPermissions (no human to approve);
#     blast radius is bounded by the per-round worktree

LONGHAUL_DIR="${LONGHAUL_DIR:-.longhaul}"
# Resolve this file's own path so the driver can re-exec it — works whether the
# helpers are sourced into bash or zsh (zsh leaves BASH_SOURCE empty).
if [ -n "${ZSH_VERSION:-}" ]; then _haul_bg_src="${(%):-%x}"; else _haul_bg_src="${BASH_SOURCE[0]}"; fi
_HAUL_BG_SELF="$(cd "$(dirname "$_haul_bg_src")" >/dev/null 2>&1 && pwd)/$(basename "$_haul_bg_src")"

# Read a STATE.md field. _haul_num extracts the leading integer only, so a value
# like "0 before haul" or a CRLF line ending can't wedge the driver's arithmetic.
_haul_state() { grep -m1 "^$1:" "$LONGHAUL_DIR/STATE.md" 2>/dev/null | sed "s/^$1:[[:space:]]*//"; }
_haul_num()   { _haul_state "$1" | tr -dc '0-9'; }
# Set (replace or append) a STATE.md field — used to record terminal status.
_haul_set() {
  local f="$1" v="$2" file="$LONGHAUL_DIR/STATE.md"
  if grep -q "^$f:" "$file" 2>/dev/null; then
    sed "s|^$f:.*|$f: $v|" "$file" > "$file.tmp" && mv "$file.tmp" "$file"
  else printf '%s: %s\n' "$f" "$v" >> "$file"; fi
}

haul_bg_alive() {
  local pid; pid="$(cat "$LONGHAUL_DIR/bg.pid" 2>/dev/null)" || return 1
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

haul_bg_start() {
  command -v claude >/dev/null || { echo "haul-bg: 'claude' not on PATH"; return 1; }
  [ -d "$LONGHAUL_DIR" ] || { echo "haul-bg: no $LONGHAUL_DIR — run /long-haul first"; return 1; }
  [ -f "$LONGHAUL_DIR/check.sh" ] || { echo "haul-bg: no $LONGHAUL_DIR/check.sh — background mode needs the goal's runnable check (exit 0 = met)"; return 1; }
  if haul_bg_alive; then echo "haul-bg: already running (PID $(cat "$LONGHAUL_DIR/bg.pid"))"; return 1; fi
  # The check.sh templates assume cwd = repo root; pin it so a detached run matches.
  local top; top="$(git rev-parse --show-toplevel 2>/dev/null)" && cd "$top" || { echo "haul-bg: not in a git repo"; return 1; }
  : > "$LONGHAUL_DIR/driver.log"
  local pid detach
  if command -v setsid >/dev/null 2>&1; then
    # Linux: own session — survives full logout / remote disconnect.
    setsid nohup bash "$_HAUL_BG_SELF" __driver >>"$LONGHAUL_DIR/driver.log" 2>&1 < /dev/null &
    pid=$!; detach="setsid (survives logout)"
  else
    # macOS et al.: no setsid — nohup+disown survives terminal close.
    nohup bash "$_HAUL_BG_SELF" __driver >>"$LONGHAUL_DIR/driver.log" 2>&1 < /dev/null &
    pid=$!; disown "$pid" 2>/dev/null || true; detach="nohup (survives terminal close)"
  fi
  echo "$pid" > "$LONGHAUL_DIR/bg.pid"
  echo "haul-bg: started PID $pid — $detach"
  echo "  progress: $LONGHAUL_DIR/PROGRESS.log    raw: $LONGHAUL_DIR/driver.log"
  echo "  safe to close the terminal now; stop with: haul_bg_stop"
}

haul_bg_status() {
  if haul_bg_alive; then echo "haul-bg: RUNNING (PID $(cat "$LONGHAUL_DIR/bg.pid"))"
  else echo "haul-bg: not running"; fi
  echo "--- tail $LONGHAUL_DIR/PROGRESS.log ---"
  tail -n 40 "$LONGHAUL_DIR/PROGRESS.log" 2>/dev/null
}

haul_bg_stop() {
  local pid; pid="$(cat "$LONGHAUL_DIR/bg.pid" 2>/dev/null)"
  [ -n "${pid:-}" ] || { echo "haul-bg: no bg.pid"; return 1; }
  # Reap the in-flight headless `claude` first (direct child of the driver), then
  # the process group (Linux/setsid), then the leader. Children before leader so
  # they don't reparent away. Never `killall claude` — that kills the user's session.
  pkill -P "$pid" 2>/dev/null; kill -- "-$pid" 2>/dev/null; kill "$pid" 2>/dev/null
  echo "haul-bg: stopped PID $pid"
  rm -f "$LONGHAUL_DIR/bg.pid"
}

_haul_round_prompt() {
  local n="$1"
  cat <<EOF
You are the long-haul BACKGROUND DRIVER running exactly ONE round — round $n — unattended, with no human present.
Read $LONGHAUL_DIR/STATE.md, GOAL.md, SPEC.md, and the most recent R*.md. Follow the haul-loop skill EXACTLY:
decide explore vs exploit (honor the stall rule and the "## Tried" list), spin $LONGHAUL_DIR/attempt off the right base,
implement per the /implement contract using ONLY the SPEC toolbox, run the goal's stated check in the worktree,
ratchet the incumbent (keep ONLY a measured win), tear the worktree down, update STATE.md, and write R$n.md.
Then APPEND one block to $LONGHAUL_DIR/PROGRESS.log in EXACTLY this format (use a real timestamp from \`date '+%F %T'\`):

[Loop$n]
start: <YYYY-MM-DD HH:MM:SS>
output: <one-line assessment of what this round produced and whether the check moved>
error message: <the failing check output or error this round, or "none">
next decision: <explore|exploit> (<why, citing the stall counter or a structural reason>) -> <the concrete change planned for next round>

Do exactly one round, then stop. Never start a second round. Do NOT run wrap-up, open a PR, push, or set GOAL-MET — the driver owns termination and a human confirms the PR later. Just do the round, update STATE.md/PROGRESS.log, and exit.
EOF
}

__haul_bg_driver() {
  set -uo pipefail
  local rounds start n before after
  rounds="$(_haul_num ROUNDS)"; rounds="${rounds:-8}"
  start="$(_haul_num ROUND)";   start="${start:-0}"
  for (( n = start + 1; n <= rounds; n++ )); do
    echo "=== driver: round $n / $rounds @ $(date '+%F %T') ==="
    local -a cflags=(--permission-mode bypassPermissions --add-dir "$PWD" -p)
    [ -n "${LONGHAUL_BG_MODEL:-}" ] && cflags+=(--model "$LONGHAUL_BG_MODEL")
    before="$(_haul_num ROUND)"
    claude "${cflags[@]}" -- "$(_haul_round_prompt "$n")" || echo "driver: claude exited $? on round $n"
    after="$(_haul_num ROUND)"
    # A healthy round bumps ROUND. If it didn't (claude crashed / API outage / hit
    # an output limit), DON'T march through the rest of the budget doing nothing —
    # abort and leave a clear marker so a human (or a re-launch) can resume.
    if [ "${after:-0}" = "${before:-0}" ]; then
      echo "=== driver: round $n made no progress (ROUND stuck at ${before:-0}) — aborting ==="
      printf '\n[Stopped] round %s made no progress (claude crash or limit); driver aborted @ %s\n' "$n" "$(date '+%F %T')" >> "$LONGHAUL_DIR/PROGRESS.log"
      _haul_set STATUS "BLOCKED: background round $n made no progress"
      rm -f "$LONGHAUL_DIR/bg.pid"; return 1
    fi
    if bash "$LONGHAUL_DIR/check.sh"; then
      echo "=== driver: goal check PASSED after round $n — stopping ==="
      printf '\n[Done] goal met after Loop%s @ %s\n' "$n" "$(date '+%F %T')" >> "$LONGHAUL_DIR/PROGRESS.log"
      # Durable handoff: a resuming /long-haul sees GOAL-MET and runs wrap-up.
      _haul_set PHASE wrap; _haul_set STATUS GOAL-MET
      rm -f "$LONGHAUL_DIR/bg.pid"; return 0
    fi
  done
  echo "=== driver: round cap ($rounds) reached without the goal — stopping ==="
  printf '\n[Stopped] round cap %s reached without the goal @ %s\n' "$rounds" "$(date '+%F %T')" >> "$LONGHAUL_DIR/PROGRESS.log"
  _haul_set STATUS "WAITING-USER: cap-decision"
  rm -f "$LONGHAUL_DIR/bg.pid"
}

[ "${1:-}" = "__driver" ] && __haul_bg_driver
