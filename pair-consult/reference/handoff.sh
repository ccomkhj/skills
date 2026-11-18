# pair-consult helpers. Source this file, don't read it: every helper prints what to do next.
#
#   source <skill-dir>/reference/handoff.sh      (bash or zsh, cwd = repo root)
#
# Orchestrator (A):
#   consult_init <me> <peer> [rounds] [effort]   create .consult/ and STATE.md
#   consult_handoff [--fresh]                    start B's next round (resumes B's session unless --fresh)
#   consult_wait [--timeout s] [--interval s]    block until B's round lands, then print its digest
#   consult_close                                final round written -> STATUS: AWAITING_USER
#   consult_digest <N>                           terse summary of .consult/R<N>.md for chat
#   consult_status | consult_takeover | consult_resume [--fresh]
# Human, second terminal:
#   consult_watch | consult_inject "<note>"
#
# .consult/STATE.md is written only by these helpers:
#   STATUS: WAITING: <cli> | AWAITING_USER | BLOCKED: <reason>    <cli> owes round ROUND
#   ROUND:  the round being worked on
#   ROUNDS: round cap, odd and >= 3, so A both proposes and synthesizes
#   A / B:  orchestrator CLI / reviewer CLI (claude | codex), fixed for the session
#   EFFORT: reviewer reasoning effort (high | xhigh)
#
# B never touches STATE.md. It writes .consult/R<ROUND>.md and exits; consult_wait sees the
# exit and advances the state. One writer, so two instances cannot collide on the file.

_CONSULT_HOME="$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" && pwd)"

_consult_get() {
  awk -v k="$1" 'index($0, k ":") == 1 {
    sub(/^[^:]*:[[:space:]]*/, ""); sub(/[[:space:]]*(#.*)?$/, ""); print; exit
  }' .consult/STATE.md
}

_consult_set() {
  awk -v k="$1" -v v="$2" 'index($0, k ":") == 1 && !done { print k ": " v; done = 1; next } { print }' \
    .consult/STATE.md > .consult/STATE.md.tmp && mv .consult/STATE.md.tmp .consult/STATE.md
}

# Guard shared by every orchestrator verb. A reviewer that handed off would spawn a second
# orchestrator racing the live one, so the peer process is marked and refused here.
_consult_guard() {
  if [[ -n "${PAIR_CONSULT_PEER:-}" ]]; then
    echo "$1: you are the reviewer. Write your .consult/R<round>.md and exit; the orchestrator advances the session." >&2
    return 6
  fi
  if [[ "$1" != consult_init && ! -f .consult/STATE.md ]]; then
    echo "$1: no .consult/STATE.md in $(pwd). Run from the repo root, or start with consult_init." >&2
    return 2
  fi
}

_consult_peer_alive() {
  local pid=""
  [[ -f .consult/peer.pid ]] && pid=$(cat .consult/peer.pid)
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

# ---------- orchestrator ----------

consult_init() {
  _consult_guard consult_init || return
  local me="${1:-}" peer="${2:-}" rounds="${3:-5}" effort="${4:-high}"
  case "$me:$peer" in
    claude:codex|codex:claude) ;;
    *) echo "consult_init: usage: consult_init <me> <peer> [rounds] [effort]; me/peer are claude and codex, one each" >&2; return 2 ;;
  esac
  case "$rounds" in ''|*[!0-9]*) echo "consult_init: rounds must be a number (got '$rounds')" >&2; return 2 ;; esac
  case "$effort" in high|xhigh) ;; *) echo "consult_init: effort must be high or xhigh (got '$effort')" >&2; return 2 ;; esac
  if [[ -f .consult/STATE.md ]]; then
    echo "consult_init: .consult/ already holds a session ($(_consult_get STATUS), round $(_consult_get ROUND))." >&2
    echo "              Resume it, or ask the user before 'rm -rf .consult' for a fresh start." >&2
    return 2
  fi
  if ! command -v "$peer" >/dev/null 2>&1; then
    echo "consult_init: peer CLI '$peer' is not on PATH. Tell the user; no consult without a reviewer." >&2
    return 3
  fi

  local asked="$rounds"
  (( rounds < 3 )) && rounds=3
  (( rounds % 2 == 0 )) && rounds=$((rounds + 1))
  if [[ "$asked" != "$rounds" ]]; then
    echo "consult_init: $asked rounds can't start and end on A (propose ... synthesize); using a $rounds-round cap. Tell the user."
  fi

  mkdir -p .consult
  # Local ignore, so the session never shows up in the diff B reviews or in a commit.
  local exclude
  if exclude=$(git rev-parse --git-path info/exclude 2>/dev/null) && ! git check-ignore -q .consult 2>/dev/null; then
    mkdir -p "$(dirname "$exclude")" && echo ".consult/" >> "$exclude"
  fi

  cat > .consult/STATE.md <<EOF
