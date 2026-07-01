# dual-haul worktree-race + human-intervention helpers.
#
# Source once (from the repo root, with .dualhaul/ present):
#   source ~/.claude/skills/dual-haul/reference/handoff.sh   # Claude Code orchestrator
#   source ~/.agents/skills/dual-haul/reference/handoff.sh   # (rarely needed; racers get a self-contained brief)
#
# THE MODEL
# ---------
# Unlike the other pair-* skills (one peer, ping-pong rounds), dual-haul runs a
# RACE: each round the orchestrator commissions TWO independent implementers —
# a Claude on a chosen model and Codex on a chosen model — each in its OWN git
# worktree off the current base commit. They never see each other. The
# orchestrator then judges both against the goal's stated check and merges the
# winner into the main tree.
#
# Functions (orchestrator-side, called inside a dual-loop round):
#   goal_race <round>        — create wt-claude/ + wt-codex/ worktrees off HEAD,
#                              spawn both racers detached on their chosen models,
#                              each fed the self-contained brief in
#                              .dualhaul/R<round>-brief.md. Logs to
#                              .dualhaul/round-<round>-<name>.log + session.log.
#   goal_wait_race <round>   — block until BOTH racers drop their .dualhaul-done
#                              sentinel (or timeout / crash heuristic). MUST follow
#                              goal_race — racers are nohup'd and invisible to the
#                              Claude Code harness, so without this poll the
#                              orchestrator idles. In Claude Code, invoke via Bash
#                              run_in_background=true so the harness notifies you
#                              the instant both land.
#   goal_teardown [round]    — remove both worktrees and delete their temp branches.
#                              Run after judging+merging, and on any abort.
#   goal_racer_status        — list running claude/codex racer PIDs (never killall).
#
# Human-side:
#   goal_watch               — tail -F .dualhaul/session.log (survives round boundaries).
#   goal_status              — one-screen: STATE.md + open notes + last 20 log lines.
#   goal_inject "<note>"     — append a USER_NOTE; the orchestrator addresses it next round.
#   goal_takeover            — kill running racers by PID (lsof on logs), set BLOCKED.
#
# Hazards these guard against (see SKILL.md Hazards): claude flag-order hang,
# --add-dir variadic eating the prompt, blanket killall, warm worktrees not torn
# down. Racers are spawned with PAIR_GOAL_ROLE=racer so they can't re-enter the
# orchestration helpers.

# ---------- orchestrator-side ----------

# Refuse if a racer process somehow sources this and calls an orchestrator fn.
_goal_refuse_if_racer() {
  if [[ "${PAIR_GOAL_ROLE:-}" == "racer" ]]; then
    echo "$1: you are a RACER — implement in your worktree, commit, touch .dualhaul-done, and EXIT." >&2
    echo "      Racers never orchestrate. Do not call goal_race / goal_wait_race / goal_teardown." >&2
    return 6
  fi
  return 0
}

