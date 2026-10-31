#!/usr/bin/env bash
# Linker: creates Harness Links from the Canonical Layout. Installed by aisetup at .agents/link.sh.
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root"

block_start='# >>> aisetup Harness Links (managed by .agents/link.sh)'
block_end='# <<< aisetup Harness Links'
links=()

# Creates the Harness Link `$1` pointing at `$2` (relative to the link's folder),
# when the Canonical Layout path `$3` exists.
link() {
  local link_path="$1" target="$2" source_path="$3"
  [[ -e "$source_path" ]] || return 0
  mkdir -p "$(dirname "$link_path")"
  if [[ -L "$link_path" ]]; then
    rm "$link_path"
  elif [[ -e "$link_path" ]]; then
    echo "Skipped $link_path: it already exists and is not a Harness Link." >&2
    return 0
  fi
  ln -s "$target" "$link_path"
  links+=("$link_path")
}

# Replaces the managed block in .gitignore with the current Harness Links.
write_gitignore() {
  local kept=''
  if [[ -f .gitignore ]]; then
    kept="$(awk -v start="$block_start" -v end="$block_end" '
      $0 == start { skipping = 1; next }
      $0 == end { skipping = 0; next }
      !skipping { print }
    ' .gitignore)"
  elif [[ ${#links[@]} -eq 0 ]]; then
    return 0
  fi
  {
    if [[ -n "$kept" ]]; then printf '%s\n' "$kept"; fi
    if [[ ${#links[@]} -gt 0 ]]; then
      if [[ -n "$kept" ]]; then printf '\n'; fi
      printf '%s\n' "$block_start"
      printf '/%s\n' "${links[@]}"
      printf '%s\n' "$block_end"
    fi
  } > .gitignore
}

# Claude Code
link .claude/skills ../.agents/skills .agents/skills
link .claude/agents ../.agents/agents .agents/agents

write_gitignore