# pair-consult state (written by handoff.sh helpers only)
STATUS: WAITING: $me
ROUND: 1
ROUNDS: $rounds
A: $me
B: $peer
EFFORT: $effort
EOF
  echo "consult_init: session ready. A=$me, B=$peer, $rounds-round cap, effort $effort."
  echo "consult_init: NEXT: write .consult/QUESTION.md and .consult/R1.md, then consult_handoff."
}

consult_handoff() {
  _consult_guard consult_handoff || return
  local fresh=0 arg
  for arg in "$@"; do
    case "$arg" in
      --fresh) fresh=1 ;;
      *) echo "consult_handoff: usage: consult_handoff [--fresh]" >&2; return 2 ;;
    esac
  done

  local a b round rounds effort cur
  a=$(_consult_get A); b=$(_consult_get B)
  round=$(_consult_get ROUND); rounds=$(_consult_get ROUNDS); effort=$(_consult_get EFFORT)
  cur=$(_consult_get STATUS)
  if [[ -z "$round" || -z "$rounds" || -z "$effort" ]]; then
    echo "consult_handoff: STATE.md is missing one of ROUND, ROUNDS, EFFORT." >&2
    return 2
  fi
  case "$a:$b" in
    claude:codex|codex:claude) ;;
    *) echo "consult_handoff: STATE.md needs A and B to be claude and codex, one each (got A='$a', B='$b')." >&2; return 2 ;;
  esac
  if _consult_peer_alive; then
    echo "consult_handoff: a reviewer is already running (pid $(cat .consult/peer.pid)). Run consult_wait instead." >&2
    return 5
  fi

  local flip=0
  case "$cur" in
    "WAITING: $a")
      if (( round >= rounds )); then
        echo "consult_handoff: round $round is the final round and it is yours. Write .consult/R${rounds}.md, then consult_close." >&2
        return 4
      fi
      if [[ ! -s ".consult/R${round}.md" ]]; then
        echo "consult_handoff: write .consult/R${round}.md first; B reviews that file." >&2
        return 5
      fi
      round=$((round + 1)); flip=1
      ;;
    "WAITING: $b") ;;   # B owes this round already: retry after a failed round, or consult_resume
    *)
      echo "consult_handoff: STATUS is '$cur'; nothing to hand off." >&2
      return 5
      ;;
  esac

  # The last B round re-reviews A's answers; it only exists when an A response precedes it.
  local kind="review"
  (( rounds >= 5 && round == rounds - 1 )) && kind="re-review"

  # Resume B's own session when it has one: it already holds the question, the code it read
  # and its own critiques, so a later round costs a fraction of a cold start.
  # Only once B has finished a round, so a retry of a failed first round starts clean.
  local sid=""
  if (( ! fresh && round > 2 )) && [[ -f .consult/session.log ]]; then
    sid=$(awk '/^session id: / { id = $3 } END { print id }' .consult/session.log)
  fi

  local files=".consult/QUESTION.md" i
  for (( i = 1; i < round; i++ )); do
    [[ -f ".consult/R${i}.md" ]] && files="$files, .consult/R${i}.md"
  done
  local notes=""
  [[ -f .consult/USER_NOTES.md ]] && notes=" Then .consult/USER_NOTES.md."

  # Same brief for a cold start and a resumed session; only the reading list differs. The
  # last sentence stops the reviewer CLI from loading this skill by name: SKILL.md is the
  # orchestrator's document and costs the reviewer a few thousand tokens for nothing.
  local reading="Read ${files}."
  [[ -n "$sid" ]] && reading="A's latest round is .consult/R$((round - 1)).md: read it, and re-check any code or evidence A changed."
  local prompt="pair-consult round ${round} of ${rounds}: a ${kind}. ${reading}${notes} Write .consult/R${round}.md. Your brief follows and is complete: work from it and these files, without loading any skill.

