# pair-consult handoff and human-intervention helpers.
#
# Source once:
#   source ~/.claude/skills/pair-consult/reference/handoff.sh   # Claude Code
#   source ~/.agents/skills/pair-consult/reference/handoff.sh   # Codex
#
# Functions provided (all expect cwd at the repo root with .consult/ present):
#
#   Agent-side (called inside a round):
#     consult_handoff <peer>        — fire the peer headless, log to .consult/round-N-<peer>.log
#                                      AND append to .consult/session.log for live tailing.
#     consult_peer_status <peer>    — list running peer PIDs (do NOT killall by name).
#
#   Human-side:
#     consult_watch                 — tail -F .consult/session.log. Survives round boundaries.
#     consult_status                — terse one-screen summary: STATE.md + last 20 log lines.
#     consult_inject "<note>"       — append a USER_NOTE block to .consult/USER_NOTES.md.
#                                      Next agent must address it before their main action.
#     consult_takeover              — kill running peer by PID (via lsof on log files),
#                                      set STATUS: BLOCKED: human-takeover.
#     consult_resume <peer>         — set STATUS: WAITING: <peer>, fire consult_handoff.
#                                      Does NOT increment ROUND — manual takeovers don't add rounds.
#     consult_digest <N>            — print a terse 5-15 line summary of .consult/R<N>.md
#                                      (agreements + critique titles + verdict). Used by
#                                      the active agent to relay round content into chat.
#
# See SKILL.md's Hazards table for the bugs these functions guard against (claude
# flag-order, --add-dir variadic eating prompt, killall, --bare auth). Function
# bodies have inline comments explaining each fix at the point it's applied.

# ---------- agent-side ----------

consult_handoff() {
  local peer="$1"
  case "$peer" in
    codex|claude) ;;
    *) echo "consult_handoff: peer must be 'codex' or 'claude' (got '$peer')" >&2; return 2 ;;
  esac

  if [[ ! -f .consult/STATE.md ]]; then
    echo "consult_handoff: no .consult/STATE.md in $(pwd)" >&2
    return 2
  fi

  # Guard against firing with a stale STATE: STATE.md must say WAITING: <peer>
  # before we invoke. Catches the bug where the agent forgets to flip STATE
  # after writing their round.
  local state_status
  state_status=$(awk '/^STATUS:/ {sub(/^STATUS: */,""); print; exit}' .consult/STATE.md)
  if [[ "$state_status" != "WAITING: $peer" ]]; then
    echo "consult_handoff: STATE.md says STATUS='$state_status' but you're handing off to '$peer'." >&2
    echo "                 Update STATE.md first: 'STATUS: WAITING: $peer', then retry." >&2
    return 5
  fi

  if ! command -v "$peer" >/dev/null 2>&1; then
    echo "consult_handoff: peer CLI '$peer' not on PATH — write STATUS: BLOCKED and surface to the user" >&2
    return 3
  fi

  local round
  round=$(awk '/^ROUND:/ {print $2; exit}' .consult/STATE.md)
  if [[ -z "$round" ]]; then
    echo "consult_handoff: couldn't parse 'ROUND:' line from .consult/STATE.md" >&2
    return 2
  fi

  if (( round < 1 || round > 5 )); then
    echo "consult_handoff: ROUND=$round out of range; the loop has only 5 rounds." >&2
    return 2
  fi

  if (( round == 5 )); then
    echo "consult_handoff: R5 is the final round — do NOT invoke the peer." >&2
    echo "                  Set STATUS: AWAITING_USER in STATE.md and surface to the user." >&2
    return 4
  fi

  local logfile=".consult/round-${round}-${peer}.log"
  local session_log=".consult/session.log"
  local prompt="Resume the pair-consult skill. Read .consult/STATE.md and continue from STATUS: WAITING: ${peer}."

  {
    echo
    echo "=== R${round} ${peer} === $(date '+%Y-%m-%d %H:%M:%S')"
  } | tee -a "$logfile" >> "$session_log"

  # stdbuf -oL forces line-buffered stdout so logs appear incrementally.
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
      # flags before prompt; `--` terminates the variadic --add-dir so the
      # prompt isn't parsed as another directory.
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

  echo "consult_handoff: invoked $peer for round $round (pid $pid, log $logfile, live: consult_watch)"
}

