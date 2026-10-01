# air-upload

Push images/videos into an Air board headlessly. Two auth modes:

- **API key** (`--board ...`, no flag): official public API, needs a Business/Enterprise admin key
  in `~/.config/air/api_key` + `~/.config/air/workspace_id`. Blocked for us (no API access).
- **Session hijack** (`--session`): reuses your logged-in Air session via its AWS Cognito refresh
  token. No API plan, no Google login on the box, renews itself ~30 days.

## Session hijack — capture once (2 min)

Air signs API calls with a Cognito JWT (`Authorization: <idToken>` to api.air.inc). The refresh
token lives in your browser's localStorage and mints fresh JWTs from anywhere.

1. On your Mac, open a logged-in **app.air.inc** tab. DevTools (Cmd+Opt+I) > Console. Paste:

   ```js
   (()=>{const L=localStorage,P="CognitoIdentityServiceProvider";let o={};
   for(let i=0;i<L.length;i++){const k=L.key(i);if(k.startsWith(P)&&k.endsWith(".refreshToken")){
   const c=k.split(".")[1],u=L.getItem(P+"."+c+".LastAuthUser");
   o={clientId:c,region:"us-east-1",refreshToken:L.getItem(k),idToken:L.getItem(P+"."+c+"."+u+".idToken")};}}
   copy(JSON.stringify(o));console.log("copied:",o.clientId?"ok":"NOT FOUND");})()
   ```

   It copies the credential JSON to your clipboard (nothing secret printed).

2. SSH to the box and paste it straight into the cred file (keeps it out of any chat):

   ```bash
   umask 077; mkdir -p ~/.config/air
   cat > ~/.config/air/cognito.json   # paste, then Ctrl-D
   ```

3. Prove it and auto-fill the workspace id:

   ```bash
   ~/systems/air-upload/air_session.py --probe        # expect: idToken OK + GET /workspaces 200
   ```

Refresh tokens expire after ~30 idle days or a password/SSO reset — re-run capture when `--probe` 401s.

## Upload

```bash
air_upload.py ~/Downloads/sha-mb-launch-images/cal30 --board https://app.air.inc/a/<short> --session
air_upload.py delivery.zip --new-board "SH-19151 statics" --parent "Shameless Statics" --session
```

`--board` accepts a uuid, an `/a/<short>` share link, a `/b/<slug-uuid>` workspace link, or a title.
Inputs may be files, dirs, or zips. `--dry-run` prints the plan; `--json` emits
`{boardId, boardUrl, uploaded:[{file, assetId}]}`. Then paste `boardUrl` into the ClickUp
`✨ File Link` field (see feedback_sha_image_delivery_file_naming).

## Files
- `air_session.py`  — Cognito refresh-token session, `--probe` to test, self-caching JWT.
- `air_upload.py`   — the uploader; `--session` uses the hijacked token, default uses an API key.
