# Security-stage — pick ONE remediation, apply with one command

Both options close the same hole from the sweep (NET-1..NET-5): the unauthenticated
0.0.0.0 services — CCC:3000, md-server:8092, camofox:9377, tablet-dash:8765,
visionclaw-shim:8643 — reachable by any host on the home LAN (192.168.0.0/24).
Nothing here has been applied. Files staged 2026-07-04; facts verified same day.

## The two options

### Option A — one nftables firewall (network layer)
- `optionA.nft` — **default-drop** LAN ruleset (task spec). Everything inbound is
  dropped unless allowed; tailnet gets full access; LAN keeps SSH, NoMachine,
  Syncthing, mDNS, DHCP, and tablet->8765 only.
- `optionA-variant-targeted-drop.nft` — lower-blast-radius alternative: keeps
  `policy accept` and drops ONLY the five app ports. Same table name (`inet fw`),
  same apply/rollback scripts. Use this if you want the smallest possible change.
- Apply: `bash optionA-apply.sh`   Rollback: `bash optionA-rollback.sh`
- Coexists with Tailscale's iptables-nft table (never edits it). Not persisted
  across reboot until you add an nftables include / boot unit (not staged).

### Option B — rebind each service to localhost / tailnet (application layer)
- `optionB/md-server.service` -> MD_HOST=100.107.26.69 (tailnet only)
- `optionB/creative-command-center.service` -> HOSTNAME=127.0.0.1
- `optionB/camofox.service` + `camofox.server.js.patch` -> CAMOFOX_HOST=127.0.0.1
- `optionB/tablet-dash.service` + `tablet-dash-server.py.patch` -> TABLET_DASH_HOST=127.0.0.1
- Apply/rollback + backup steps: `optionB/apply-rollback.md`
- Survives reboot automatically (it's the service config). Requires editing 4
  units + 2 source files and restarting the services.

## Blast-radius comparison

| Dimension | Option A (firewall) | Option B (rebind) |
|---|---|---|
| Files touched | 0 configs, 0 restarts | 4 units + 2 source patches, 4 restarts |
| Covers FUTURE 0.0.0.0 services | Yes — anything new is dropped by default | No — each new service must be rebound |
| Reboot persistence | No, until you add a boot unit | Yes, automatic |
| Reversibility | Instant: `nft delete table inet fw` | Restore backups + restart (staged) |
| Worst-case if you get it wrong | default-drop can lock out an un-enumerated inbound flow (SSH/DHCP/NoMachine) — mitigated by the explicit allows, but higher | a service fails to bind / a client loses access; contained to that one service |
| Defence-in-depth | Network layer only; service still answers on 0.0.0.0 behind the drop | App layer only; no firewall, a new 0.0.0.0 service is exposed again |
| Tablet dashboard (8765) | **Kept working** — allow is scoped to 192.168.0.160 | **Breaks** unless tablet is moved onto Tailscale (tablet is LAN-only today) |
| md-server / CCC / camofox | Closed on LAN, still 0.0.0.0-bound behind the drop | Genuinely bound to localhost/tailnet |

## Recommendation
- **Do both, in this order.** Option A first (one command, instant, covers today
  and every future service, and is the only clean way to keep the tablet dash
  working). Then Option B on md-server / CCC / camofox as defence-in-depth so they
  stop answering on 0.0.0.0 at all. Skip Option B for tablet-dash — Option A's
  scoped allow is the right tool there.
- If you only pick one: **Option A** (variant-targeted-drop if you want minimal
  change) — bigger coverage, zero service edits, keeps the tablet up.
- Independent of both: `SSH-1` (disable password auth) and `SSH-2` (passphrase the
  keys, see `ssh-key-passphrase-plan.md`) still matter — a firewall/rebind doesn't
  touch the SSH brute-force surface or the plaintext keys.
