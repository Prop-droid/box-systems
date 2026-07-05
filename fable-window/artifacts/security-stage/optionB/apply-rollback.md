# Option B — apply / rollback (rebind services to localhost / tailnet)

Nothing here has been run. These are paste-ready commands for you to apply the
staged replacements. `STAGE=~/fable-window/artifacts/security-stage/optionB`.

## Back up first (enables clean rollback)
```
STAGE=~/fable-window/artifacts/security-stage/optionB
BK=~/security-stage-backup-$(date +%Y%m%d-%H%M%S); mkdir -p "$BK"
cp ~/.config/systemd/user/{md-server,creative-command-center,camofox,tablet-dash}.service "$BK"/
cp ~/camofox-browser/server.js "$BK"/camofox.server.js
cp ~/tablet-assistant/server.py "$BK"/tablet-server.py
echo "backed up to $BK"
```

## Apply
```
# 1. env-driven services: just swap the unit files
cp "$STAGE"/md-server.service              ~/.config/systemd/user/md-server.service
cp "$STAGE"/creative-command-center.service ~/.config/systemd/user/creative-command-center.service
cp "$STAGE"/camofox.service                ~/.config/systemd/user/camofox.service
cp "$STAGE"/tablet-dash.service            ~/.config/systemd/user/tablet-dash.service

# 2. hardcoded-bind services: patch the source (adds the HOST env the units set)
( cd ~/camofox-browser  && git apply "$STAGE"/camofox.server.js.patch )      # or hand-edit server.js:6070
( cd ~/tablet-assistant && git apply "$STAGE"/tablet-dash-server.py.patch )  # or hand-edit server.py

# 3. reload + restart
systemctl --user daemon-reload
systemctl --user restart md-server creative-command-center camofox tablet-dash
```

## Verify
```
ss -tlnp | grep -E ':(8092|3000|9377|8765)\b'
# EXPECT: 8092 bound 100.107.26.69, 3000/9377/8765 bound 127.0.0.1 (not 0.0.0.0)
curl -m3 -so /dev/null -w '%{http_code}\n' http://127.0.0.1:8092/   # 200 (local still works)
```
NOTE: after this, reach md-server over Tailscale (100.107.26.69:8092); reach CCC
via SSH tunnel or NoMachine; the tablet dashboard goes dark unless you moved the
tablet onto Tailscale (see tablet-dash.service warning) — prefer Option A there.

## Rollback
```
BK=~/security-stage-backup-YYYYMMDD-HHMMSS   # <- the dir printed above
cp "$BK"/{md-server,creative-command-center,camofox,tablet-dash}.service ~/.config/systemd/user/
cp "$BK"/camofox.server.js ~/camofox-browser/server.js
cp "$BK"/tablet-server.py  ~/tablet-assistant/server.py
systemctl --user daemon-reload
systemctl --user restart md-server creative-command-center camofox tablet-dash
```
(If you used `git apply`, `git -C ~/camofox-browser checkout -- server.js` and
`git -C ~/tablet-assistant checkout -- server.py` also revert the source cleanly.)
