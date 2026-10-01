#!/usr/bin/env python3
"""Upload images (or any files) to an Air board via Air's public API.

Creds (600):  ~/.config/air/api_key        workspace-scoped key (Workspace Settings > API Access)
              ~/.config/air/workspace_id   the workspace UUID shown on the same page
Env overrides: AIR_API_KEY, AIR_WORKSPACE_ID

Usage:
  air_upload.py FILE|DIR|ZIP ... --board <uuid | app.air.inc/a/<short> | "Board title">
  air_upload.py FILES --new-board "SH-19151 statics" [--parent <board>]
  air_upload.py --check                      # auth smoke test, lists 5 newest boards
  air_upload.py --find "Mini Bites"          # board name search
  add --dry-run to print the plan without uploading, --json for machine output.

Flow per file: POST /v1/uploads {fileName,ext,size,mime,parentBoardId} -> PUT bytes to uploadUrl.
Files >= 5 GB (multipart) are refused; this is an image/short-video tool.
"""
import argparse, json, mimetypes, os, re, sys, tempfile, time, zipfile
from datetime import datetime, timezone
from pathlib import Path

import requests

API = "https://api.air.inc"
CFG = Path.home() / ".config" / "air"
MEDIA_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".pdf", ".psd", ".ai", ".tif", ".tiff", ".heic"}
UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def _read(name, env):
    v = os.environ.get(env)
    if v:
        return v.strip()
    p = CFG / name
    if p.exists():
        return p.read_text().strip()
    sys.exit(f"missing {p} (or ${env}); see header of this script")


