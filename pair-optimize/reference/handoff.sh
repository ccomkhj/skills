# pair-optimize handoff and human-intervention helpers.
#
# Source once:
#   source ~/.claude/skills/pair-optimize/reference/handoff.sh   # Claude Code
#   source ~/.agents/skills/pair-optimize/reference/handoff.sh   # Codex
#
# Functions provided (all expect cwd at the repo root with .optimize/ present):
#
#   Agent-side (called inside a round):
#     optimize_handoff <peer>        — fire the peer headless, log to .optimize/round-N-<peer>.log
#                                      AND append to .optimize/session.log for live tailing.
#     optimize_wait                  — block until STATE.md flips off 'WAITING: <peer>'.
#                                      MUST be called after optimize_handoff (the nohup'd peer
#                                      is invisible to the Claude-Code harness, so without
#                                      this poll the agent has no way to learn the peer is
#                                      done). In Claude Code, invoke via Bash with
#                                      run_in_background=true so the harness notifies the
#                                      agent the instant the wait returns.
#     optimize_peer_status <peer>    — list running peer PIDs (do NOT killall by name).
#
#   Human-side:
#     optimize_watch                 — tail -F .optimize/session.log. Survives round boundaries.
#     optimize_status                — terse one-screen summary: STATE.md + last 20 log lines.
#     optimize_inject "<note>"       — append a USER_NOTE block to .optimize/USER_NOTES.md.
#                                      Next agent must address it before their main action.
#     optimize_takeover              — kill running peer by PID (via lsof on log files),
#                                      set STATUS: BLOCKED: human-takeover.
#     optimize_resume <peer>         — set STATUS: WAITING: <peer>, fire optimize_handoff.
#                                      Does NOT increment ROUND — manual takeovers don't add rounds.
#     optimize_digest <N>            — print a terse 5-15 line summary of .optimize/R<N>.md
#                                      (agreements + critique titles + verdict). Used by
#                                      the active agent to relay round content into chat.
#
# See SKILL.md's Hazards table for the bugs these functions guard against (claude
# flag-order, --add-dir variadic eating prompt, killall, --bare auth). Function
# bodies have inline comments explaining each fix at the point it's applied.

# ---------- agent-side ----------

