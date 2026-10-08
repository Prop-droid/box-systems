#!/usr/bin/env python3
"""Work/personal Google-account firewall.

Two entry points, picked by how it's invoked:
  gws / gws-work / gws-personal   -> wrapper around the real gws binary. Binds the
      profile's config dir (creds live ONLY there, so bare /usr/bin/gws has none) and
      refuses writes whose args carry the other side's markers.
  guard.py hook                   -> Claude Code PreToolUse hook. Blocks MCP writes that
      cross sides (company brain / ClickUp / Cruva / Created.AI = work; Drive MCP =
      personal) and Bash attempts to bypass the wrapper.
Rules: rules.json next to this file.
"""
import json, os, re, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RULES = json.loads((HERE / "rules.json").read_text())
GWS_BIN = "/usr/lib/node_modules/@googleworkspace/cli/bin/gws"
READ_METHODS = {"get", "list", "export", "batchGet", "getByDataFilter", "search", "query"}
PASSTHROUGH = {"auth", "schema", "help", "--help", "-h", "--version", "-V"}


def markers(side):
    return [re.compile(p) for p in RULES[side]["markers"]]


def crossing(text, dest):
    """Markers of the OTHER side found in text headed for `dest`."""
    other = "personal" if dest == "work" else "work"
    return sorted({m.group(0) for p in markers(other) for m in [p.search(text)] if m})


def block_msg(dest, hits):
    acct = RULES[dest]["account"]
    other = "personal" if dest == "work" else "work"
    return (f"ACCOUNT FIREWALL: blocked write to {dest} ({acct}) - content looks {other} "
            f"({', '.join(hits)}). Rule: Shameless + creative strategy -> tomas.s@ejam.com, "
            f"everything else -> propeidzas@gmail.com. Use the {other} side "
            f"({'gws-personal / Drive MCP' if other == 'personal' else 'gws-work'}). "
            f"If this is a misfire, stop and ask Tomas; don't route around it.")


def run_gws(dest):
    args = sys.argv[1:]
    pos = []
    for a in args:
        if a.startswith("-"):
            break
        pos.append(a)
    is_read = bool(pos) and (pos[0] in PASSTHROUGH or pos[-1] in READ_METHODS)
    if not pos and args and args[0] in PASSTHROUGH:
        is_read = True
    if not is_read:
        hits = crossing(" ".join(args), dest)
        if hits:
            print(block_msg(dest, hits), file=sys.stderr)
            sys.exit(3)
    env = dict(os.environ, GOOGLE_WORKSPACE_CLI_CONFIG_DIR=os.path.expanduser(RULES[dest]["config_dir"]))
    rc = subprocess.call([GWS_BIN, *args], env=env)
    # A profile must only ever hold its own account: undo a login into the wrong one.
    if pos[:2] == ["auth", "login"] and rc == 0:
        st = subprocess.run([GWS_BIN, "auth", "status"], env=env, capture_output=True, text=True).stdout
        user = (json.loads(st[st.find("{"):]) if "{" in st else {}).get("user")
        if user != RULES[dest]["account"]:
            subprocess.call([GWS_BIN, "auth", "logout"], env=env)
            print(f"ACCOUNT FIREWALL: {dest} profile must be {RULES[dest]['account']}, got {user}; logged out.",
                  file=sys.stderr)
            sys.exit(4)
    sys.exit(rc)


WORK_MCP = re.compile(r"^mcp__(brain|claude_ai_ClickUp|claude_ai_Shameless_Snacks_Cruva|created-ai)__")
PERSONAL_MCP = re.compile(r"^mcp__claude_ai_Google_Drive__(create_file|update_file|copy_file|share_file)$")
WRITE_VERB = re.compile(r"create|update|add_|send|attach|upload|merge|move|execute|share|copy|comment|"
                        r"rename|tag|record|approve|reject|set_|toggle|import|save|archive")
# Command-shaped only: plain mentions in docs/memory must pass.
BYPASS = re.compile(r"GOOGLE_WORKSPACE_CLI_(CONFIG_DIR|CREDENTIALS_FILE|TOKEN)[\"']?\]?\s*[=:,]|"
                    r"(?:^|[;&|(]|\bexec|\bsudo|\btimeout\s+\d+)\s*/usr/bin/gws\b|"
                    r"@googleworkspace/cli/bin|\.config/gws[\w.-]*/(credentials|token_cache|\.encryption_key)|"
                    r"\bauth\s+export\b")


def hook():
    ev = json.load(sys.stdin)
    tool, inp = ev.get("tool_name", ""), ev.get("tool_input", {}) or {}
    if tool == "Bash":
        if BYPASS.search(inp.get("command", "")):
            print("ACCOUNT FIREWALL: don't touch gws creds/env or the raw binary. Use gws-work "
                  "(Shameless + creative strategy) or gws-personal (everything else).", file=sys.stderr)
            sys.exit(2)
        return
    dest = None
    if WORK_MCP.match(tool) and WRITE_VERB.search(tool.split("__")[-1]):
        dest = "work"
    elif PERSONAL_MCP.match(tool):
        dest = "personal"
    if dest:
        hits = crossing(json.dumps(inp, ensure_ascii=False), dest)
        if hits:
            print(block_msg(dest, hits), file=sys.stderr)
            sys.exit(2)


if __name__ == "__main__":
    if sys.argv[1:2] == ["hook"]:
        hook()
    else:
        run_gws("personal" if Path(sys.argv[0]).name == "gws-personal" else "work")