consult_peer_status() {
  local peer="${1:-}"
  case "$peer" in
    codex|claude) ;;
    *) echo "consult_peer_status: peer must be 'codex' or 'claude'" >&2; return 2 ;;
  esac
  echo "consult_peer_status: running $peer processes (do NOT killall by name):"
  ps -axo pid,etime,command | grep -E "[ /]${peer}([[:space:]]|$)" | grep -v 'consult_peer_status' || echo "  (none)"
}

# ---------- human-side ----------

consult_watch() {
  if [[ ! -d .consult ]]; then
    echo "consult_watch: no .consult/ in $(pwd)" >&2
    return 2
  fi
  touch .consult/session.log
  echo "consult_watch: tailing .consult/session.log (Ctrl-C to exit)"
  echo "consult_watch: current state:"
  grep -E '^(STATUS|ROUND|ACTOR|A|B):' .consult/STATE.md 2>/dev/null | sed 's/^/  /'
  echo "--- live feed ---"
  tail -F .consult/session.log
}

consult_status() {
  if [[ ! -f .consult/STATE.md ]]; then
    echo "consult_status: no .consult/STATE.md in $(pwd)" >&2
    return 2
  fi
  echo "=== state ==="
  grep -E '^(STATUS|ROUND|ACTOR|A|B):' .consult/STATE.md | sed 's/^/  /'
  echo
  echo "=== user notes (mid-flight) ==="
  local notes=""
  if [[ -f .consult/USER_NOTES.md ]]; then
    notes=$(grep -E '^## N' .consult/USER_NOTES.md 2>/dev/null || true)
  fi
  if [[ -n "$notes" ]]; then
    echo "$notes" | sed 's/^/  /'
  else
    echo "  (none)"
  fi
  echo
  echo "=== last 20 lines of session.log ==="
  if [[ -s .consult/session.log ]]; then
    tail -20 .consult/session.log | sed 's/^/  /'
  else
    echo "  (no session activity yet)"
  fi
}

consult_inject() {
  local msg="$*"
  if [[ -z "$msg" ]]; then
    echo "consult_inject: usage: consult_inject \"<note for the agents>\"" >&2
    return 2
  fi
  if [[ ! -d .consult ]]; then
    echo "consult_inject: no .consult/ in $(pwd)" >&2
    return 2
  fi

  local notes_file=".consult/USER_NOTES.md"
  if [[ ! -f "$notes_file" ]]; then
    {
      echo "# User notes (mid-flight)"
      echo
    } > "$notes_file"
  fi

  local next_n
  next_n=$(grep -oE '^## N[0-9]+' "$notes_file" | sed 's/^## N//' | sort -n | tail -1)
  next_n=$((${next_n:-0} + 1))

  local round=""
  if [[ -f .consult/STATE.md ]]; then
    round=$(awk '/^ROUND:/ {print $2; exit}' .consult/STATE.md)
  fi

  {
    echo
    echo "## N${next_n} (added at $(date '+%Y-%m-%d %H:%M:%S'), during R${round:-?})"
    echo "${msg}"
    echo "**Status:** unaddressed"
  } >> "$notes_file"

  echo "consult_inject: added N${next_n} to $notes_file"
  echo "                next agent must address it before their round."
}

consult_takeover() {
  if [[ ! -d .consult ]]; then
    echo "consult_takeover: no .consult/ in $(pwd)" >&2
    return 2
  fi

  local pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -t .consult/round-*.log 2>/dev/null | sort -u)
  fi

  if [[ -z "$pids" ]]; then
    echo "consult_takeover: no peer process currently writing to .consult/round-*.log"
  else
    echo "consult_takeover: stopping peer PIDs: $pids"
    kill $pids 2>/dev/null
    sleep 1
    for p in $pids; do
      if kill -0 "$p" 2>/dev/null; then
        echo "consult_takeover: PID $p still alive, sending SIGKILL"
        kill -9 "$p" 2>/dev/null
      fi
    done
  fi

  if [[ -f .consult/STATE.md ]]; then
    sed -i.bak 's/^STATUS: .*/STATUS: BLOCKED: human-takeover/' .consult/STATE.md
    rm -f .consult/STATE.md.bak
    echo "consult_takeover: set STATUS: BLOCKED: human-takeover in .consult/STATE.md"
  fi

  echo "consult_takeover: the loop is paused. Work directly, then 'consult_resume <peer>' when ready."
}

