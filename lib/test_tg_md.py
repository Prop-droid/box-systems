"""Regression tests for tg_md.unwrap_prose_fences (Tomas 2026-09-01: prose
must never render as monospace copy boxes; real code keeps its fence).
Run: python3 ~/systems/lib/test_tg_md.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tg_md import md_to_html, unwrap_prose_fences

# name -> (fenced markdown, expect fence kept)
CASES = {
    "lp copy": ("```\nWhat a Day of This Actually Costs\n"
                "1 box: $34.99, which is $1.25 a day\n"
                "2 boxes: $31.49 each, $1.12 a day\n\n"
                "Three is where it drops under a dollar,\n"
                "and it is twelve weeks of candy.\n```", False),
    "email draft": ("```\nSubject: Your candy is waiting\n"
                    "Hey, quick note about the box you looked at.\n"
                    "It ships free this week.\nGrab it before Sunday.\n```", False),
    "hooks list": ("```\n1. POV: your candy has more fiber than your cereal\n"
                   "2. I ate candy every night for 30 days\n"
                   "3. My dietitian said keep eating this\n```", False),
    "json": ('```\n{\n  "key": "value",\n  "n": 2\n}\n```', True),
    "traceback": ("```\nTraceback (most recent call last):\n"
                  '  File "bot.py", line 3, in <module>\n'
                  "    main()\nValueError: bad\n```", True),
    "untagged cmds": ('```\ngit add -A\ngit commit -m "fix"\n```', True),
    "tagged bash": ("```bash\nsystemctl --user restart tg-dev-bot\n```", True),
    "tagged diff": ("```diff\n-old line\n+new line\n```", True),
    "empty fence": ("```\n```", True),
    "untagged python": ("```\nresult = compute(x)\nif result > 0:\n"
                        "    return result\n```", True),
}

failures = 0
for name, (src, expect_kept) in CASES.items():
    kept = "```" in unwrap_prose_fences(src)
    if kept != expect_kept:
        failures += 1
        print(f"FAIL {name}: fence {'kept' if kept else 'unwrapped'}, "
              f"expected {'kept' if expect_kept else 'unwrapped'}")

# pipeline sanity: unwrapped prose must not become <pre>
html_out = md_to_html(unwrap_prose_fences(CASES["lp copy"][0]))
if "<pre>" in html_out:
    failures += 1
    print("FAIL pipeline: unwrapped prose still rendered as <pre>")

if failures:
    sys.exit(f"{failures} failure(s)")
print(f"OK: {len(CASES)} fence cases + pipeline pass")
