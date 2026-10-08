#!/usr/bin/env python3
"""Hook regression cases. Run: python3 test_guard.py (exit 1 on any mismatch)."""
import json, subprocess, sys
from pathlib import Path

G = Path(__file__).resolve().parent / "guard.py"
CASES = [
    ("Bash", {"command": "GOOGLE_WORKSPACE_CLI_CONFIG_DIR=~/.config/gws-work gws drive files list"}, 2),
    ("Bash", {"command": "/usr/bin/gws drive files list"}, 2),
    ("Bash", {"command": "ls; /usr/bin/gws auth status"}, 2),
    ("Bash", {"command": "cat ~/.config/gws-personal/credentials.json"}, 2),
    ("Bash", {"command": "gws-work auth export"}, 2),
    ("Bash", {"command": "echo 'note: `/usr/bin/gws` has no creds; see ~/.config/gws-work' >> notes.md"}, 0),
    ("Bash", {"command": "gws-work drive files list"}, 0),
    ("mcp__claude_ai_ClickUp__clickup_create_task", {"name": "Call grandma care homes"}, 2),
    ("mcp__claude_ai_ClickUp__clickup_create_task", {"name": "SHA_2026_S42 hook test"}, 0),
    ("mcp__claude_ai_ClickUp__clickup_get_task", {"task_id": "grandma"}, 0),
    ("mcp__brain__create_entry", {"body": "share with propeidzas@gmail.com"}, 2),
    ("mcp__claude_ai_Google_Drive__create_file", {"title": "Shameless LP copy"}, 2),
    ("mcp__claude_ai_Google_Drive__create_file", {"title": "Lake house shortlist"}, 0),
    ("mcp__claude_ai_Google_Drive__create_file", {"title": "sha256 sums"}, 0),
]
bad = 0
for tool, inp, want in CASES:
    rc = subprocess.run([sys.executable, G, "hook"], input=json.dumps({"tool_name": tool, "tool_input": inp}),
                        capture_output=True, text=True).returncode
    if rc != want:
        bad += 1
        print(f"FAIL {tool} {inp} -> {rc}, want {want}")
print(f"{len(CASES) - bad}/{len(CASES)} pass")
sys.exit(1 if bad else 0)
