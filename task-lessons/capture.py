#!/usr/bin/env python3
"""Capture one task/cron/agent outcome as a lesson.

Reads a JSON record from stdin. Always appends one atomic line to ledger.jsonl
(the source of truth). Then, unless it's a plain success, writes a structured
gbrain page and wires the graph the flat brain is missing: tags (task-lesson,
skill:<skill>, <verdict>), a timeline entry, and best-effort typed links to the
owning project page. gbrain failures are logged but never fail the capture --
the ledger always lands.

Record schema (stdin JSON):
  skill        (required)  cron/skill/agent name, e.g. "bq-clickup-perf"
  verdict      (required)  success | fixed | failed
  summary      (required)  one line: what happened
  lesson       (optional)  one-line extracted lesson
  how_to_apply (optional)  one line: how to act on the lesson next time
  context      (optional)  inputs/env worth recording
  tags         (optional)  list[str] of extra tags
  link_to      (optional)  list[str] of gbrain slugs to link this lesson to
  exit_code    (optional)  int
  duration_s   (optional)  int/float
  force_page   (optional)  bool -- write a gbrain page even on plain success

Usage:  python3 capture.py < record.json
"""
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "ledger.jsonl")
CONFIG = os.path.join(HERE, "config.json")

REQUIRED = ("skill", "verdict", "summary")


def load_config():
    try:
        with open(CONFIG) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def ensure_env():
    """gbrain is a bun-shebang .ts; embeddings need the Gemini key."""
    home = os.path.expanduser("~")
    bun = os.path.join(home, ".bun", "bin")
    if bun not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = bun + os.pathsep + os.environ.get("PATH", "")
    envf = os.path.join(home, ".hermes", ".env")
    if os.path.exists(envf):
        try:
            with open(envf) as f:
                for line in f:
                    for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
                        if line.startswith(k + "=") and not os.environ.get(k):
                            os.environ[k] = line.split("=", 1)[1].strip()
        except OSError:
            pass


def gbrain(args, stdin_text=None, warn=True):
    """Run a gbrain subcommand. Best-effort: return (ok, output)."""
    try:
        r = subprocess.run(
            ["gbrain", *args],
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if r.returncode != 0:
            if warn:
                print(f"WARN gbrain {args[0]}: {r.stderr.strip()[:200]}", file=sys.stderr)
            return False, r.stderr
        return True, r.stdout
    except Exception as e:  # noqa: BLE001 -- capture must never crash the caller
        if warn:
            print(f"WARN gbrain {args[0]} raised: {e}", file=sys.stderr)
        return False, str(e)


def append_ledger(rec):
    line = json.dumps(rec, ensure_ascii=False)
    fd = os.open(LEDGER, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, (line + "\n").encode("utf-8"))
    finally:
        os.close(fd)


def render_page(rec, cfg):
    date = rec["ts"][:10]
    skill = rec["skill"]
    verdict = rec["verdict"]
    # Tags are applied via explicit `gbrain tag` calls (reliable index); they are
    # intentionally NOT placed in frontmatter (colon tags + a failed frontmatter
    # parse would silently drop them).
    tags = [cfg.get("base_tag", "task-lesson"), f"skill:{skill}", verdict]
    tags += [t for t in rec.get("tags", []) if t not in tags]
    # YAML-safe the title: collapse whitespace and json-quote so embedded ": "
    # (common in tracebacks) cannot break the frontmatter and demote the page.
    raw_title = f"{skill} - {verdict} - {rec['summary']}"
    safe_title = json.dumps(" ".join(raw_title.split())[:90], ensure_ascii=False)
    meta = f"exit {rec.get('exit_code', 'NA')}"
    if rec.get("duration_s") is not None:
        meta += f", {rec['duration_s']}s"
    fm = [
        "---",
        f"type: {cfg.get('page_type', 'feedback')}",
        f"title: {safe_title}",
        f"date: {date}",
        "---",
        "",
        f"**Skill/cron:** {skill}",
        f"**Verdict:** {verdict}  ({meta})",
        f"**When:** {rec['ts']}",
        "",
        f"**What happened:** {rec['summary']}",
    ]
    if rec.get("lesson"):
        fm += ["", f"**Lesson:** {rec['lesson']}"]
    if rec.get("how_to_apply"):
        fm += ["", f"**How to apply:** {rec['how_to_apply']}"]
    if rec.get("context"):
        fm += ["", f"**Context:** {rec['context']}"]
    fm += ["", f"Source: task-lessons ledger {rec['id']}"]
    return "\n".join(fm) + "\n", tags


def write_to_brain(rec, cfg):
    slug = f"{cfg.get('slug_prefix', 'lessons')}/{rec['skill']}/{rec['id']}"
    body, tags = render_page(rec, cfg)
    ok, _ = gbrain(["put", slug], stdin_text=body)
    if not ok:
        return None
    for t in tags:
        gbrain(["tag", slug, t], warn=False)
    gbrain(["timeline-add", slug, rec["ts"][:10], f"{rec['verdict']}: {rec['summary'][:80]}"], warn=False)
    for target in rec.get("link_to", []):
        gbrain(["link", slug, target, "--link-type", "lesson-of", "--link-source", "task-lessons"], warn=False)
    gbrain(["embed", slug], warn=False)
    return slug


def main():
    ensure_env()
    cfg = load_config()
    try:
        rec = json.load(sys.stdin)
    except json.JSONDecodeError as e:
        print(f"ERROR: stdin is not valid JSON: {e}", file=sys.stderr)
        return 1
    if not isinstance(rec, dict):
        print("ERROR: record must be a JSON object", file=sys.stderr)
        return 1
    missing = [k for k in REQUIRED if not rec.get(k)]
    if missing:
        print(f"ERROR: missing required field(s): {', '.join(missing)}", file=sys.stderr)
        return 1
    valid = set(cfg.get("valid_verdicts", ["success", "fixed", "failed"]))
    if rec["verdict"] not in valid:
        print(f"ERROR: verdict must be one of {sorted(valid)}", file=sys.stderr)
        return 1

    rec.setdefault("id", "tl_" + uuid.uuid4().hex[:8])
    rec.setdefault("ts", datetime.now().astimezone().isoformat(timespec="seconds"))
    rec.setdefault("promoted", False)
    rec.setdefault("tags", [])

    append_ledger(rec)

    write_page = rec.get("force_page", False) or rec["verdict"] != "success" or bool(rec.get("lesson"))
    if not write_page and not cfg.get("write_page_on_success", False):
        print(f"OK logged {rec['id']} [{rec['skill']}/{rec['verdict']}] (ledger only)")
        return 0

    slug = write_to_brain(rec, cfg)
    if slug:
        print(f"OK logged {rec['id']} [{rec['skill']}/{rec['verdict']}] -> brain:{slug}")
    else:
        print(f"OK logged {rec['id']} [{rec['skill']}/{rec['verdict']}] (ledger only; brain write failed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