# consult_digest <round-number> — print a terse 5-15 line summary of an R<N>.md
# for the agent to relay into chat. Extracts agreement bullets and critique
# titles; skips the full body. Use after each round completes to keep the
# user in the loop without forcing them to cat the file.
consult_digest() {
  local n="$1"
  if [[ -z "$n" || ! "$n" =~ ^[1-5]$ ]]; then
    echo "consult_digest: usage: consult_digest <1|2|3|4|5>" >&2
    return 2
  fi
  local f=".consult/R${n}.md"
  if [[ ! -f "$f" ]]; then
    echo "consult_digest: $f not found" >&2
    return 2
  fi

  # Helper: truncate each piped line to 110 chars with ellipsis
  _trunc() { awk '{ if (length > 110) print substr($0,1,107) "..."; else print }'; }

  echo "=== R${n} digest ($(head -1 "$f" | sed 's/^# //')) ==="

  # Agreements: bullets under "## Where A/B is right" or "## Agreed*"
  local agreed
  agreed=$(awk '
    /^## (Where [AB] is right|Agreed)/ { in_block=1; next }
    /^## / && in_block { in_block=0 }
    in_block && /^- / { print }
  ' "$f" 2>/dev/null || true)
  if [[ -n "$agreed" ]]; then
    echo "agreed:"
    echo "$agreed" | head -5 | sed 's/^/  /' | _trunc
  fi

  # Critique titles only (strip body after the bold title or em dash)
  local titles
  titles=$(grep -E '^([0-9]+\. )?(\*\*)?C[0-9]+' "$f" 2>/dev/null | head -8 \
    | sed -E '
        s/^[0-9]+\. \*\*(C[0-9]+:[^*]*)\*\*.*/\1/
        s/^\*\*(C[0-9]+:[^*]*)\*\*.*/\1/
        s/^## (C[0-9]+.*)$/\1/
    ' || true)
  if [[ -n "$titles" ]]; then
    echo "critiques:"
    echo "$titles" | sed 's/^/  /' | _trunc
  fi

  # Per-critique verdicts. Handles both R3 (`**Verdict:** agree|partial|object`)
  # and R4 (`**B's verdict:** accept|double down`).
  local verdicts
  verdicts=$(awk '
    /^## C[0-9]+/ { c=$0; sub(/^## /,"",c); sub(/ —.*/,"",c); sub(/ -.*/,"",c); next }
    /^\*\*(B.s )?[Vv]erdict:\*\*/ {
      v=$0
      sub(/^\*\*(B.s )?[Vv]erdict:\*\* */,"",v)
      if (c != "") print c ": " v
      c=""
    }
  ' "$f" 2>/dev/null || true)
  if [[ -n "$verdicts" ]]; then
    echo "per-C verdicts:"
    echo "$verdicts" | sed 's/^/  /' | _trunc
  fi

  # Overall verdict (R4 closer)
  local overall
  overall=$(awk '
    /^## (Overall verdict|Verdict overall)/ { in_v=1; next }
    /^## / && in_v { in_v=0 }
    in_v && NF > 0 { print; exit }
  ' "$f" 2>/dev/null || true)
  if [[ -n "$overall" ]]; then
    echo "overall verdict: $overall"
  fi

  unset -f _trunc
}

consult_resume() {
  local peer="$1"
  case "$peer" in
    codex|claude) ;;
    *) echo "consult_resume: usage: consult_resume <codex|claude>" >&2; return 2 ;;
  esac
  if [[ ! -f .consult/STATE.md ]]; then
    echo "consult_resume: no .consult/STATE.md in $(pwd)" >&2
    return 2
  fi

  # Unlike pair_resume, we do NOT bump ROUND — manual takeovers stay within
  # the current round. If you want to advance a round manually, edit STATE.md
  # before calling this.
  sed -i.bak "s/^STATUS: .*/STATUS: WAITING: ${peer}/" .consult/STATE.md
  rm -f .consult/STATE.md.bak

  echo "consult_resume: STATUS=WAITING:${peer} (ROUND unchanged)"
  consult_handoff "$peer"
}
