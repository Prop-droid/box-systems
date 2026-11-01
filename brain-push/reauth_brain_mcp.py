#!/usr/bin/env python3
"""Re-authorize the `brain` MCP (eJam Company Brain hub) for box Claude Code, headless.

Why: the hub issues ~90-day access tokens and no refresh_token (its metadata
advertises grant_types=[authorization_code] only). When the token lapses,
brain-push.service fails with HTTP 401 and interactive sessions report the
brain MCP as needing auth. The box has no browser, so this script runs the
OAuth dance by hand (recipe proven 2026-08-19 for the bigquery MCP, memory
reference_headless_mcp_oauth_recipe):

  1. dynamic client registration with a tailnet-only https redirect URI
  2. a localhost callback listener published via `tailscale serve --set-path`
  3. ONE authorize URL for Tomas (ejam Google sign-in, device on Tailscale)
  4. code -> token exchange (PKCE); accessToken + expiresAt written into the
     existing `brain|<hash>` entry of ~/.claude/.credentials.json (backup kept,
     clientId left alone so an interactive /mcp re-auth still works)
  5. cleanup of the serve path + listener, raw MCP tools/list as proof, then
     `systemctl --user reset-failed brain-push && start brain-push`

Usage:
  python3 reauth_brain_mcp.py [--port 8768] [--path /brain-callback] [--timeout 86400] [--no-run]

Run it detached so it outlives the calling session:
  systemd-run --user --unit brain-reauth --collect python3 ~/systems/brain-push/reauth_brain_mcp.py
The authorize URL is printed to stdout (journalctl --user -u brain-reauth) and to
~/systems/brain-push/reauth-url.txt (deleted on exit). Completion or failure is
announced through lib/tg-notify.sh.
"""
import argparse, base64, hashlib, json, os, secrets, signal, subprocess, sys, threading, time
import urllib.error, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

AUTH = "https://adk-backend-7643849657.us-central1.run.app"
RESOURCE = AUTH + "/mcp"
CREDS = Path.home() / ".claude/.credentials.json"
HERE = Path(__file__).resolve().parent
URL_FILE = HERE / "reauth-url.txt"
NOTIFY = Path.home() / "systems/lib/tg-notify.sh"
DEFAULT_TTL_S = 90 * 24 * 3600


def log(msg):
    print(f"[{time.strftime('%F %T')}] {msg}", flush=True)


def notify(title, body, prio="default"):
    if NOTIFY.exists():
        subprocess.run(["bash", str(NOTIFY), title, body, prio], check=False)


def http_json(url, data=None, form=False):
    h = {"Accept": "application/json"}
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            h["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            h["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {"_error_body": e.read().decode(errors="replace")[:500]}


def tailnet_fqdn():
    out = subprocess.check_output(["tailscale", "status", "--json"], text=True)
    return json.loads(out)["Self"]["DNSName"].rstrip(".")


class Catcher(BaseHTTPRequestHandler):
    got = {}
    event = threading.Event()

    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if "code" in q:
            Catcher.got = {k: v[0] for k, v in q.items()}
            Catcher.event.set()
            msg = b"brain MCP re-auth: code received. You can close this tab."
        else:
            msg = b"waiting for the OAuth redirect (no code in this request)"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(msg)))
        self.end_headers()
        self.wfile.write(msg)

    def log_message(self, *a):
        pass


def serve_path(path, port, on):
    if on:
        subprocess.run(["tailscale", "serve", "--bg", "--set-path", path, f"http://127.0.0.1:{port}"],
                       check=True, capture_output=True, text=True)
    else:
        subprocess.run(["tailscale", "serve", "--https=443", "--set-path", path, "off"],
                       check=False, capture_output=True, text=True)