optimize_handoff() {
  local peer="$1"
  case "$peer" in
    codex|claude) ;;
    *) echo "optimize_handoff: peer must be 'codex' or 'claude' (got '$peer')" >&2; return 2 ;;
  esac

  if [[ ! -f .optimize/STATE.md ]]; then
    echo "optimize_handoff: no .optimize/STATE.md in $(pwd)" >&2
    return 2
  fi

  # Guard against firing with a stale STATE: STATE.md must say WAITING: <peer>
  # before we invoke. Catches the bug where the agent forgets to flip STATE
  # after writing their round.
  # The trailing sub() strips inline '# ...' comments and whitespace, so a
  # STATE.md copied verbatim from the file-formats template still parses.
  local state_status
  state_status=$(awk '/^STATUS:/ {sub(/^STATUS: */,""); sub(/[[:space:]]*(#.*)?$/,""); print; exit}' .optimize/STATE.md)
  if [[ "$state_status" != "WAITING: $peer" ]]; then
    echo "optimize_handoff: STATE.md says STATUS='$state_status' but you're handing off to '$peer'." >&2
    echo "                 Update STATE.md first: 'STATUS: WAITING: $peer', then retry." >&2
    return 5
  fi

  if ! command -v "$peer" >/dev/null 2>&1; then
    echo "optimize_handoff: peer CLI '$peer' not on PATH — write STATUS: BLOCKED and surface to the user" >&2
    return 3
  fi

  local round
  round=$(awk '/^ROUND:/ {print $2; exit}' .optimize/STATE.md)
  if [[ -z "$round" ]]; then
    echo "optimize_handoff: couldn't parse 'ROUND:' line from .optimize/STATE.md" >&2
    return 2
  fi

  # Total rounds for this session. Defaults to 5 for back-compat with any
  # STATE.md written before the ROUNDS: field existed. Forced odd at init so
  # the final round always lands on A (the synthesizer); see SKILL.md.
  local rounds
  rounds=$(awk '/^ROUNDS:/ {print $2; exit}' .optimize/STATE.md)
  rounds=${rounds:-5}

  # Reasoning effort for the peer (optional). When empty we inject no flag and
  # each CLI uses its own default. Written once at init from --model.
  local effort
  effort=$(awk '/^EFFORT:/ {print $2; exit}' .optimize/STATE.md)

  if (( round < 1 || round > rounds )); then
    echo "optimize_handoff: ROUND=$round out of range; the loop has only $rounds rounds." >&2
    return 2
  fi

  if (( round == rounds )); then
    echo "optimize_handoff: R$rounds is the final round — do NOT invoke the peer." >&2
    echo "                  Set STATUS: AWAITING_USER in STATE.md and surface to the user." >&2
    return 4
  fi

  local logfile=".optimize/round-${round}-${peer}.log"
  local session_log=".optimize/session.log"
  local prompt="Resume the pair-optimize skill. Read .optimize/STATE.md and continue from STATUS: WAITING: ${peer}."

  {
    echo
    echo "=== R${round} ${peer} === $(date '+%Y-%m-%d %H:%M:%S')"
  } | tee -a "$logfile" >> "$session_log"

  # stdbuf -oL forces line-buffered stdout so logs appear incrementally.
  local buf=()
  if command -v stdbuf >/dev/null 2>&1; then
    buf=(stdbuf -oL -eL)
  fi

  # Per-CLI effort flag, only added when EFFORT: is set. codex takes it as a
  # config override (-c model_reasoning_effort=...); claude has a first-class
  # --effort. Both accept high|xhigh verbatim. Empty array = true no-op.
  local codex_effort=() claude_effort=()
  if [[ -n "$effort" ]]; then
    codex_effort=(-c "model_reasoning_effort=$effort")
    claude_effort=(--effort "$effort")
  fi

  case "$peer" in
    codex)
      ( nohup "${buf[@]}" codex exec \
          -s workspace-write \
          "${codex_effort[@]}" \
          -C "$(pwd)" \
          --skip-git-repo-check \
          "$prompt" 2>&1 \
        | tee -a "$logfile" >> "$session_log" ) &
      ;;
    claude)
      # flags before prompt; `--` terminates the variadic --add-dir so the
      # prompt isn't parsed as another directory. --effort must stay before --.
      ( nohup "${buf[@]}" claude -p \
          --dangerously-skip-permissions \
          "${claude_effort[@]}" \
          --add-dir "$(pwd)" \
          -- \
          "$prompt" 2>&1 \
        | tee -a "$logfile" >> "$session_log" ) &
      ;;
  esac

  local pid=$!
  disown

  echo "optimize_handoff: invoked $peer for round $round (pid $pid, log $logfile, live: optimize_watch)"
  echo "optimize_handoff: NEXT — call 'optimize_wait' (Bash run_in_background=true in Claude Code)."
  echo "                 The peer is nohup'd and invisible to the harness; without optimize_wait you will idle."
}

