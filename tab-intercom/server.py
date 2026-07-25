#!/usr/bin/env python3
"""tab-intercom — live tablet cam + phone→tablet voice, served from the box.

One page (token-gated) does both:
  - live view: polls Fully Kiosk's remote camshot (~1 fps, front cam)
  - push-to-talk: records mic in the browser (MediaRecorder), POSTs the clip
    here; box transcodes to mp3 (ffmpeg) and tells Fully to play it on the
    tablet speaker
  - quick TTS line to the tablet

Exposure: bind 127.0.0.1:8093 + LAN; reached via `tailscale serve --https=10000`
(tailnet-only — NEVER funnel this; it's a camera + mic in the flat).
The tablet itself fetches clips over plain LAN HTTP from /audio/<random>.mp3.

Token: .token next to this file (auto-generated on first run).
"""
import json
import secrets
import subprocess
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
PORT = 8093
FULLY = "http://192.168.0.160:2323"
FULLY_PW = "tomastab2026"
BOX_LAN = "192.168.0.107"          # URL the TABLET uses to fetch clips
AUDIO_DIR = HERE / "audio"
TOKEN_PATH = HERE / ".token"
LOG = HERE / "intercom.log"


def log(msg):
    with LOG.open("a") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} {msg}\n")


def token():
    if not TOKEN_PATH.exists():
        TOKEN_PATH.write_text(secrets.token_urlsafe(18) + "\n")
        TOKEN_PATH.chmod(0o600)
    return TOKEN_PATH.read_text().strip()


TOKEN = None  # set in __main__


def fully(cmd, **params):
    qs = urllib.parse.urlencode({"cmd": cmd, "password": FULLY_PW, **params})
    with urllib.request.urlopen(f"{FULLY}/?{qs}", timeout=15) as r:
        return r.read()


PAGE = """<!doctype html><meta charset=utf-8>
<meta name=viewport content='width=device-width,initial-scale=1'>
<title>Plansetke intercom</title>
<body style='font-family:sans-serif;background:#0d1117;color:#eef;margin:0;padding:16px;text-align:center'>
<h3 style='margin:4px 0'>Plansetke — live</h3>
<img id=cam style='width:100%;max-width:640px;border-radius:10px;background:#222;aspect-ratio:11/9'>
<div style='margin:18px 0'>
<button id=ptt style='width:80%;max-width:400px;padding:22px;font-size:1.3em;border:0;border-radius:14px;background:#238636;color:#fff'>&#127908; Hold to talk</button>
<div id=st style='margin-top:8px;color:#8b949e'>idle</div></div>
<div><input id=tts placeholder='or type a line to speak…' style='padding:10px;width:60%;max-width:300px;border-radius:8px;border:1px solid #333;background:#161b22;color:#eef'>
<button onclick=say() style='padding:10px 16px;border-radius:8px;border:0;background:#1f6feb;color:#fff'>Say</button></div>
<script>
const T=new URLSearchParams(location.search).get('t');
const cam=document.getElementById('cam'),st=document.getElementById('st'),ptt=document.getElementById('ptt');
setInterval(()=>{cam.src='/camshot?t='+T+'&x='+Date.now()},1100);
let rec,chunks=[];
async function start(e){e.preventDefault();
 try{const s=await navigator.mediaDevices.getUserMedia({audio:true});
  chunks=[];rec=new MediaRecorder(s);rec.ondataavailable=e=>chunks.push(e.data);
  rec.onstop=async()=>{s.getTracks().forEach(t=>t.stop());
   st.textContent='sending…';
   const r=await fetch('/voice?t='+T,{method:'POST',body:new Blob(chunks)});
   st.textContent=r.ok?'played on tablet ✅':'failed: '+await r.text();};
  rec.start();ptt.style.background='#da3633';st.textContent='recording — release to send';}
 catch(err){st.textContent='mic blocked: '+err.message;}}
function stop(e){e.preventDefault();if(rec&&rec.state=='recording')rec.stop();ptt.style.background='#238636';}
ptt.addEventListener('pointerdown',start);ptt.addEventListener('pointerup',stop);ptt.addEventListener('pointerleave',stop);
async function say(){const v=document.getElementById('tts').value.trim();if(!v)return;
 st.textContent=(await fetch('/say?t='+T+'&text='+encodeURIComponent(v))).ok?'spoken ✅':'TTS failed';}
</script>"""


class Handler(BaseHTTPRequestHandler):
    def _ok(self, body, ctype="text/plain"):
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authed(self, q):
        return secrets.compare_digest(q.get("t", [""])[0], TOKEN)

    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(url.query)
        # tablet fetches clips unauthenticated (random names, LAN/tailnet only)
        if url.path.startswith("/audio/"):
            f = AUDIO_DIR / Path(url.path).name
            if f.is_file() and AUDIO_DIR.resolve() in f.resolve().parents:
                self._ok(f.read_bytes(), "audio/mpeg")
            else:
                self.send_error(404)
            return
        if not self._authed(q):
            self.send_error(403)
            return
        if url.path == "/":
            self._ok(PAGE.encode(), "text/html; charset=utf-8")
        elif url.path == "/camshot":
            try:
                self._ok(fully("getCamshot"), "image/jpeg")
            except Exception as e:
                self.send_error(502, str(e)[:80])
        elif url.path == "/say":
            try:
                fully("textToSpeech", text=q.get("text", [""])[0][:300])
                self._ok(b"ok")
            except Exception as e:
                self.send_error(502, str(e)[:80])
        else:
            self.send_error(404)

    def do_POST(self):
        url = urllib.parse.urlparse(self.path)
        if not self._authed(urllib.parse.parse_qs(url.query)):
            self.send_error(403)
            return
        if url.path != "/voice":
            self.send_error(404)
            return
        raw = self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 20_000_000))
        if len(raw) < 200:
            self.send_error(400, "empty clip")
            return
        name = f"v{secrets.token_hex(6)}.mp3"
        AUDIO_DIR.mkdir(exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(suffix=".webm") as tmp:
                tmp.write(raw)
                tmp.flush()
                subprocess.run(["ffmpeg", "-y", "-i", tmp.name, "-vn", "-b:a", "64k",
                                str(AUDIO_DIR / name)],
                               capture_output=True, timeout=30, check=True)
            fully("stopSound")
            fully("playSound", url=f"http://{BOX_LAN}:{PORT}/audio/{name}", loop="false")
        except Exception as e:
            log(f"voice failed: {e}")
            self.send_error(502, str(e)[:100])
            return
        log(f"voice clip {name} ({len(raw)}b) -> tablet")
        # keep only the last 20 clips
        for old in sorted(AUDIO_DIR.glob("v*.mp3"))[:-20]:
            old.unlink(missing_ok=True)
        self._ok(b"ok")

    def log_message(self, fmt, *args):
        pass


if __name__ == "__main__":
    TOKEN = token()
    log(f"start :{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
