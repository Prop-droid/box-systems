#!/usr/bin/env python3
"""PreToolUse hook: no direct writes to the eJam Company Brain (Tomas 2026-11-12).

One write path: edit ~/brain/wiki, then run_brain_push.sh (gate.py applies).
A direct brain write from a session skips the gate and makes entries that have
no wiki source, so it is blocked by default.

Unlock, ONLY after Tomas says "push to brain" for that content in the
conversation:  touch ~/.cache/brain-direct-write.ok   (valid 30 minutes)
The weekly push is not affected: it does not go through this hook.
"""
import json, re, sys, time
from pathlib import Path

WRITE = re.compile(r"^mcp__brain__(create_entry|update_entry|archive_entry|"
                   r"create_folder|move_folder|delete_folder|rename_folder)$")
FLAG = Path.home() / ".cache/brain-direct-write.ok"
TTL_S = 30 * 60


def main():
    try:
        tool = json.load(sys.stdin).get("tool_name", "")
    except (ValueError, AttributeError):
        return 0
    if not WRITE.match(tool):
        return 0
    try:
        if time.time() - FLAG.stat().st_mtime < TTL_S:
            return 0
    except OSError:
        pass
    print("BRAIN WRITE RULE: direct writes to the company brain are blocked. "
          "Write the page in ~/brain/wiki, then run "
          "`bash ~/systems/brain-push/run_brain_push.sh` (the gate applies there). "
          "A direct write is allowed only when Tomas said \"push to brain\" for this "
          "content in this conversation: then `touch ~/.cache/brain-direct-write.ok` "
          "(valid 30 min) and retry. Do not unlock on your own; ask him.",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