def mcp_tools_count(token):
    h = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream",
         "Authorization": f"Bearer {token}"}

    def post(payload, sid=None):
        hh = dict(h)
        if sid:
            hh["Mcp-Session-Id"] = sid
        req = urllib.request.Request(RESOURCE, json.dumps(payload).encode(), hh)
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.headers.get("Mcp-Session-Id"), r.read().decode()

    sid, _ = post({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                   "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                              "clientInfo": {"name": "brain-reauth", "version": "1"}}})
    post({"jsonrpc": "2.0", "method": "notifications/initialized"}, sid)
    _, body = post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, sid)
    for line in body.splitlines():
        if line.startswith("data:"):
            return len(json.loads(line[5:]).get("result", {}).get("tools", []))
    return len(json.loads(body).get("result", {}).get("tools", []))


def inject(token, expires_at_ms):
    d = json.loads(CREDS.read_text())
    keys = [k for k, v in d.get("mcpOAuth", {}).items()
            if v.get("serverName") == "brain" or k.startswith("brain|")]
    if not keys:
        sys.exit("no brain|<hash> entry in .credentials.json; run `claude mcp list` once so Claude Code "
                 "scaffolds it, then rerun")
    bak = CREDS.with_name(f".credentials.json.bak-{time.strftime('%Y%m%d-%H%M%S')}")
    bak.write_bytes(CREDS.read_bytes())
    os.chmod(bak, 0o600)
    for k in keys:
        d["mcpOAuth"][k]["accessToken"] = token
        d["mcpOAuth"][k]["expiresAt"] = expires_at_ms
    tmp = CREDS.with_name(".credentials.json.tmp")
    tmp.write_text(json.dumps(d, indent=2))
    os.chmod(tmp, 0o600)
    os.replace(tmp, CREDS)
    return keys, bak


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8768)
    ap.add_argument("--path", default="/brain-callback")
    ap.add_argument("--timeout", type=int, default=86400, help="seconds to wait for the callback")
    ap.add_argument("--no-run", action="store_true", help="do not start brain-push.service afterwards")
    a = ap.parse_args()

    st, meta = http_json(AUTH + "/.well-known/oauth-authorization-server")
    if st != 200 or "authorization_endpoint" not in meta:
        sys.exit(f"metadata fetch failed: {st} {meta}")
    redirect = f"https://{tailnet_fqdn()}{a.path}"

    st, reg = http_json(meta["registration_endpoint"], {
        "client_name": "box-brain-reauth", "redirect_uris": [redirect],
        "grant_types": ["authorization_code"], "response_types": ["code"],
        "token_endpoint_auth_method": "none"})
    if st not in (200, 201) or "client_id" not in reg:
        sys.exit(f"client registration failed: {st} {reg}")
    client_id = reg["client_id"]

    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)

    srv = HTTPServer(("127.0.0.1", a.port), Catcher)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    serve_path(a.path, a.port, True)
    url = meta["authorization_endpoint"] + "?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": client_id, "redirect_uri": redirect,
        "code_challenge": challenge, "code_challenge_method": "S256", "state": state,
        "resource": RESOURCE})
    URL_FILE.write_text(url + "\n")
    os.chmod(URL_FILE, 0o600)
    log(f"AUTHORIZE URL (ejam Google sign-in, device on Tailscale; callback {redirect}):\n{url}")

    n = 0
    expires_at = 0
    # `systemctl --user stop brain-reauth` sends SIGTERM; turn it into SystemExit so the
    # finally block below still removes the serve path and the listener.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit("terminated"))
    try:
        if not Catcher.event.wait(a.timeout):
            notify("brain re-auth expired", f"authorize URL not used within {a.timeout // 3600}h; "
                   "rerun ~/systems/brain-push/reauth_brain_mcp.py")
            sys.exit("timed out waiting for the OAuth callback")
        got = Catcher.got
        if got.get("state") != state:
            sys.exit("state mismatch on the callback; aborting")
        st, tok = http_json(meta["token_endpoint"], {
            "grant_type": "authorization_code", "code": got["code"], "redirect_uri": redirect,
            "client_id": client_id, "code_verifier": verifier, "resource": RESOURCE}, form=True)
        if st != 200 or "access_token" not in tok:
            sys.exit(f"token exchange failed: {st} {tok}")
        ttl = int(tok.get("expires_in") or DEFAULT_TTL_S)
        expires_at = int(time.time() * 1000) + ttl * 1000
        n = mcp_tools_count(tok["access_token"])
        keys, bak = inject(tok["access_token"], expires_at)
        log(f"token written into {keys} (backup {bak.name}); brain tools/list = {n} tools; "
            f"valid to {time.strftime('%F', time.localtime(expires_at / 1000))}")
    finally:
        serve_path(a.path, a.port, False)
        srv.shutdown()
        URL_FILE.unlink(missing_ok=True)

    valid_to = time.strftime('%F', time.localtime(expires_at / 1000))
    if a.no_run:
        notify("brain MCP re-auth done", f"{n} tools visible; token valid to {valid_to}")
        return
    subprocess.run(["systemctl", "--user", "reset-failed", "brain-push.service"], check=False)
    subprocess.run(["systemctl", "--user", "start", "brain-push.service"], check=False,
                   capture_output=True, text=True)
    result = subprocess.run(["systemctl", "--user", "show", "-p", "Result", "--value", "brain-push.service"],
                            capture_output=True, text=True).stdout.strip()
    last = subprocess.run(["bash", "-c", "grep -oE 'pass 1: [0-9]+ ok, [0-9]+ failed' "
                           "~/systems/brain-push/last_run.log | tail -1"],
                          capture_output=True, text=True).stdout.strip()
    log(f"brain-push.service result={result} {last}")
    notify("brain MCP re-auth done" if result == "success" else "brain re-auth: push still failing",
           f"brain MCP: {n} tools, token valid to {valid_to}. brain-push result={result} {last}",
           "default" if result == "success" else "high")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        if e.code not in (0, None):
            notify("brain re-auth FAILED", str(e.code)[:300], "high")
        raise
    except Exception as e:
        notify("brain re-auth FAILED", f"{type(e).__name__}: {e}"[:300], "high")
        raise