class Air:
    def __init__(self, session=False):
        self.s = requests.Session()
        self.session_mode = session
        if session:
            import air_session  # hijacked Cognito JWT, no api key
            h = air_session.auth_headers()
            if not h.get("x-air-workspace-id"):
                h["x-air-workspace-id"] = _read("workspace_id", "AIR_WORKSPACE_ID")
            h["accept"] = "application/json"
            self.s.headers.update(h)
            # public /v1 API expects "Bearer <jwt>"; web API uses the raw jwt
            self.s.headers["Authorization"] = "Bearer " + self.s.headers["Authorization"]
        else:
            self.s.headers.update({
                "x-api-key": _read("api_key", "AIR_API_KEY"),
                "x-air-workspace-id": _read("workspace_id", "AIR_WORKSPACE_ID"),
                "accept": "application/json",
            })

    def _req(self, method, path, **kw):
        for attempt in range(4):
            r = self.s.request(method, API + path, timeout=60, **kw)
            if r.status_code in (429, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            if r.status_code >= 400:
                sys.exit(f"{method} {path} -> {r.status_code}: {r.text[:400]}")
            return r
        sys.exit(f"{method} {path} kept failing ({r.status_code})")

    def boards(self, name=None, parent=None, limit=25):
        q = {"limit": limit}
        if name:
            q["name"] = name
        if parent:
            q["parentBoardId"] = parent
        return self._req("GET", "/v1/boards", params=q).json().get("data", [])

    def board(self, board_id):
        return self._req("GET", f"/v1/boards/{board_id}").json()

    def create_board(self, title, parent=None):
        body = {"title": title}
        if parent:
            body["parentBoardId"] = parent
        return self._req("POST", "/v1/boards", json=body).json()

    def upload(self, path: Path, board_id):
        size = path.stat().st_size
        if size >= 5 * 1024 ** 3:
            sys.exit(f"{path.name}: >=5GB needs multipart, not supported here")
        mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        body = {
            "fileName": path.name,
            "ext": path.suffix.lstrip(".").lower(),
            "size": size,
            "mime": mime,
            "recordedAt": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
            "parentBoardId": board_id,
        }
        meta = self._req("POST", "/v1/uploads", json=body).json()
        if "uploadUrl" not in meta:
            sys.exit(f"{path.name}: unexpected upload response {meta}")
        with path.open("rb") as fh:
            for attempt in range(3):
                put = requests.put(meta["uploadUrl"], data=fh, timeout=600,
                                   headers={"Content-Type": mime, "Content-Length": str(size)})
                if put.status_code < 300:
                    break
                fh.seek(0)
                time.sleep(2 ** attempt)
            else:
                sys.exit(f"{path.name}: S3 PUT failed {put.status_code} {put.text[:200]}")
        return {"file": path.name, "assetId": meta["assetId"], "versionId": meta["versionId"], "bytes": size}


def resolve_board(air: Air, ref: str):
    """uuid | app.air.inc/a/<short> share link | board title -> board id."""
    ref = ref.strip()
    if UUID_RE.match(ref):
        return ref
    m = re.search(r"app\.air\.inc/a/([0-9a-z]+)", ref)
    if m:  # public share link: shorturl endpoint needs no auth
        r = requests.get(f"{API}/shorturl/{m.group(1)}", timeout=30)
        if r.status_code != 200:
            sys.exit(f"share link {ref} did not resolve ({r.status_code})")
        return r.json()["data"]["id"]
    m = re.search(r"app\.air\.inc/b/(?:[^/]*?-)?([0-9a-f-]{36})", ref)
    if m:
        return m.group(1)
    hits = air.boards(name=ref, limit=10)
    exact = [b for b in hits if b.get("title", "").lower() == ref.lower()]
    pick = exact or hits
    if not pick:
        sys.exit(f"no board matching {ref!r}")
    if len(pick) > 1 and not exact:
        names = ", ".join(f'{b["title"]} ({b["id"]})' for b in pick)
        sys.exit(f"ambiguous board {ref!r}: {names}")
    return pick[0]["id"]


def collect(inputs, tmp):
    files = []
    for raw in inputs:
        p = Path(raw).expanduser()
        if not p.exists():
            sys.exit(f"not found: {p}")
        if p.is_dir():
            files += sorted(x for x in p.iterdir() if x.is_file() and x.suffix.lower() in MEDIA_EXT)
        elif p.suffix.lower() == ".zip":
            out = Path(tmp) / p.stem
            with zipfile.ZipFile(p) as z:
                z.extractall(out)
            files += sorted(x for x in out.rglob("*") if x.is_file() and x.suffix.lower() in MEDIA_EXT
                            and "__MACOSX" not in x.parts and not x.name.startswith("."))
        else:
            files.append(p)
    return files


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="*", help="files, dirs, or zips")
    ap.add_argument("--board", help="target board: uuid | app.air.inc/a/<short> | title")
    ap.add_argument("--new-board", metavar="TITLE", help="create this board and upload into it")
    ap.add_argument("--parent", help="parent board (same forms as --board) for --new-board")
    ap.add_argument("--check", action="store_true", help="auth smoke test")
    ap.add_argument("--find", metavar="NAME", help="search boards by name")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--session", action="store_true",
                    help="auth via hijacked Cognito token (~/.config/air/cognito.json) instead of an API key")
    a = ap.parse_args()

    air = Air(session=a.session)
    if a.check or a.find:
        for b in air.boards(name=a.find, limit=5 if a.check else 25):
            print(f'{b["id"]}  {b.get("title")}  (parent {b.get("parentBoardId") or "-"})')
        return
    if not a.inputs or not (a.board or a.new_board):
        ap.error("need inputs and --board or --new-board")

    with tempfile.TemporaryDirectory() as tmp:
        files = collect(a.inputs, tmp)
        if not files:
            sys.exit("nothing to upload")
        if a.new_board:
            parent = resolve_board(air, a.parent) if a.parent else None
            if a.dry_run:
                print(f"[dry-run] would create board {a.new_board!r} under {parent or 'workspace root'}")
                board_id = "<new-board>"
            else:
                board_id = air.create_board(a.new_board, parent)["id"]
        else:
            board_id = resolve_board(air, a.board)
        if a.dry_run:
            for f in files:
                print(f"[dry-run] {f.name}  {f.stat().st_size} B  -> board {board_id}")
            return
        results = []
        for i, f in enumerate(files, 1):
            r = air.upload(f, board_id)
            results.append(r)
            if not a.json:
                print(f"[{i}/{len(files)}] {r['file']}  asset {r['assetId']}", flush=True)
        out = {"boardId": board_id, "boardUrl": f"https://app.air.inc/b/{board_id}", "uploaded": results}
        if a.json:
            print(json.dumps(out, indent=1))
        else:
            print(f"\n{len(results)} file(s) -> {out['boardUrl']}")


if __name__ == "__main__":
    main()
