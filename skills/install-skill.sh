#!/usr/bin/env bash
# Install the bundled skill into an agent's global skill directory.
#
#   ./skills/install-skill.sh                 # -> ~/.claude/skills
#   ./skills/install-skill.sh /path/to/skills
#   ./skills/install-skill.sh --project       # -> ./.claude/skills
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skill="$here/fischertechnik-ft"

[ -f "$skill/SKILL.md" ] || { echo "skill not found at $skill" >&2; exit 1; }

dest="$1"
if [ "${dest:-}" = "--project" ]; then
  dest="$PWD/.claude/skills"
  shift || true
fi
if [ -z "${dest:-}" ]; then
  dest="$HOME/.claude/skills"
fi

mkdir -p "$dest"
rm -rf "$dest/fischertechnik-ft"
cp -R "$skill" "$dest/fischertechnik-ft"

echo "installed fischertechnik-ft -> $dest/fischertechnik-ft"
ls -1 "$dest/fischertechnik-ft"
