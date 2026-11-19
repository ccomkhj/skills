#!/usr/bin/env bash
# PostToolUse hook: after `gh pr create` prints exactly one PR URL, start run.sh in the background.
# Never blocks or fails the author's session: every path exits 0; anything worth knowing goes to systemMessage.
#
# Install (~/.claude/settings.json → hooks.PostToolUse):
#   { "matcher": "Bash",
#     "hooks": [{ "type": "command", "timeout": 10,
#                 "command": "$HOME/.claude/skills/pr-review/scripts/on-pr-created.sh" }] }

in=$(cat)
cmd=$(jq -r '.tool_input.command // ""' <<<"$in")
[[ $cmd == *"gh pr create"* ]] || exit 0

say() { jq -n --arg m "pr-review: $1" '{systemMessage: $m}'; exit 0; }
run="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/run.sh"
log="${PR_REVIEW_HOME:-$HOME/.cache/pr-review}/launch.log"

# One unambiguous PR, or none: guessing which of several URLs was just created could review the wrong PR.
urls=$(jq -r '.tool_response.stdout // ""' <<<"$in" \
  | grep -Eo 'https://[^[:space:]/]+/[^[:space:]/]+/[^[:space:]/]+/pull/[0-9]+' | sort -u)
n=$(grep -c . <<<"$urls")
(( n == 1 )) || say "found $n PR URLs in the output of \`gh pr create\`, so no review started. Start one by hand: $run <url>"

mkdir -p "$(dirname "$log")"
(nohup "$run" "$urls" </dev/null >>"$log" 2>&1 &)
say "reviewing $urls in a fresh background session (waits for CI first); the verdict lands as a PR comment. Log: $log"