goal_race() {
  _goal_refuse_if_racer goal_race || return 6

  local round="$1"
  if [[ -z "$round" || ! "$round" =~ ^[1-9][0-9]*$ ]]; then
    echo "goal_race: usage: goal_race <round-number>" >&2
    return 2
  fi
  if [[ ! -f .dualhaul/STATE.md ]]; then
    echo "goal_race: no .dualhaul/STATE.md in $(pwd)" >&2
    return 2
  fi
  local brief=".dualhaul/R${round}-brief.md"
  if [[ ! -s "$brief" ]]; then
    echo "goal_race: brief $brief missing/empty — orchestrator must write it before racing." >&2
    return 2
  fi
  if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "goal_race: not inside a git repo — worktrees require git." >&2
    return 2
  fi

  # Chosen racer models (the model-selection gate writes these). Empty => each
  # CLI's own default; we then inject no model flag.
  local cmodel xmodel
  cmodel=$(awk '/^RACER_CLAUDE:/ {sub(/^RACER_CLAUDE:[[:space:]]*/,""); print; exit}' .dualhaul/STATE.md)
  xmodel=$(awk '/^RACER_CODEX:/  {sub(/^RACER_CODEX:[[:space:]]*/,"");  print; exit}' .dualhaul/STATE.md)

  for peer in claude codex; do
    if ! command -v "$peer" >/dev/null 2>&1; then
      echo "goal_race: '$peer' not on PATH — cannot race. Set STATUS: BLOCKED and surface to user." >&2
      return 3
    fi
  done

  local session_log=".dualhaul/session.log"
  local base; base=$(git rev-parse --short HEAD)

  # Fresh worktrees each round, off the current base commit. Force-clean any
  # stragglers from a crashed prior round first.
  goal_teardown "$round" >/dev/null 2>&1
  local wt_claude=".dualhaul/wt-claude" wt_codex=".dualhaul/wt-codex"
  if ! git worktree add -q -b "dualhaul/r${round}-claude" "$wt_claude" HEAD 2>>"$session_log"; then
    echo "goal_race: failed to create $wt_claude worktree (branch dualhaul/r${round}-claude exists?). See $session_log." >&2
    return 4
  fi
  if ! git worktree add -q -b "dualhaul/r${round}-codex" "$wt_codex" HEAD 2>>"$session_log"; then
    echo "goal_race: failed to create $wt_codex worktree." >&2
    git worktree remove --force "$wt_claude" 2>/dev/null; git branch -D "dualhaul/r${round}-claude" 2>/dev/null
    return 4
  fi

  # Build the racer prompt = the brief + a self-contained tail instruction. The
  # racer's cwd IS its worktree; it commits there and drops the sentinel the
  # orchestrator polls. We assemble via a top-level heredoc-to-file (NOT
  # $(cat <<EOF ...)) — a heredoc inside command substitution whose body has
  # parens trips bash's parser.
  local promptfile=".dualhaul/R${round}-prompt.txt"
  cp "$brief" "$promptfile"
  cat >> "$promptfile" <<EOF

---
YOU ARE A RACER in a code race. Work ONLY inside your current directory, which is a git worktree. Another agent is solving the same goal independently and you will not see it. Do this and nothing else:
1. Implement changes in this directory toward the goal above.
2. Run the stated check and make it pass if you can. Put the check's output in your final message.
3. Commit: git add -A && git commit -m "dualhaul r${round} racer".
4. AFTER committing, mark done: touch .dualhaul-done
Then STOP. Never push, never edit anything outside this directory, never touch the parent repo's .dualhaul directory.
EOF
  local prompt; prompt=$(cat "$promptfile")

  {
    echo; echo "=== R${round} RACE (base ${base}) === $(date '+%Y-%m-%d %H:%M:%S')"
    echo "claude model: ${cmodel:-<default>}   codex model: ${xmodel:-<default>}"
  } >> "$session_log"

  local buf=(); command -v stdbuf >/dev/null 2>&1 && buf=(stdbuf -oL -eL)
  local cm=() xm=()
  [[ -n "$cmodel" ]] && cm=(--model "$cmodel")
  [[ -n "$xmodel" ]] && xm=(-m "$xmodel")

  # Claude racer. flags BEFORE prompt; `--` terminates the variadic --add-dir so
  # the prompt isn't eaten as a directory. cwd = the worktree.
  local clog=".dualhaul/round-${round}-claude.log"
  ( cd "$wt_claude" && PAIR_GOAL_ROLE=racer nohup "${buf[@]}" claude -p \
      --dangerously-skip-permissions \
      "${cm[@]}" \
      --add-dir "$(pwd)" \
      -- \
      "$prompt" 2>&1 | tee -a "../../$clog" >> "../../$session_log" ) &
  disown
  local cpid=$!

  # Codex racer. -C sets cwd to the worktree.
  local xlog=".dualhaul/round-${round}-codex.log"
  ( PAIR_GOAL_ROLE=racer nohup "${buf[@]}" codex exec \
      -s workspace-write \
      "${xm[@]}" \
      -C "$wt_codex" \
      --skip-git-repo-check \
      "$prompt" 2>&1 | tee -a "$xlog" >> "$session_log" ) &
  disown
  local xpid=$!

  echo "goal_race: R${round} launched — claude(pid $cpid, $clog) vs codex(pid $xpid, $xlog)"
  echo "goal_race: NEXT — call 'goal_wait_race ${round}' (Bash run_in_background=true in Claude Code)."
  echo "          Racers are nohup'd and invisible to the harness; without the wait you will idle."
}