$(cat "$_CONSULT_HOME/peer.md")"

  if (( flip )); then
    _consult_set ROUND "$round"
    _consult_set STATUS "WAITING: $b"
  fi

  local logfile=".consult/round-${round}-${b}.log" session_log=".consult/session.log"
  { echo; echo "=== R${round} ${b} (${kind}) === $(date '+%Y-%m-%d %H:%M:%S')"; } | tee -a "$logfile" >> "$session_log"

  # stdbuf -oL forces line-buffered stdout so the log is live.
  local buf=()
  command -v stdbuf >/dev/null 2>&1 && buf=(stdbuf -oL -eL)

  # Codex model is pinned so the reviewer doesn't drift with ~/.codex/config.toml.
  local codex_model="${PAIR_CONSULT_CODEX_MODEL:-gpt-6-astra}" how="cold start"
  [[ -n "$sid" ]] && how="resumed session $sid"

  # nohup + & detaches the reviewer so it survives this shell; consult_wait is what the
  # harness tracks. stdin is /dev/null because codex appends piped stdin to the prompt.
  case "$b" in
    codex)
      if [[ -n "$sid" ]]; then
        # resume takes the cwd from this shell; model and sandbox must be re-asserted.
        ( PAIR_CONSULT_PEER=1 nohup "${buf[@]}" codex exec resume \
            --skip-git-repo-check \
            -m "$codex_model" \
            -c "model_reasoning_effort=$effort" \
            -c 'sandbox_mode="workspace-write"' \
            "$sid" "$prompt" </dev/null 2>&1 \
          | tee -a "$logfile" >> "$session_log" ) &
      else
        ( PAIR_CONSULT_PEER=1 nohup "${buf[@]}" codex exec \
            -s workspace-write \
            -m "$codex_model" \
            -c "model_reasoning_effort=$effort" \
            -C "$(pwd)" \
            --skip-git-repo-check \
            "$prompt" </dev/null 2>&1 \
          | tee -a "$logfile" >> "$session_log" ) &
      fi
      ;;
    claude)
      # Flags go before the prompt (after it they hang the CLI), and `--` ends the variadic
      # --add-dir so the prompt isn't parsed as a directory. No --bare: it breaks auth.
      local session_flag=(--resume "$sid")
      if [[ -z "$sid" ]]; then
        sid=$(uuidgen | tr 'A-Z' 'a-z')
        session_flag=(--session-id "$sid")
        echo "session id: $sid" | tee -a "$logfile" >> "$session_log"
      fi
      ( PAIR_CONSULT_PEER=1 nohup "${buf[@]}" claude -p \
          --dangerously-skip-permissions \
          --effort "$effort" \
          "${session_flag[@]}" \
          --add-dir "$(pwd)" \
          -- \
          "$prompt" </dev/null 2>&1 \
        | tee -a "$logfile" >> "$session_log" ) &
      ;;
  esac
  echo $! > .consult/peer.pid
  disown 2>/dev/null

  local shown="$b"
  [[ "$b" == codex ]] && shown="$b $codex_model"
  echo "consult_handoff: round $round ($kind) -> $shown, effort $effort, $how. Log: $logfile"
  echo "consult_handoff: NEXT: consult_wait (in Claude Code: Bash with run_in_background=true, then end your turn)."
}

# Exit codes: 0 B's round landed, your turn. 2 timed out, B still running: run consult_wait again.
#             3 B exited without writing its round: read the log tail, then consult_handoff again.
consult_wait() {
  _consult_guard consult_wait || return
  local interval=5 timeout=540
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --interval) interval="$2"; shift 2 ;;
      --timeout)  timeout="$2";  shift 2 ;;
      *) echo "consult_wait: usage: consult_wait [--interval s] [--timeout s]" >&2; return 2 ;;
    esac
  done

  local a b round cur
  a=$(_consult_get A); b=$(_consult_get B); round=$(_consult_get ROUND)
  cur=$(_consult_get STATUS)
  if [[ "$cur" != "WAITING: $b" ]]; then
    echo "consult_wait: STATUS is '$cur'; nothing to wait for."
    return 0
  fi
  if [[ ! -f .consult/peer.pid ]]; then
    echo "consult_wait: no reviewer was started for round $round. Run consult_handoff first." >&2
    return 2
  fi

  local elapsed=0
  while :; do
    cur=$(_consult_get STATUS)
    if [[ "$cur" != "WAITING: $b" ]]; then
      echo "consult_wait: STATUS changed to '$cur' after ${elapsed}s."
      return 0
    fi
    if ! _consult_peer_alive; then
      if [[ -s ".consult/R${round}.md" ]]; then
        _consult_set ROUND "$((round + 1))"
        _consult_set STATUS "WAITING: $a"
        echo "consult_wait: $b finished round $round after ${elapsed}s. Round $((round + 1)) is yours. Read .consult/R${round}.md."
        consult_digest "$round"
        return 0
      fi
      echo "consult_wait: $b exited without writing .consult/R${round}.md. Tail of .consult/round-${round}-${b}.log:" >&2
      tail -15 ".consult/round-${round}-${b}.log" >&2
      echo "consult_wait: fix the cause, then consult_handoff again (add --fresh if the resumed session is the problem)." >&2
      return 3
    fi
    if (( elapsed >= timeout )); then
      echo "consult_wait: $b is still working on round $round after ${timeout}s. Run consult_wait again." >&2
      return 2
    fi
    sleep "$interval"
    elapsed=$((elapsed + interval))
  done
}

