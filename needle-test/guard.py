"""Box-safety guards shared by the needle-test runners.

Three protections, born from the 2026-07-23 meltdown (26 needles x full MCP
boot + SessionEnd flush storm = load 155 on a 4-core box):

1. mcp_args() — every headless `claude -p` must pin its MCP config to exactly
   the servers it needs (usually none). NOTE: --strict-mcp-config alone is a
   no-op; without an explicit --mcp-config the CLI still loads all
   ~/.claude.json servers (6 servers, ~2GB, 60s+ boot per needle).
2. wait_for_capacity() — never spawn a claude while the box is already loaded.
3. checkpoint()/load_done() — every answered needle lands in a daily .jsonl
   immediately, so a killed run resumes instead of restarting.
"""

import json
import os
import pathlib
import time

CLAUDE_JSON = pathlib.Path.home() / ".claude.json"
MAX_LOAD = 3.0
LOAD_POLL_SECONDS = 15
LOAD_WAIT_TIMEOUT = 900


def mcp_args(servers=()):
    """CLI args pinning the MCP config to exactly `servers` (none by default)."""
    cfg = {}
    if servers:
        available = json.loads(CLAUDE_JSON.read_text()).get("mcpServers", {})
        missing = [s for s in servers if s not in available]
        if missing:
            raise SystemExit(f"MCP server(s) not in ~/.claude.json: {missing}")
        cfg = {s: available[s] for s in servers}
    return ["--strict-mcp-config", "--mcp-config", json.dumps({"mcpServers": cfg})]


def wait_for_capacity(max_load=MAX_LOAD, timeout=LOAD_WAIT_TIMEOUT):
    """Block until 1-min loadavg is below max_load; abort the run if it never is."""
    deadline = time.time() + timeout
    warned = False
    while (load := os.getloadavg()[0]) > max_load:
        if time.time() > deadline:
            raise SystemExit(
                f"[guard] loadavg {load:.1f} still > {max_load} after {timeout}s; aborting"
            )
        if not warned:
            print(f"[guard] loadavg {load:.1f} > {max_load}; waiting", flush=True)
            warned = True
        time.sleep(LOAD_POLL_SECONDS)


def load_done(jsonl_path):
    """Rows already answered today, keyed by needle id (last write wins)."""
    done = {}
    if jsonl_path.exists():
        for line in jsonl_path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
                done[row["id"]] = row
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    return done


def checkpoint(jsonl_path, row):
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
