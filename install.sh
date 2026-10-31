#!/usr/bin/env sh
# Install game-art-workflow as a Claude Code user skill.
#   curl -fsSL https://raw.githubusercontent.com/mnmnsyf/game-art-workflow/main/install.sh | sh
# Re-running updates an existing install in place.
set -eu

REPO="https://github.com/mnmnsyf/game-art-workflow.git"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}/game-art-workflow"

command -v git >/dev/null 2>&1 || { echo "git is required" >&2; exit 1; }
mkdir -p "$(dirname "$DEST")"

if [ -d "$DEST/.git" ]; then
  git -C "$DEST" pull --ff-only
elif [ -e "$DEST" ]; then
  echo "$DEST exists and is not a git checkout; move it away and re-run" >&2
  exit 1
else
  git clone --depth 1 "$REPO" "$DEST"
fi

if command -v python3 >/dev/null 2>&1; then
  python3 -m pip install --user --quiet -r "$DEST/requirements.txt" || echo "note: install Pillow yourself for the image check scripts"
fi

echo "Installed to $DEST"
echo "Start a new Claude Code session and ask: \"Make a village house for my Godot scene\""
