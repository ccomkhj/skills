# pair-coding handoff and human-intervention helpers.
#
# Source once:
#   source ~/.claude/skills/pair-coding/reference/handoff.sh   # Claude Code
#   source ~/.agents/skills/pair-coding/reference/handoff.sh   # Codex
#
# Functions provided (all expect cwd at the repo root with .pair/ present):
#
#   Agent-side (called inside a turn):
#     pair_handoff <peer>          — fire the peer headless, log to .pair/turn-N-<peer>.log
#                                     AND append to .pair/session.log for live tailing.
#     pair_peer_status <peer>      — list running peer PIDs (do NOT killall by name).
#
#   Human-side (called by the user steering the loop):
#     pair_watch                   — tail -F .pair/session.log. Survives turn boundaries.
#     pair_status                  — terse one-screen summary: state + open items + last 20 log lines.
#     pair_inject "<message>"      — append a USER-tagged item to .pair/DISCUSSION.md.
#                                     Next agent addresses it before continuing.
#     pair_constraint "<text>"     — append a bullet to .pair/CONTEXT.md → ## Constraints.
#                                     Becomes a hard constraint for every subsequent turn.
#     pair_takeover                — kill running peer processes by PID (via lsof on log files),
#                                     set STATUS: BLOCKED: human-takeover.
#     pair_resume <peer>           — set STATUS: WAITING: <peer>, bump TURN, fire pair_handoff.
#
# Designed to be hard to get wrong:
# - Correct CLI flags per peer (codex: sandbox + git-skip; claude: --dangerously-skip-permissions + --add-dir).
# - Flags BEFORE the prompt for claude -p (misordered flags hang the CLI).
# - nohup + & + disown so the peer runs detached.
# - All peer output also appended to .pair/session.log (per-turn logs preserved for forensics).
# - Refuses to invoke a peer that's not on PATH.
# - Never killall/pkill by name (would kill the user's primary interactive session).

# ---------- agent-side ----------

pair_handoff() {
  local peer="$1"
  case "$peer" in
    codex|claude) ;;
    *) echo "pair_handoff: peer must be 'codex' or 'claude' (got '$peer')" >&2; return 2 ;;
  esac

  if [[ ! -f .pair/PROGRESS.md ]]; then
    echo "pair_handoff: no .pair/PROGRESS.md in $(pwd)" >&2
    return 2
  fi

  # Guard against firing with a stale STATE: PROGRESS.md must say WAITING: <peer>
  # before we invoke. Catches the bug where the agent forgets to flip STATUS
  # after writing their turn.
  local state_status
  state_status=$(awk '/^STATUS:/ {sub(/^STATUS: */,""); print; exit}' .pair/PROGRESS.md)
  if [[ "$state_status" != "WAITING: $peer" ]]; then
    echo "pair_handoff: PROGRESS.md says STATUS='$state_status' but you're handing off to '$peer'." >&2
    echo "              Update PROGRESS.md first: 'STATUS: WAITING: $peer', then retry." >&2
    return 5
  fi

  if ! command -v "$peer" >/dev/null 2>&1; then
    echo "pair_handoff: peer CLI '$peer' not on PATH — write STATUS: BLOCKED to PROGRESS.md and surface to the user" >&2
    return 3
  fi

  local turn
  turn=$(awk '/^TURN:/ {print $2; exit}' .pair/PROGRESS.md)
  if [[ -z "$turn" ]]; then
    echo "pair_handoff: couldn't parse 'TURN:' line from .pair/PROGRESS.md" >&2
    return 2
  fi

  local logfile=".pair/turn-${turn}-${peer}.log"
  local session_log=".pair/session.log"
  local prompt="Resume the pair-coding skill. Read .pair/PROGRESS.md and continue from STATUS: WAITING: ${peer}."

  # Header so pair_watch readers can see turn boundaries clearly.
  {
    echo
    echo "=== T${turn} ${peer} === $(date '+%Y-%m-%d %H:%M:%S')"
  } | tee -a "$logfile" >> "$session_log"

  # Pipeline: agent → tee to per-turn log → append to session.log.
  # The whole pipeline is backgrounded; disown removes it from the job table.
  # stdbuf -oL forces line-buffered stdout so output appears in the log files
  # incrementally instead of in a single dump at exit. Without this, the peer
  # appears stuck for minutes (it's actually running fine, just buffered).
  local buf=()
  if command -v stdbuf >/dev/null 2>&1; then
    buf=(stdbuf -oL -eL)
  fi

  case "$peer" in
    codex)
      ( nohup "${buf[@]}" codex exec \
          -s workspace-write \
          -C "$(pwd)" \
          --skip-git-repo-check \
          "$prompt" 2>&1 \
        | tee -a "$logfile" >> "$session_log" ) &
      ;;
    claude)
      # flags MUST come before the prompt — misordered flags hang the CLI.
      # `--add-dir` is variadic ("directories..."), so without a `--` terminator
      # it gobbles the prompt as another directory and claude errors with
      # "Input must be provided either through stdin or as a prompt argument".
      # Do not pass --bare; it skips OAuth/keychain and errors "Not logged in"
      # unless ANTHROPIC_API_KEY is set.
      ( nohup "${buf[@]}" claude -p \
          --dangerously-skip-permissions \
          --add-dir "$(pwd)" \
          -- \
          "$prompt" 2>&1 \
        | tee -a "$logfile" >> "$session_log" ) &
      ;;
  esac

  local pid=$!
  disown

  echo "pair_handoff: invoked $peer for turn $turn (pid $pid, log $logfile, live: pair_watch)"
}

