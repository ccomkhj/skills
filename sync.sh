#!/usr/bin/env bash
# Symlink every skill in this repo into ~/.claude/skills (Claude Code) and
# ~/.agents/skills (Codex, Gemini CLI, ...), one symlink per skill.
# Idempotent: correct links are left alone, stale links are re-pointed,
# real files/dirs are never clobbered (warned and skipped).
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGETS=("$HOME/.claude/skills" "$HOME/.agents/skills")

# Every dir holding a SKILL.md: top-level skills (./<name>/SKILL.md) and
# plugin-bundled skills (./<plugin>/skills/<name>/SKILL.md).
skill_dirs() {
  find "$REPO_DIR" -mindepth 2 -maxdepth 4 -name SKILL.md \
    -not -path "*/node_modules/*" -not -path "*/.git/*" \
    | xargs -n1 dirname | sort -u
}

link() { # $1=skill dir, $2=target parent
  local src="$1" name dest
  name="$(basename "$1")"
  dest="$2/$name"
  if [[ -L "$dest" ]]; then
    if [[ "$(readlink "$dest")" == "$src" ]]; then
      echo "  ok      $dest"
    else
      ln -sfn "$src" "$dest"
      echo "  updated $dest -> $src (was $(readlink "$dest" 2>/dev/null || echo '?'))"
    fi
  elif [[ -e "$dest" ]]; then
    echo "  SKIP    $dest exists and is not a symlink — resolve by hand" >&2
  else
    ln -s "$src" "$dest"
    echo "  linked  $dest -> $src"
  fi
}

for target in "${TARGETS[@]}"; do
  mkdir -p "$target"
  echo "$target"
  while IFS= read -r dir; do
    link "$dir" "$target"
  done < <(skill_dirs)
done