# goal_wait_race <round> — block until BOTH racers drop .dualhaul-done.
# Exit codes: 0 both done; 2 timeout; 3 a racer likely died (no process, stale log, no sentinel).
goal_wait_race() {
  _goal_refuse_if_racer goal_wait_race || return 6

  local round="$1"; shift 2>/dev/null
  if [[ -z "$round" || ! "$round" =~ ^[1-9][0-9]*$ ]]; then
    echo "goal_wait_race: usage: goal_wait_race <round> [--interval S] [--timeout S]" >&2
    return 2
  fi
  local interval=5 timeout=900
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --interval) interval="$2"; shift 2 ;;
      --timeout)  timeout="$2";  shift 2 ;;
      *) echo "goal_wait_race: unknown arg '$1'" >&2; return 2 ;;
    esac
  done

  local cdone=".dualhaul/wt-claude/.dualhaul-done"
  local xdone=".dualhaul/wt-codex/.dualhaul-done"
  local clog=".dualhaul/round-${round}-claude.log"
  local xlog=".dualhaul/round-${round}-codex.log"

  echo "goal_wait_race: waiting for both racers to finish R${round} (poll ${interval}s, timeout ${timeout}s)..."
  local elapsed=0
  while (( elapsed < timeout )); do
    if [[ -f "$cdone" && -f "$xdone" ]]; then
      echo "goal_wait_race: both racers done after ${elapsed}s — judge now."
      return 0
    fi
    sleep "$interval"; elapsed=$((elapsed + interval))

    # Crash heuristic per racer: no holder on its log AND log stale AND no sentinel.
    if (( elapsed >= interval * 4 )) && command -v lsof >/dev/null 2>&1; then
      local who=""
      [[ ! -f "$cdone" ]] && _goal_log_dead "$clog" "$interval" && who="$who claude"
      [[ ! -f "$xdone" ]] && _goal_log_dead "$xlog" "$interval" && who="$who codex"
      if [[ -n "$who" ]]; then
        echo "goal_wait_race: racer(s)$who may have died (no process, stale log, no .dualhaul-done)." >&2
        echo "               Inspect with 'goal_racer_status' / tail $clog $xlog." >&2
        return 3
      fi
    fi
  done
  echo "goal_wait_race: timed out after ${timeout}s. Re-run, or 'goal_status' to investigate." >&2
  return 2
}

# returns 0 (true) if logfile has no open holder and is stale
_goal_log_dead() {
  local log="$1" interval="$2"
  [[ -f "$log" ]] || return 1
  lsof -t "$log" >/dev/null 2>&1 && return 1
  local m now; m=$(stat -f %m "$log" 2>/dev/null || stat -c %Y "$log" 2>/dev/null); now=$(date +%s)
  (( now - m > interval * 4 ))
}

goal_teardown() {
  _goal_refuse_if_racer goal_teardown || return 6
  local round="${1:-}"
  # 1) Remove the worktrees (git resolves the relative path itself, so no
  #    /private-vs-/var symlink mismatch). rm -rf is the fallback if the dir
  #    exists but git doesn't know it as a worktree.
  for name in claude codex; do
    local wt=".dualhaul/wt-${name}"
    [[ -d "$wt" ]] && { git worktree remove --force "$wt" 2>/dev/null || rm -rf "$wt"; }
  done
  # 2) Prune stale admin BEFORE deleting branches — otherwise git still thinks
  #    the branch is checked out in a (now-gone) worktree and refuses -D.
  git worktree prune 2>/dev/null
  # 3) Delete the round's temp branches.
  if [[ -n "$round" ]]; then
    for name in claude codex; do
      git branch -D "dualhaul/r${round}-${name}" 2>/dev/null
    done
  fi
  return 0
}

