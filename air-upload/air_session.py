#!/usr/bin/env python3
"""Air session via a hijacked Cognito refresh token (no API key, no Google in the loop).

Air authenticates its web API with an AWS Cognito JWT: the browser sends
`Authorization: <idToken>` to api.air.inc. Cognito refresh tokens live ~30 days and can be
exchanged for fresh idTokens from anywhere with just the (public, secret-less) app clientId.
So we capture the refresh token ONCE from a logged-in Air tab and renew forever headlessly.

Capture (once, from Tomas's logged-in app.air.inc tab):
  DevTools > Application > Local Storage > https://app.air.inc
  Keys look like  CognitoIdentityServiceProvider.<clientId>.<user>.refreshToken
  Run the one-liner in README to dump them, paste JSON into ~/.config/air/cognito.json:
    {"clientId":"...","region":"us-east-1","refreshToken":"...","workspaceId":"..."}

This module: get_id_token() (cached, auto-refresh on expiry) and auth_headers().
"""
import base64, json, os, time
from pathlib import Path
import requests

CFG = Path.home() / ".config" / "air" / "cognito.json"
CACHE = Path.home() / ".config" / "air" / ".jwt_cache.json"
KNOWN_CLIENTS = ["1h7dfp1g14jb92lstrkf96i6c", "25j49n2d316fpn496kttr32rsm"]  # from app.air.inc bundle


def _cfg():
    if not CFG.exists():
        raise SystemExit(f"missing {CFG}; see README capture steps")
    c = json.loads(CFG.read_text())
    c.setdefault("region", "us-east-1")
    if not c.get("refreshToken") or not c.get("clientId"):
        raise SystemExit(f"{CFG} needs at least clientId + refreshToken")
    return c


def _jwt_exp(tok):
    try:
        p = tok.split(".")[1]
        p += "=" * (-len(p) % 4)
        return json.loads(base64.urlsafe_b64decode(p)).get("exp", 0)
    except Exception:
        return 0


def _refresh(c):
    """Cognito InitiateAuth REFRESH_TOKEN_AUTH -> fresh idToken (public client, no secret)."""
    r = requests.post(
        f"https://cognito-idp.{c['region']}.amazonaws.com/",
        headers={"content-type": "application/x-amz-json-1.1",
                 "x-amz-target": "AWSCognitoIdentityProviderService.InitiateAuth"},
        data=json.dumps({"AuthFlow": "REFRESH_TOKEN_AUTH", "ClientId": c["clientId"],
                         "AuthParameters": {"REFRESH_TOKEN": c["refreshToken"]}}),
        timeout=30)
    if r.status_code != 200:
        raise SystemExit(f"Cognito refresh failed {r.status_code}: {r.text[:300]}\n"
                         f"Token likely expired (>30d) or wrong clientId (try {KNOWN_CLIENTS}). Re-capture.")
    res = r.json()["AuthenticationResult"]
    return res["IdToken"], res.get("AccessToken", "")


def get_id_token(force=False):
    c = _cfg()
    if not force and CACHE.exists():
        try:
            cached = json.loads(CACHE.read_text())
            if cached.get("idToken") and _jwt_exp(cached["idToken"]) - 120 > time.time():
                return cached["idToken"]
        except Exception:
            pass
    idt, acc = _refresh(c)
    CACHE.write_text(json.dumps({"idToken": idt, "accessToken": acc}))
    os.chmod(CACHE, 0o600)
    return idt


def workspace_id():
    return _cfg().get("workspaceId")


def auth_headers():
    h = {"Authorization": get_id_token(), "X-Air-Client-Version": "web"}
    ws = workspace_id()
    if ws:
        h["x-air-workspace-id"] = ws
    return h


if __name__ == "__main__":
    import sys
    if "--probe" in sys.argv:
        h = auth_headers()
        exp = _jwt_exp(h["Authorization"])
        print(f"idToken OK, exp in {int(exp - time.time())}s")
        r = requests.get("https://api.air.inc/workspaces", headers=h, timeout=30)
        print(f"GET /workspaces -> {r.status_code}: {r.text[:400]}")
    else:
        print(get_id_token())