# optimize_wait — block until STATE.md flips off 'WAITING: <peer>'.
#
# Why this exists: optimize_handoff fires the peer via `nohup ... &`, which
# detaches it from the Claude-Code harness's process tracking. The harness
# therefore has no way to surface "peer is done" to the active agent — the
# agent would sit idle until the user happens to ping (which triggers a
# file-change reminder) or a manual ScheduleWakeup fires.
#
# optimize_wait closes that gap by polling .optimize/STATE.md. When invoked via
# Bash with run_in_background=true (Claude Code), the harness DOES track the
# wait-process, so the agent gets notified the instant this function returns.
# In Codex CLI or other contexts without run_in_background, call inline — it
# blocks the current turn until the peer's round lands (or timeout).
#
# Usage:
#   optimize_wait                    # default: 5s poll, 540s max wait
#   optimize_wait --interval 3
#   optimize_wait --timeout 300
#
# Exit codes:
#   0  STATUS changed off 'WAITING: <peer>' — your turn (or session done/blocked).
#   2  Timed out. Re-invoke, or run optimize_status to investigate.
#   3  Peer process died without writing the round file (lsof+mtime heuristic).
optimize_wait() {
  local interval=5
  local timeout=540
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --interval) interval="$2"; shift 2 ;;
      --timeout)  timeout="$2";  shift 2 ;;
      -h|--help)
        echo "Usage: optimize_wait [--interval SECONDS] [--timeout SECONDS]"
        return 0
        ;;
      *) echo "optimize_wait: unknown arg '$1'" >&2; return 2 ;;
    esac
  done

  if [[ ! -f .optimize/STATE.md ]]; then
    echo "optimize_wait: no .optimize/STATE.md in $(pwd)" >&2
    return 2
  fi

  # Use awk to both detect and extract — keeps the function portable across
  # bash and zsh (zsh has no BASH_REMATCH, and `status` is a read-only
  # special variable, so we use `cur_status` below). Trailing sub() strips
  # inline '# ...' comments so template-faithful STATE.md files parse.
  local initial peer
  initial=$(awk '/^STATUS:/ {sub(/^STATUS: */,""); sub(/[[:space:]]*(#.*)?$/,""); print; exit}' .optimize/STATE.md)
  peer=$(awk '/^STATUS:[[:space:]]*WAITING:/ {sub(/^STATUS:[[:space:]]*WAITING:[[:space:]]*/,""); sub(/[[:space:]]*(#.*)?$/,""); print; exit}' .optimize/STATE.md)
  if [[ -z "$peer" ]]; then
    echo "optimize_wait: STATUS is '$initial' (not 'WAITING: <peer>'). Nothing to wait for — act now."
    return 0
  fi

  local round
  round=$(awk '/^ROUND:/ {print $2; exit}' .optimize/STATE.md)
  local round_log=".optimize/round-${round}-${peer}.log"

  echo "optimize_wait: polling STATE.md every ${interval}s for status change off 'WAITING: ${peer}' (timeout ${timeout}s)..."

  local elapsed=0
  while (( elapsed < timeout )); do
    sleep "$interval"
    elapsed=$((elapsed + interval))

    # Init to "" — declaring a bare `local` inside a loop causes zsh to print
    # the variable each iteration (zsh's `local` is `typeset`, which echoes
    # parameter state in some forms).
    local cur_status=""
    cur_status=$(awk '/^STATUS:/ {sub(/^STATUS: */,""); sub(/[[:space:]]*(#.*)?$/,""); print; exit}' .optimize/STATE.md 2>/dev/null)
    if [[ "$cur_status" != "WAITING: $peer" ]]; then
      echo "optimize_wait: STATUS is now '$cur_status' after ${elapsed}s — your turn."
      return 0
    fi

    # Crash heuristic: after a few polls, if no process holds the round log
    # open AND the file hasn't been touched in 3*interval seconds, the peer
    # likely died (segfault, OOM, network drop on `claude -p`, etc.).
    if (( elapsed >= interval * 3 )) && [[ -f "$round_log" ]] && command -v lsof >/dev/null 2>&1; then
      if ! lsof -t "$round_log" >/dev/null 2>&1; then
        local log_mtime now stale
        log_mtime=$(stat -f %m "$round_log" 2>/dev/null || stat -c %Y "$round_log" 2>/dev/null)
        now=$(date +%s)
        stale=$((now - log_mtime))
        if (( stale > interval * 3 )); then
          echo "optimize_wait: no process writing $round_log and last write was ${stale}s ago — peer may have died." >&2
          echo "              Run 'optimize_status' / 'optimize_peer_status ${peer}' to investigate." >&2
          return 3
        fi
      fi
    fi
  done

  echo "optimize_wait: timed out after ${timeout}s (STATUS still 'WAITING: ${peer}'). Re-run optimize_wait or check 'optimize_status'." >&2
  return 2
}