goal_racer_status() {
  echo "goal_racer_status: running racer processes (do NOT killall by name):"
  ps -axo pid,etime,command | grep -E '[ /](claude|codex)([[:space:]]|$)' \
    | grep -v 'goal_racer_status' || echo "  (none)"
}

# ---------- human-side ----------

goal_watch() {
  [[ -d .dualhaul ]] || { echo "goal_watch: no .dualhaul/ in $(pwd)" >&2; return 2; }
  touch .dualhaul/session.log
  echo "goal_watch: current state:"
  grep -E '^(PHASE|STATUS|ROUND|ROUNDS|RACER_CLAUDE|RACER_CODEX):' .dualhaul/STATE.md 2>/dev/null | sed 's/^/  /'
  echo "--- live feed (Ctrl-C to exit) ---"
  tail -F .dualhaul/session.log
}

goal_status() {
  [[ -f .dualhaul/STATE.md ]] || { echo "goal_status: no .dualhaul/STATE.md in $(pwd)" >&2; return 2; }
  echo "=== state ==="
  grep -E '^(PHASE|STATUS|ROUND|ROUNDS|RACER_CLAUDE|RACER_CODEX):' .dualhaul/STATE.md | sed 's/^/  /'
  echo; echo "=== user notes ==="
  if [[ -f .dualhaul/USER_NOTES.md ]]; then
    grep -E '^## N' .dualhaul/USER_NOTES.md 2>/dev/null | sed 's/^/  /' || echo "  (none)"
  else echo "  (none)"; fi
  echo; echo "=== last 20 lines of session.log ==="
  [[ -s .dualhaul/session.log ]] && tail -20 .dualhaul/session.log | sed 's/^/  /' || echo "  (no activity yet)"
}

goal_inject() {
  local msg="$*"
  [[ -n "$msg" ]] || { echo "goal_inject: usage: goal_inject \"<note>\"" >&2; return 2; }
  [[ -d .dualhaul ]] || { echo "goal_inject: no .dualhaul/ in $(pwd)" >&2; return 2; }
  local f=".dualhaul/USER_NOTES.md"
  [[ -f "$f" ]] || { echo "# User notes (mid-flight)"; echo; } > "$f"
  local n; n=$(grep -oE '^## N[0-9]+' "$f" | sed 's/^## N//' | sort -n | tail -1); n=$((${n:-0}+1))
  local round=""; [[ -f .dualhaul/STATE.md ]] && round=$(awk '/^ROUND:/ {print $2; exit}' .dualhaul/STATE.md)
  { echo; echo "## N${n} (added $(date '+%Y-%m-%d %H:%M:%S'), during R${round:-?})"; echo "$msg"; echo "**Status:** unaddressed"; } >> "$f"
  echo "goal_inject: added N${n} — the orchestrator must address it before the next round."
}

goal_takeover() {
  [[ -d .dualhaul ]] || { echo "goal_takeover: no .dualhaul/ in $(pwd)" >&2; return 2; }
  local pids=""
  command -v lsof >/dev/null 2>&1 && pids=$(lsof -t .dualhaul/round-*.log 2>/dev/null | sort -u)
  if [[ -z "$pids" ]]; then
    echo "goal_takeover: no racer currently writing .dualhaul/round-*.log"
  else
    echo "goal_takeover: stopping racer PIDs: $pids"; kill $pids 2>/dev/null; sleep 1
    for p in $pids; do kill -0 "$p" 2>/dev/null && { echo "  SIGKILL $p"; kill -9 "$p" 2>/dev/null; }; done
  fi
  if [[ -f .dualhaul/STATE.md ]]; then
    sed -i.bak 's/^STATUS: .*/STATUS: BLOCKED: human-takeover/' .dualhaul/STATE.md; rm -f .dualhaul/STATE.md.bak
    echo "goal_takeover: STATUS: BLOCKED: human-takeover. Work directly, then re-run the orchestrator to resume."
  fi
}
