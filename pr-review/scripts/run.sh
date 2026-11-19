#!/usr/bin/env bash
# One supervised pr-review run per PR head commit.
#
#   run.sh [--force] <PR URL>      from any directory: each run reviews its own clone, never yours
#
# Pre:  gh is authenticated and can read the PR's repo.
# Post: exit 0 = done (receipt comment found on the PR) or skipped (already running/done);
#       exit 1 = failed: state=failed, run dir and checkout kept for inspection, next call retries.
# Run dir: $PR_REVIEW_HOME (default ~/.cache/pr-review)/<host>_<owner>_<repo>_<N>_<head12>/
#          state, proc, session, pin.json, claude.log, src/ (removed when done)
set -euo pipefail

force=0
[[ ${1:-} == --force ]] && { force=1; shift; }
url=${1:?usage: run.sh [--force] <PR URL>}

ROOT=${PR_REVIEW_HOME:-$HOME/.cache/pr-review}
CI_TIMEOUT=${PR_REVIEW_CI_TIMEOUT:-1800}   # seconds to wait for pending CI before reviewing anyway
CI_GRACE=${PR_REVIEW_CI_GRACE:-20}         # seconds for CI to register its checks on a fresh PR

dir="" claimed=0
log() { echo "run.sh $(date '+%F %T') [${url}]: $*"; }
die() { log "FAILED: $*"; exit 1; }
trap 'rc=$?; if (( claimed )) && (( rc != 0 )); then echo failed > "$dir/state"; fi' EXIT

# Canonical identity.
read -r pr_url number base_ref < <(gh pr view "$url" --json url,number,baseRefName -q '"\(.url) \(.number) \(.baseRefName)"') \
  || die "gh can't resolve the PR"
slug=$(sed -E 's#^https://([^/]+)/([^/]+)/([^/]+)/pull/[0-9]+$#\1/\2/\3#' <<<"$pr_url" | tr 'A-Z' 'a-z')

# Review finished CI, not a snapshot of it. The verdict's own status is not CI.
sleep "$CI_GRACE"
deadline=$((SECONDS + CI_TIMEOUT))
while (( SECONDS < deadline )); do
  pending=$(gh pr checks "$pr_url" --json name,bucket \
    -q '[.[] | select(.bucket == "pending" and .name != "pr-classify")] | length' 2>/dev/null || echo 0)
  (( ${pending:-0} == 0 )) && break
  sleep 30
done

read -r head base < <(gh pr view "$pr_url" --json headRefOid,baseRefOid -q '"\(.headRefOid) \(.baseRefOid)"')
dir="$ROOT/${slug//\//_}_${number}_${head:0:12}"
src="$dir/src"
url=$pr_url

# Claim the run. mkdir is atomic; an existing dir is reclaimed only if its run is over or its process is gone.
proc_id() { ps -o lstart= -p "$1" 2>/dev/null | tr -s ' '; }
mkdir -p "$ROOT"
if ! mkdir "$dir" 2>/dev/null; then
  state=$(cat "$dir/state" 2>/dev/null || echo unknown)
  opid=$(sed -n 1p "$dir/proc" 2>/dev/null || true)
  ostart=$(sed -n 2p "$dir/proc" 2>/dev/null || true)
  # Same pid AND same start time: the original process is still alive, not a recycled pid.
  if [[ $state == running && -n $opid && "$(proc_id "$opid")" == "$ostart" ]]; then
    log "already running (pid $opid): $dir"; exit 0
  fi
  if [[ $state == "done" && $force == 0 ]]; then
    log "already reviewed: $dir (rerun with --force)"; exit 0
  fi
  log "reclaiming ($state): $dir"
  rm -rf "$src"
fi
claimed=1
echo running > "$dir/state"
printf '%s\n%s\n' "$$" "$(proc_id $$)" > "$dir/proc"

# Pin: the exact head in the run's own clone, so neither a push mid-review nor the author's
# working tree can change what is judged. Blobless: full history (merge-base works), contents on demand.
gh repo clone "${pr_url%/pull/*}" "$src" -- -q --filter=blob:none --no-checkout || die "clone failed"
git -C "$src" fetch -q origin "pull/$number/head" "refs/heads/$base_ref" || die "fetch failed"
git -C "$src" cat-file -e "$head^{commit}" || die "head $head not fetched"
git -C "$src" cat-file -e "$base^{commit}" || die "base $base not fetched"
git -C "$src" checkout -q --detach "$head"
[[ $(git -C "$src" rev-parse HEAD) == "$head" ]] || die "checkout is not at $head"
jq -n --arg url "$pr_url" --arg repo "$slug" --argjson number "$number" --arg base_ref "$base_ref" \
  --arg base "$base" --arg head "$head" --arg checkout "$src" \
  '{url:$url, repo:$repo, number:$number, base_ref:$base_ref, base:$base, head:$head, checkout:$checkout}' > "$dir/pin.json"

# Fresh headless session. Report-only is enforced here, not just asked for in the skill.
sid=$(uuidgen | tr 'A-Z' 'a-z')
echo "$sid" > "$dir/session"
log "reviewing $head in $dir (session $sid; open with: claude --resume $sid)"
if (cd "$src" && claude -p \
      --session-id "$sid" \
      --permission-mode auto \
      --add-dir "$dir" \
      --allowedTools "Bash(gh pr view *)" "Bash(gh pr diff *)" "Bash(gh pr checks *)" "Bash(gh pr comment *)" \
                     "Bash(gh issue view *)" "Bash(gh api *)" "Bash(git *)" \
      --disallowedTools "Bash(gh pr merge *)" "Bash(gh pr create *)" "Bash(gh pr close *)" "Bash(gh pr edit *)" \
                        "Bash(gh pr review *)" "Bash(git push *)" \
      -- "/pr-review $pr_url $dir" </dev/null >"$dir/claude.log" 2>&1); then
  rc=0
else
  rc=$?
fi
(( rc == 0 )) || die "claude exited $rc (see $dir/claude.log)"

# Done means the receipt is on GitHub, not that the model says so.
gh pr view "$pr_url" --json comments -q '.comments[].body' | grep -qF "<!-- pr-review:$head -->" \
  || die "no pr-review comment for $head on the PR (see $dir/claude.log)"
echo "done" > "$dir/state"
rm -rf "$src"
log "done: $(cat "$dir/state") — $pr_url"