pair_peer_status() {
  local peer="${1:-}"
  case "$peer" in
    codex|claude) ;;
    *) echo "pair_peer_status: peer must be 'codex' or 'claude'" >&2; return 2 ;;
  esac
  echo "pair_peer_status: running $peer processes (do NOT killall by name):"
  ps -axo pid,etime,command | grep -E "[ /]${peer}([[:space:]]|$)" | grep -v 'pair_peer_status' || echo "  (none)"
}

# ---------- human-side ----------

pair_watch() {
  if [[ ! -d .pair ]]; then
    echo "pair_watch: no .pair/ in $(pwd)" >&2
    return 2
  fi
  # touch so tail -F doesn't error if no turn has run yet
  touch .pair/session.log

  echo "pair_watch: tailing .pair/session.log (Ctrl-C to exit)"
  echo "pair_watch: current state:"
  grep -E '^(STATUS|TURN|PHASE|STEP|NEXT_PROPOSER):' .pair/PROGRESS.md 2>/dev/null | sed 's/^/  /'
  echo "--- live feed ---"
  tail -F .pair/session.log
}

pair_status() {
  if [[ ! -f .pair/PROGRESS.md ]]; then
    echo "pair_status: no .pair/PROGRESS.md in $(pwd)" >&2
    return 2
  fi
  echo "=== state ==="
  grep -E '^(STATUS|TURN|PHASE|STEP|NEXT_PROPOSER):' .pair/PROGRESS.md | sed 's/^/  /'
  echo
  echo "=== open discussion items ==="
  local discussion_items=""
  if [[ -f .pair/DISCUSSION.md ]]; then
    discussion_items=$(grep -E '^## D' .pair/DISCUSSION.md 2>/dev/null || true)
  fi
  if [[ -n "$discussion_items" ]]; then
    echo "$discussion_items" | sed 's/^/  /'
  else
    echo "  (none)"
  fi
  echo
  echo "=== last 20 lines of session.log ==="
  if [[ -s .pair/session.log ]]; then
    tail -20 .pair/session.log | sed 's/^/  /'
  else
    echo "  (no session activity yet)"
  fi
}

pair_inject() {
  local msg="$*"
  if [[ -z "$msg" ]]; then
    echo "pair_inject: usage: pair_inject \"<message for the agents>\"" >&2
    return 2
  fi
  if [[ ! -f .pair/DISCUSSION.md ]]; then
    echo "pair_inject: no .pair/DISCUSSION.md (is .pair/ initialized?)" >&2
    return 2
  fi

  local next_d
  next_d=$(grep -oE '^## D[0-9]+' .pair/DISCUSSION.md | sed 's/^## D//' | sort -n | tail -1)
  next_d=$((${next_d:-0} + 1))

  local turn=""
  if [[ -f .pair/PROGRESS.md ]]; then
    turn=$(awk '/^TURN:/ {print $2; exit}' .pair/PROGRESS.md)
  fi

  # Strip the "(none)" placeholder if present
  if grep -qxE '\(none\)' .pair/DISCUSSION.md; then
    awk 'BEGIN{skipped=0} /^\(none\)$/ && skipped==0 {skipped=1; next} {print}' .pair/DISCUSSION.md > .pair/DISCUSSION.md.tmp \
      && mv .pair/DISCUSSION.md.tmp .pair/DISCUSSION.md
  fi

  {
    echo
    echo "## D${next_d} — [USER INPUT] (opened T${turn:-?} by user)"
    echo "**User:** ${msg}"
    echo "**Status:** open — both agents address this before continuing the current artifact."
  } >> .pair/DISCUSSION.md

  echo "pair_inject: added D${next_d} to .pair/DISCUSSION.md"
  echo "             next agent's turn will address it before continuing."
}