optimize_peer_status() {
  local peer="${1:-}"
  case "$peer" in
    codex|claude) ;;
    *) echo "optimize_peer_status: peer must be 'codex' or 'claude'" >&2; return 2 ;;
  esac
  echo "optimize_peer_status: running $peer processes (do NOT killall by name):"
  ps -axo pid,etime,command | grep -E "[ /]${peer}([[:space:]]|$)" | grep -v 'optimize_peer_status' || echo "  (none)"
}

# ---------- human-side ----------

optimize_watch() {
  if [[ ! -d .optimize ]]; then
    echo "optimize_watch: no .optimize/ in $(pwd)" >&2
    return 2
  fi
  touch .optimize/session.log
  echo "optimize_watch: tailing .optimize/session.log (Ctrl-C to exit)"
  echo "optimize_watch: current state:"
  grep -E '^(STATUS|ROUND|ROUNDS|A|B):' .optimize/STATE.md 2>/dev/null | sed 's/^/  /'
  echo "--- live feed ---"
  tail -F .optimize/session.log
}

optimize_status() {
  if [[ ! -f .optimize/STATE.md ]]; then
    echo "optimize_status: no .optimize/STATE.md in $(pwd)" >&2
    return 2
  fi
  echo "=== state ==="
  grep -E '^(STATUS|ROUND|ROUNDS|A|B):' .optimize/STATE.md | sed 's/^/  /'
  echo
  echo "=== user notes (mid-flight) ==="
  local notes=""
  if [[ -f .optimize/USER_NOTES.md ]]; then
    notes=$(grep -E '^## N' .optimize/USER_NOTES.md 2>/dev/null || true)
  fi
  if [[ -n "$notes" ]]; then
    echo "$notes" | sed 's/^/  /'
  else
    echo "  (none)"
  fi
  echo
  echo "=== last 20 lines of session.log ==="
  if [[ -s .optimize/session.log ]]; then
    tail -20 .optimize/session.log | sed 's/^/  /'
  else
    echo "  (no session activity yet)"
  fi
}

optimize_inject() {
  local msg="$*"
  if [[ -z "$msg" ]]; then
    echo "optimize_inject: usage: optimize_inject \"<note for the agents>\"" >&2
    return 2
  fi
  if [[ ! -d .optimize ]]; then
    echo "optimize_inject: no .optimize/ in $(pwd)" >&2
    return 2
  fi

  local notes_file=".optimize/USER_NOTES.md"
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
  if [[ -f .optimize/STATE.md ]]; then
    round=$(awk '/^ROUND:/ {print $2; exit}' .optimize/STATE.md)
  fi

  {
    echo
    echo "## N${next_n} (added at $(date '+%Y-%m-%d %H:%M:%S'), during R${round:-?})"
    echo "${msg}"
    echo "**Status:** unaddressed"
  } >> "$notes_file"

  echo "optimize_inject: added N${next_n} to $notes_file"
  echo "                next agent must address it before their round."
}

optimize_takeover() {
  if [[ ! -d .optimize ]]; then
    echo "optimize_takeover: no .optimize/ in $(pwd)" >&2
    return 2
  fi

  local pids=""
  if command -v lsof >/dev/null 2>&1; then
    pids=$(lsof -t .optimize/round-*.log 2>/dev/null | sort -u)
  fi

  if [[ -z "$pids" ]]; then
    echo "optimize_takeover: no peer process currently writing to .optimize/round-*.log"
  else
    echo "optimize_takeover: stopping peer PIDs: $pids"
    kill $pids 2>/dev/null
    sleep 1
    for p in $pids; do
      if kill -0 "$p" 2>/dev/null; then
        echo "optimize_takeover: PID $p still alive, sending SIGKILL"
        kill -9 "$p" 2>/dev/null
      fi
    done
  fi

  if [[ -f .optimize/STATE.md ]]; then
    sed -i.bak 's/^STATUS: .*/STATUS: BLOCKED: human-takeover/' .optimize/STATE.md
    rm -f .optimize/STATE.md.bak
    echo "optimize_takeover: set STATUS: BLOCKED: human-takeover in .optimize/STATE.md"
  fi

  echo "optimize_takeover: the loop is paused. Work directly, then 'optimize_resume <peer>' when ready."
}

