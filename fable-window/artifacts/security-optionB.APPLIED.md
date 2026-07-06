# Security-stage Option B — APPLIED (task 34)

Applied live 2026-07-05 ~23:22 Europe/Vilnius on tomas-agent-box, under RULES rule 9
(Night-4 live exception, Tomas-approved). Scope: rebind md-server, CCC, camofox to
localhost/tailnet only. tablet-dash intentionally NOT touched (Option A is the right
tool there; rebinding would dark the LAN-only tablet).

Backup of all in-scope targets (units + camofox source):
`/home/tomas/security-stage-backup-20260705-232053/`

## Per-service before / after bind table

| Service | Port | BEFORE (live bind) | Staged change | AFTER (live bind) | Reachability verify | Result |
|---|---|---|---|---|---|---|
| md-server | 8092 | `0.0.0.0:8092` | unit `MD_HOST=0.0.0.0` -> `100.107.26.69` | `100.107.26.69:8092` | tailscale 100.107.26.69 = **200**; 127.0.0.1 = 000 (by design); LAN 0.0.0.0 gone | **PASS** |
| creative-command-center | 3000 | `*:3000` | unit `HOSTNAME=0.0.0.0` -> `127.0.0.1` | `*:3000` (unchanged) | 127.0.0.1 = 307 but bind still `*` (LAN NOT closed) | **FAILED -> ROLLED BACK** |
| camofox | 9377 | `*:9377` | `server.js:6070` honour `CAMOFOX_HOST`; unit `CAMOFOX_HOST=127.0.0.1` | `127.0.0.1:9377` | 127.0.0.1 `/`=200, `/health`=200, browser pre-warmed; tailscale = 000 (by design); LAN gone | **PASS** |
| tablet-dash | 8765 | `0.0.0.0:8765` | (out of scope) | `0.0.0.0:8765` (untouched) | n/a | SKIPPED (intentional) |

Note on verify semantics: each service binds a single interface, so it answers on its
intended interface only. md-server binds the tailnet IP (tailscale reachable, 127.0.0.1
refused by design). CCC/camofox target 127.0.0.1 (localhost reachable, tailnet refused by
design). Pass criterion per service = reachable on intended interface + service active +
LAN 0.0.0.0/192.168.0.107 exposure gone.

## What changed on disk

- `~/.config/systemd/user/md-server.service` — replaced with staged unit (MD_HOST=100.107.26.69). LIVE.
- `~/camofox-browser/server.js` — patched line 6070 via `git apply` (honours CAMOFOX_HOST, default 127.0.0.1). LIVE.
- `~/.config/systemd/user/camofox.service` — replaced with staged unit (adds CAMOFOX_HOST=127.0.0.1). LIVE.
- `~/.config/systemd/user/creative-command-center.service` — swapped, verified FAILED, then RESTORED from backup. Net: unchanged from pre-task state.

## CCC failure — root cause

The staged Option-B patch only sets `HOSTNAME=127.0.0.1` in the unit. The dev script is
`"dev": "next dev"` on **Next.js 14.2.35**. `next dev` does NOT honour the `HOSTNAME` env
var for its listen address, so it kept binding `*:3000` (all interfaces, LAN included).
Rolled back to avoid a false sense of closure with zero actual bind change.

Real fix for CCC (NOT applied — out of this task's staged scope):
- Change the dev script to `next dev -H 127.0.0.1` (or `next dev --hostname 127.0.0.1`),
  which is the flag `next dev` actually respects; OR
- Cover it with Option A's firewall drop on 3000 (network-layer, no source edit needed).
Recommend folding CCC into Option A rather than re-attempting the app-layer rebind.

## Net security outcome

- md-server (8092): LAN exposure **closed**, now tailnet-only. ✓
- camofox (9377): LAN exposure **closed**, now localhost-only. ✓
- CCC (3000): still `*:3000` LAN-exposed — staged fix ineffective, needs `-H` flag or Option A.
- tablet-dash (8765): still `0.0.0.0` by design (out of scope; use Option A scoped allow).

## Rollback (if needed)

```
BK=/home/tomas/security-stage-backup-20260705-232053
cp "$BK"/{md-server,camofox}.service ~/.config/systemd/user/
cp "$BK"/camofox.server.js ~/camofox-browser/server.js   # or: git -C ~/camofox-browser checkout -- server.js
systemctl --user daemon-reload
systemctl --user restart md-server camofox
```
(CCC already at its original state — no rollback needed.)
