#!/usr/bin/env python3
"""Qwen OAuth device-code login for Hermes' built-in `qwen-oauth` provider.

Writes ~/.qwen/oauth_creds.json (the Qwen Code CLI format Hermes reads) and
smoke-tests the portal API. Status lands in ~/systems/qwen-oauth/status.json.
Run detached:  setsid nohup python3 device_login.py > last_login.log 2>&1 &
"""
import base64, hashlib, json, os, platform, secrets, sys, time
import urllib.error, urllib.parse, urllib.request

BASE = "https://chat.qwen.ai"
CLIENT_ID = "f0304373b74a44d2b584a3fb70ca9e56"
SCOPE = "openid profile email model.completion"
GRANT = "urn:ietf:params:oauth:grant-type:device_code"
UA = f"QwenCode/0.14.1 ({platform.system().lower()}; {platform.machine()})"
CREDS = os.path.expanduser("~/.qwen/oauth_creds.json")
HERE = os.path.dirname(os.path.abspath(__file__))
STATUS = os.path.join(HERE, "status.json")
CANDIDATE_MODELS = ["qwen3-coder-plus", "coder-model", "qwen3.5-plus", "qwen3-coder-flash", "vision-model"]


def request(url, data=None, headers=None, json_body=None, method=None):
    if json_body is not None:
        body = json.dumps(json_body).encode()
        ctype = "application/json"
    elif data is not None:
        body = urllib.parse.urlencode(data).encode()
        ctype = "application/x-www-form-urlencoded"
    else:
        body, ctype = None, None
    req = urllib.request.Request(url, data=body, method=method or ("POST" if body else "GET"))
    if ctype:
        req.add_header("Content-Type", ctype)
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", UA)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read().decode(errors="replace")
            try:
                return r.status, json.loads(raw or "{}")
            except Exception:
                return r.status, {"raw": raw[:500]}
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw or "{}")
        except Exception:
            return e.code, {"raw": raw[:500]}
    except Exception as e:  # network
        return 0, {"error": repr(e)}


def write_status(**kw):
    kw["updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    tmp = STATUS + ".tmp"
    with open(tmp, "w") as f:
        json.dump(kw, f, indent=1)
    os.replace(tmp, STATUS)


def main():
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    code, dc = request(f"{BASE}/api/v1/oauth2/device/code", data={
        "client_id": CLIENT_ID, "scope": SCOPE,
        "code_challenge": challenge, "code_challenge_method": "S256"})
    if code != 200 or "device_code" not in dc:
        write_status(state="error", step="device_code", http=code, body=dc)
        print("device code failed", code, dc)
        sys.exit(1)
    url = dc.get("verification_uri_complete") or dc["verification_uri"]
    expires_at = time.time() + int(dc.get("expires_in", 900))
    interval = int(dc.get("interval") or 5)
    write_status(state="waiting", url=url, user_code=dc.get("user_code"), expires_at=expires_at)
    print("OPEN:", url, flush=True)

    tok = None
    while time.time() < expires_at:
        time.sleep(interval)
        code, tok = request(f"{BASE}/api/v1/oauth2/token", data={
            "grant_type": GRANT, "client_id": CLIENT_ID,
            "device_code": dc["device_code"], "code_verifier": verifier})
        if code == 200 and tok.get("access_token"):
            break
        err = (tok or {}).get("error", "")
        if err == "slow_down":
            interval += 5
            continue
        if err in ("authorization_pending", "") or code == 0:
            continue
        write_status(state="error", step="token", http=code, body=tok)
        print("token error", code, tok)
        sys.exit(1)
    else:
        write_status(state="expired")
        print("expired")
        sys.exit(1)

    os.makedirs(os.path.dirname(CREDS), exist_ok=True)
    creds = {
        "access_token": tok["access_token"],
        "refresh_token": tok.get("refresh_token"),
        "token_type": tok.get("token_type", "Bearer"),
        "resource_url": tok.get("resource_url") or "portal.qwen.ai",
        "expiry_date": int((time.time() + int(tok.get("expires_in", 3600))) * 1000),
    }
    with open(CREDS, "w") as f:
        json.dump(creds, f, indent=1)
    os.chmod(CREDS, 0o600)
    print("creds written", CREDS, "resource_url=", creds["resource_url"], flush=True)

    host = creds["resource_url"]
    if not host.startswith("http"):
        host = "https://" + host
    api = host.rstrip("/")
    if not api.endswith("/v1"):
        api += "/v1"
    hdr = {"Authorization": f"Bearer {creds['access_token']}",
           "X-DashScope-CacheControl": "enable", "X-DashScope-UserAgent": UA,
           "X-DashScope-AuthType": "qwen-oauth"}
    mcode, models = request(f"{api}/models", headers=hdr)
    model_ids = []
    if mcode == 200 and isinstance(models, dict):
        model_ids = [m.get("id") for m in models.get("data", []) if isinstance(m, dict)]
    tried = []
    ok_model = None
    reply = None
    for m in (model_ids[:3] + [c for c in CANDIDATE_MODELS if c not in model_ids]):
        ccode, resp = request(f"{api}/chat/completions", headers=hdr, json_body={
            "model": m, "max_tokens": 20,
            "messages": [{"role": "user", "content": "Reply with the single word OK."}]})
        snippet = resp if ccode != 200 else (resp.get("choices", [{}])[0].get("message", {}).get("content"))
        tried.append({"model": m, "http": ccode, "resp": snippet if ccode != 200 else None})
        if ccode == 200:
            ok_model, reply = m, snippet
            break
    write_status(state="ok" if ok_model else "login_ok_api_failed", api=api,
                 models_http=mcode, models=model_ids[:40], tried=tried,
                 working_model=ok_model, reply=reply, expiry_date=creds["expiry_date"])
    print("DONE state=", "ok" if ok_model else "login_ok_api_failed", "model=", ok_model, "reply=", reply)


if __name__ == "__main__":
    main()