pair_constraint() {
  local text="$*"
  if [[ -z "$text" ]]; then
    echo "pair_constraint: usage: pair_constraint \"<constraint text>\"" >&2
    return 2
  fi
  if [[ ! -f .pair/CONTEXT.md ]]; then
    echo "pair_constraint: no .pair/CONTEXT.md (is .pair/ initialized?)" >&2
    return 2
  fi

  if ! grep -qE '^## Constraints$' .pair/CONTEXT.md; then
    echo "pair_constraint: no '## Constraints' section in CONTEXT.md — add one and retry" >&2
    return 2
  fi

  # Insert as a bullet immediately under the "## Constraints" header.
  # If the next non-blank line is "(none)" or similar, replace it; otherwise prepend.
  awk -v line="- ${text} (added by user)" '
    BEGIN {inserted=0}
    /^## Constraints$/ {print; in_section=1; next}
    in_section && !inserted {
      if ($0 ~ /^\(none[^)]*\)$/) { print line; inserted=1; next }
      if ($0 ~ /^- /) { print line; print; inserted=1; in_section=0; next }
      if ($0 ~ /^$/) { print line; print; inserted=1; in_section=0; next }
    }
    {print}
    END { if (!inserted) print line }
  ' .pair/CONTEXT.md > .pair/CONTEXT.md.tmp && mv .pair/CONTEXT.md.tmp .pair/CONTEXT.md

  echo "pair_constraint: added '${text}' under ## Constraints in .pair/CONTEXT.md"
  echo "                 both agents will treat it as binding from their next turn on."
}

pair_takeover() {
  if [[ ! -d .pair ]]; then
    echo "pair_takeover: no .pair/ in $(pwd)" >&2
    return 2
  fi

  # Find peer PIDs by identifying which processes have a .pair/turn-*.log open.
  # This is far safer than killing by name (which would kill the user's primary session).
  local pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -t .pair/turn-*.log 2>/dev/null | sort -u)
  fi

  if [[ -z "$pids" ]]; then
    echo "pair_takeover: no peer process currently writing to .pair/turn-*.log"
  else
    echo "pair_takeover: stopping peer PIDs: $pids"
    kill $pids 2>/dev/null
    sleep 1
    for p in $pids; do
      if kill -0 "$p" 2>/dev/null; then
        echo "pair_takeover: PID $p still alive, sending SIGKILL"
        kill -9 "$p" 2>/dev/null
      fi
    done
  fi

  if [[ -f .pair/PROGRESS.md ]]; then
    sed -i.bak 's/^STATUS: .*/STATUS: BLOCKED: human-takeover/' .pair/PROGRESS.md
    rm -f .pair/PROGRESS.md.bak
    echo "pair_takeover: set STATUS: BLOCKED: human-takeover in .pair/PROGRESS.md"
  fi

  echo "pair_takeover: the loop is paused. Work directly, then 'pair_resume <peer>' when ready."
}

pair_resume() {
  local peer="$1"
  case "$peer" in
    codex|claude) ;;
    *) echo "pair_resume: usage: pair_resume <codex|claude>" >&2; return 2 ;;
  esac
  if [[ ! -f .pair/PROGRESS.md ]]; then
    echo "pair_resume: no .pair/PROGRESS.md in $(pwd)" >&2
    return 2
  fi

  local current_turn
  current_turn=$(awk '/^TURN:/ {print $2; exit}' .pair/PROGRESS.md)
  local new_turn=$((${current_turn:-0} + 1))

  sed -i.bak \
    -e "s/^STATUS: .*/STATUS: WAITING: ${peer}/" \
    -e "s/^TURN: .*/TURN: ${new_turn}/" \
    .pair/PROGRESS.md
  rm -f .pair/PROGRESS.md.bak

  echo "pair_resume: STATUS=WAITING:${peer}, TURN=${new_turn}"
  pair_handoff "$peer"
}