# optimize_digest <round-number> — print a terse 5-15 line summary of an R<N>.md
# for the agent to relay into chat. Extracts agreement bullets and critique
# titles; skips the full body. Use after each round completes to keep the
# user in the loop without forcing them to cat the file.
optimize_digest() {
  local n="$1"
  if [[ -z "$n" || ! "$n" =~ ^[1-9][0-9]*$ ]]; then
    echo "optimize_digest: usage: optimize_digest <round-number>" >&2
    return 2
  fi
  local f=".optimize/R${n}.md"
  if [[ ! -f "$f" ]]; then
    echo "optimize_digest: $f not found" >&2
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

  # Candidate / challenge titles only (C#-numbered). Strip body after the bold
  # title or em dash. Covers R1 candidates and R2 challenges alike.
  local titles
  titles=$(grep -E '^([0-9]+\. )?(\*\*)?C[0-9]+' "$f" 2>/dev/null | head -8 \
    | sed -E '
        s/^[0-9]+\. \*\*(C[0-9]+:[^*]*)\*\*.*/\1/
        s/^\*\*(C[0-9]+:[^*]*)\*\*.*/\1/
        s/^## (C[0-9]+.*)$/\1/
    ' || true)
  if [[ -n "$titles" ]]; then
    echo "candidates/challenges:"
    echo "$titles" | sed 's/^/  /' | _trunc
  fi

  # Per-candidate outcomes. Handles R3 (`**Result:** kept|reverted` + numbers)
  # and R4 (`**Verdict:** keep|revert|doubt-the-measurement`).
  local verdicts
  verdicts=$(awk '
    /^## C[0-9]+/ { c=$0; sub(/^## /,"",c); sub(/ —.*/,"",c); sub(/ -.*/,"",c); next }
    /^\*\*([Rr]esult|(B.s )?[Vv]erdict):\*\*/ {
      v=$0
      sub(/^\*\*([Rr]esult|(B.s )?[Vv]erdict):\*\* */,"",v)
      if (c != "") print c ": " v
      c=""
    }
  ' "$f" 2>/dev/null || true)
  if [[ -n "$verdicts" ]]; then
    echo "per-candidate result:"
    echo "$verdicts" | sed 's/^/  /' | _trunc
  fi

  # Overall verdict (R4 closer): keep-list / revert-list
  local overall
  overall=$(awk '
    /^## (Overall verdict|Verdict overall|Net result)/ { in_v=1; next }
    /^## / && in_v { in_v=0 }
    in_v && NF > 0 { print; exit }
  ' "$f" 2>/dev/null || true)
  if [[ -n "$overall" ]]; then
    echo "net result: $overall"
  fi

  unset -f _trunc
}

optimize_resume() {
  local peer="$1"
  case "$peer" in
    codex|claude) ;;
    *) echo "optimize_resume: usage: optimize_resume <codex|claude>" >&2; return 2 ;;
  esac
  if [[ ! -f .optimize/STATE.md ]]; then
    echo "optimize_resume: no .optimize/STATE.md in $(pwd)" >&2
    return 2
  fi

  # Unlike pair_resume, we do NOT bump ROUND — manual takeovers stay within
  # the current round. If you want to advance a round manually, edit STATE.md
  # before calling this.
  sed -i.bak "s/^STATUS: .*/STATUS: WAITING: ${peer}/" .optimize/STATE.md
  rm -f .optimize/STATE.md.bak

  echo "optimize_resume: STATUS=WAITING:${peer} (ROUND unchanged)"
  optimize_handoff "$peer"
}
