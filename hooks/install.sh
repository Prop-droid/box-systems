#!/usr/bin/env bash
# install.sh — install the shared pre-commit hook into estate git repos (task 55).
#
# Symlinks <repo>/.git/hooks/pre-commit -> ~/systems/hooks/pre-commit so every
# repo shares one source of truth. Any pre-existing NON-symlink hook is backed
# up to pre-commit.pre-hooks.bak first. Idempotent: re-running is a no-op once
# the symlink is in place.
#
# Usage:
#   bash ~/systems/hooks/install.sh            # install into the default set
#   bash ~/systems/hooks/install.sh --check    # report status, change nothing
#   bash ~/systems/hooks/install.sh /path/repo # install into specific repo(s)
set -uo pipefail

HOOK_SRC="$HOME/systems/hooks/pre-commit"
[ -f "$HOOK_SRC" ] || { echo "install: missing $HOOK_SRC" >&2; exit 1; }

check=0; targets=()
for a in "$@"; do
  case "$a" in
    --check) check=1 ;;
    *) targets+=("$a") ;;
  esac
done

# Default target set: ~/systems + every git repo directly under ~/personal.
if [ "${#targets[@]}" -eq 0 ]; then
  targets+=("$HOME/systems")
  for d in "$HOME"/personal/*/; do
    [ -d "$d/.git" ] && targets+=("${d%/}")
  done
fi

rc=0
for repo in "${targets[@]}"; do
  if [ ! -d "$repo/.git" ]; then
    echo "skip  $repo (not a git repo)"; continue
  fi
  dest="$repo/.git/hooks/pre-commit"
  if [ "$check" -eq 1 ]; then
    if [ -L "$dest" ] && [ "$(readlink -f "$dest")" = "$(readlink -f "$HOOK_SRC")" ]; then
      echo "ok    $repo -> shared hook"
    elif [ -e "$dest" ]; then
      echo "OTHER $repo has a different pre-commit hook"; rc=1
    else
      echo "MISS  $repo has no pre-commit hook"; rc=1
    fi
    continue
  fi
  mkdir -p "$repo/.git/hooks"
  if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    mv "$dest" "$dest.pre-hooks.bak"
    echo "backed up existing hook -> $dest.pre-hooks.bak"
  fi
  ln -sf "$HOOK_SRC" "$dest"
  echo "installed $repo -> shared pre-commit hook"
done
exit "$rc"