consult_close() {
  _consult_guard consult_close || return
  local rounds cur
  rounds=$(_consult_get ROUNDS); cur=$(_consult_get STATUS)
  if [[ "$cur" != "WAITING: $(_consult_get A)" ]]; then
    echo "consult_close: STATUS is '$cur'; only the orchestrator's own turn can close the session." >&2
    return 5
  fi
  if [[ ! -s ".consult/R${rounds}.md" ]]; then
    echo "consult_close: write the synthesis to .consult/R${rounds}.md first (always the last round number, even on an early exit)." >&2
    return 5
  fi
  _consult_set ROUND "$rounds"
  _consult_set STATUS "AWAITING_USER"
  echo "consult_close: STATUS: AWAITING_USER. Present .consult/R${rounds}.md to the user and stop."
}

# ---------- human ----------

consult_status() {
  _consult_guard consult_status || return
  grep -E '^(STATUS|ROUND|ROUNDS|A|B|EFFORT):' .consult/STATE.md
  if _consult_peer_alive; then echo "reviewer: running (pid $(cat .consult/peer.pid))"; else echo "reviewer: not running"; fi
  if [[ -f .consult/USER_NOTES.md ]]; then
    echo "--- user notes ---"
    grep -E '^(## N|\*\*Status)' .consult/USER_NOTES.md
  fi
  if [[ -s .consult/session.log ]]; then
    echo "--- last 20 lines of session.log ---"
    tail -20 .consult/session.log
  fi
}

consult_watch() {
  _consult_guard consult_watch || return
  touch .consult/session.log
  tail -F .consult/session.log
}

# A steer for whichever agent acts next. From inside Claude Code, just tell the orchestrator.
consult_inject() {
  _consult_guard consult_inject || return
  local msg="$*" notes=".consult/USER_NOTES.md"
  if [[ -z "$msg" ]]; then
    echo "consult_inject: usage: consult_inject \"<note for the agents>\"" >&2
    return 2
  fi
  [[ -f "$notes" ]] || echo "# User notes" > "$notes"
  local n
  n=$(( $(grep -c '^## N' "$notes") + 1 ))
  {
    echo
    echo "## N${n} ($(date '+%Y-%m-%d %H:%M:%S'), during round $(_consult_get ROUND))"
    echo "$msg"
    echo "**Status:** unaddressed"
  } >> "$notes"
  echo "consult_inject: added N${n}. The next agent to act answers it; A marks it addressed."
}

# Stops this session's reviewer only. Never pkill/killall by name: that kills the user's own CLI.
consult_takeover() {
  _consult_guard consult_takeover || return
  if ! _consult_peer_alive; then
    echo "consult_takeover: no reviewer running; nothing to take over."
    return 0
  fi
  local pid
  pid=$(cat .consult/peer.pid)
  pkill -P "$pid" 2>/dev/null
  kill "$pid" 2>/dev/null
  _consult_set STATUS "BLOCKED: human-takeover"
  echo "consult_takeover: stopped the reviewer (pid $pid). STATUS: BLOCKED: human-takeover."
  echo "consult_takeover: work directly, then consult_resume to rerun B's round."
}

consult_resume() {
  _consult_guard consult_resume || return
  _consult_set STATUS "WAITING: $(_consult_get B)"
  consult_handoff "$@"
}

# ---------- digest ----------

# consult_digest <N>: terse summary of .consult/R<N>.md for chat. Parses the headings in peer.md
# and file-formats.md, so a template heading change needs a matching change here.
consult_digest() {
  local n="$1"
  if [[ -z "$n" || ! "$n" =~ ^[1-9][0-9]*$ ]]; then
    echo "consult_digest: usage: consult_digest <round-number>" >&2
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

  # Agreements: bullets under "## Where A is right"
  local agreed
  agreed=$(awk '
    /^## Where A is right/ { in_block=1; next }
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

  # Per-critique verdicts: A's response (`**Verdict:**`) and B's re-review (`**B's verdict:**`).
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

  # Overall verdict (re-review)
  local overall
  overall=$(awk '
    /^## Overall verdict/ { in_v=1; next }
    /^## / && in_v { in_v=0 }
    in_v && NF > 0 { print; exit }
  ' "$f" 2>/dev/null || true)
  if [[ -n "$overall" ]]; then
    echo "overall verdict: $overall"
  fi

  unset -f _trunc
}
