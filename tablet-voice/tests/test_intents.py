"""Tier 0 intent table test (14d 7b): 30 phrasings incl. real synthetic Whisper transcripts, plus the F2 buy/by
cases (2026-11-04: fix_buy, "by" as a due marker, the list-phrase guard), the F2 review cases (questions, completions
and reminds skip P_ADD; a verbless "by today" is no add; the guard needs a list noun), a fix_buy table and a
question/completion grid that must never give task.add.
Run: .venv/bin/python tests/test_intents.py   (exit 0 = every case passes)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from intents import strip_wake, match, best_task, fix_buy  # noqa: E402

cases = [
    # (heard transcript, expected intent, expected key slot)
    ("Hey Jarvis, add buy milk to my personal list.", "task.add", "buy milk|personal|None"),
    ("Hey Jarvis, and buy milk to my personal list.", "task.add", "buy milk|personal|None"),
    ("They jar this at my milk to my personal list.", "task.add", "my milk|personal|None"),
    ("Hey Jarvis, Ed. Call the dentist to my worklist for tomorrow.", "task.add", "call the dentist|work|tomorrow"),
    ("Hey Jarvis, add call the dentist to my work list for tomorrow.", "task.add", "call the dentist|work|tomorrow"),
    ("Jarvis put renew passport on the work list", "task.add", "renew passport|work|None"),
    ("Hey Jarvis add eggs to the shopping list", "task.add", "eggs|shopping|None"),
    ("hey jarvis add pick up parcel today", "task.add", "pick up parcel|personal|today"),
    ("Hey Jarvis, remind me to water the plants tomorrow", "task.add", "water the plants|personal|tomorrow"),
    ("Hey Jarvis, mark buy milk as done.", "task.complete", "buy milk"),
    ("H.R.V.S. Mark by Milke has done.", "task.complete", "by milke"),
    ("Hey Jarvis, tick off call the dentist", "task.complete", "call the dentist"),
    ("Hey Jarvis, I finished the tax return", "task.complete", "the tax return"),
    ("Jarvis, the dentist task is done", "task.complete", "the dentist task"),
    ("Hey Jarvis, what is next?", "next.event", ""),
    ("Hey Jarvis, what's next", "next.event", ""),
    ("hey jarvis what's coming up", "next.event", ""),
    ("H.R. This, what is on my schedule tomorrow?", "schedule.tomorrow", ""),
    ("Hey Jarvis, tomorrow's schedule", "schedule.tomorrow", ""),
    ("Hey Jarvis what do I have tomorrow", "schedule.tomorrow", ""),
    ("They jar this turn on dark mode.", "theme", "dark"),
    ("Hey Jarvis, switch to light mode", "theme", "light"),
    ("Hey Jarvis turn off dark mode", "theme", "light"),
    ("Hey Jarvis, night mode", "theme", "dark"),
    ("Hey Jarvis, auto theme", "theme", "auto"),
    ("Hey Jarvis, never mind", "cancel", ""),
    ("Hey Travis, can you pass the salt?", None, ""),
    ("You", None, ""),
    ("Thank you.", None, ""),
    ("Hey Jarvis, what's the weather like", None, ""),
    # F2 buy/by: Whisper hears "add buy" as "add by"; deadlines after by stay; "by today/tomorrow" is a due marker
    ("Add by milk to my personal list.", "task.add", "buy milk|personal|None"),
    ("Add bye eggs to my shopping list.", "task.add", "buy eggs|shopping|None"),
    ("Hey Jarvis, add by milk to my personal list", "task.add", "buy milk|personal|None"),
    ("Add by Friday send the invoice to my work list.", "task.add", "by friday send the invoice|work|None"),
    ("Add bi-weekly report to my work list.", "task.add", "bi weekly report|work|None"),
    ("Add by the end of the week finish slides to my work list.", "task.add", "by the end of the week finish slides|work|None"),
    ("Add by mayonnaise to my shopping list.", "task.add", "buy mayonnaise|shopping|None"),
    ("Add pay rent to my personal list by tomorrow.", "task.add", "pay rent|personal|tomorrow"),
    ("Remind me to buy milk by today.", "task.add", "buy milk|personal|today"),
    ("Add by milk to my personal list by today.", "task.add", "buy milk|personal|today"),
    ("Add pay rent to my personal list but tomorrow.", None, ""),
    # a default-list or remind title that still names a list is refused, not written into Personal
    ("Add call the dentist to my work list next week.", None, ""),
    ("Remind me to call the dentist to my work list next week.", None, ""),
    ("Add finish report to work list next week.", None, ""),
    ("Add drive to work tomorrow morning.", "task.add", "drive to work tomorrow morning|personal|None"),
    ("Add my passport photos to my personal list.", "task.add", "my passport photos|personal|None"),
    # F2 review: P_ADD's verb is optional and P_ADD runs first, so a question, a completion or a remind skips it
    ("What do I have on my work list by tomorrow?", "schedule.tomorrow", ""),
    ("What's next on my work list by tomorrow?", "next.event", ""),
    ("What is on my personal list by tomorrow?", "schedule.tomorrow", ""),
    ("Hey Jarvis, what do I have on my personal list by tomorrow", "schedule.tomorrow", ""),
    ("I finished the report for work by today.", "task.complete", "the report for work by today"),
    ("Tick off call mom on my personal list by today.", "task.complete", "call mom on my personal list by today"),
    ("Remind me to email the slides to work by tomorrow.", "task.add", "email the slides to work|personal|tomorrow"),
    ("What's on my work list for tomorrow?", "schedule.tomorrow", ""),
    ("What's next on my work list?", "next.event", ""),
    ("Remind me to go to work tomorrow.", "task.add", "go to work|personal|tomorrow"),
    ("Hey Jarvis, what's due for work by tomorrow?", "schedule.tomorrow", ""),
    ("Hey Jarvis, done with the report for work by tomorrow.", "task.complete", "the report for work by tomorrow"),
    ("Hey Jarvis, what do I need to do for work by tomorrow?", None, ""),
    ("Hey Jarvis, is there anything on my work list for tomorrow?", None, ""),
    ("Hey Jarvis, did I add the report to my work list?", None, ""),
    ("Hey Jarvis, and what's on my work list by tomorrow?", "schedule.tomorrow", ""),
    # ... but a spoken add verb still adds, and a bare check / a command head after a misheard add is a title
    ("Add what to pack to my personal list.", "task.add", "what to pack|personal|None"),
    ("And finish the report to my work list.", "task.add", "finish the report|work|None"),
    # no add verb, no write (all 18 verbless matches on the F2 audio were wrong titles): rephrase with "add"
    ("Hey Jarvis, check the oil on my work list.", None, ""),
    ("Hey Jarvis, buy milk to my personal list.", None, ""),
    ("Hey Jarvis, can you tell me what's on my work list?", None, ""),
    ("Hey Jarvis, I already did the report on my work list.", None, ""),
    # "by today/tomorrow" closes P_ADD only after a spoken add verb (add or a mishearing of it)
    ("Hey Jarvis, pay rent to my personal list by tomorrow", None, ""),
    ("At the rent to my personal list by tomorrow.", "task.add", "the rent|personal|tomorrow"),
    # the list-phrase guard needs a preposition, a list word and a list noun, so these titles write again
    ("Remind me to check the shopping list tomorrow.", "task.add", "check the shopping list|personal|tomorrow"),
    ("Remind me to update my work tasks tomorrow.", "task.add", "update my work tasks|personal|tomorrow"),
    ("Remind me to print the grocery list today.", "task.add", "print the grocery list|personal|today"),
    ("Remind me to send the slides to my work email.", "task.add", "send the slides to my work email|personal|None"),
    ("Remind me to forward the receipt to my personal email.", "task.add",
     "forward the receipt to my personal email|personal|None"),
    ("Remind me to put the charger in my work bag.", "task.add", "put the charger in my work bag|personal|None"),
    ("Add send the photos to my personal email.", "task.add", "send the photos to my personal email|personal|None"),
    ("Add read a book in my personal time.", "task.add", "read a book in my personal time|personal|None"),
    ("Add bring laptop to the work meeting.", "task.add", "bring laptop to the work meeting|personal|None"),
    ("Add go to the shopping mall.", "task.add", "go to the shopping mall|personal|None"),
    ("Add review my worklist.", "task.add", "review my worklist|personal|None"),
    # ... and these still name a list, so nothing is written
    ("Add milk to my shopping list please.", None, ""),
    ("Add call the dentist to my worklist next week.", None, ""),
    ("Remind me to call mom on my work list.", None, ""),
]
# F2 review grid: question and completion openers x list phrases x due forms, said after the name, never a task.add
NEVER_ADD_OPEN = ["what's", "what's due", "what is", "what do I have", "what do I need to do", "which tasks are",
                  "how many tasks are", "is there anything", "anything", "did I add the report", "I finished the report",
                  "I did the slides", "done with the report", "finish the report", "tick off call mom",
                  "check off the invoice", "mark off milk", "and what's"]
NEVER_ADD_LIST = ["on my work list", "for work", "to my personal list", "on the shopping list", "in my work tasks"]
NEVER_ADD_DUE = [" by today", " by tomorrow", " for tomorrow", " tomorrow", ""]


def main() -> int:
    ok = 0
    for heard, want, slot in cases:
        wake_audio = "travis" not in heard.lower() and heard not in ("You", "Thank you.")
        rest, wake = strip_wake(heard, wake_audio=wake_audio)
        r = match(rest)
        got = r["intent"]
        if got == "task.add":
            s = f"{r['title']}|{r['list']}|{r['due']}"
        elif got == "task.complete":
            s = r["query"]
        elif got == "theme":
            s = r["value"]
        else:
            s = ""
        good = (got == want) and (s == slot)
        ok += good
        print(f"{'PASS' if good else 'FAIL'} wake_text={str(wake):5s} {heard!r:66s} -> {got} {s!r}")
    print(f"{ok}/{len(cases)} pass")
    tasks = [{"title": t, "id": str(i), "tl": "L", "list": "PERSONAL"} for i, t in enumerate(
        ["Buy milk", "Call the dentist", "Renew passport", "Tax return 2026", "Buy milk powder for Ema", "Book car service"])]
    want_pick = {"buy milk": ("ok", "Buy milk"), "by milke": ("ok", "Buy milk"), "the dentist task": ("ok", "Call the dentist"),
                 "passport": ("ok", "Renew passport"), "car": ("none", None), "milk": ("ambiguous", None)}
    pick_ok = 0
    for q, (status, title) in want_pick.items():
        r = best_task(q, tasks)
        good = r["status"] == status and (title is None or r["task"]["title"] == title)
        pick_ok += good
        print(f"  {'PASS' if good else 'FAIL'} complete {q!r:20s} -> {r}")
    print(f"best_task {pick_ok}/{len(want_pick)} pass")
    # fix_buy on norm()ed titles: the accuracy-first judge's typed probes (None = left as it is)
    want_fix = {"by milk": "buy milk", "bye bread": "buy bread", "by mayo": "buy mayo", "by thistle seed": "buy thistle seed",
                "by the tickets": "buy the tickets", "by two lemons": "buy two lemons", "by a birthday card": "buy a birthday card",
                "by friday send the invoice": None, "by 5 pm call mom": None, "by two pm call mom": None,
                "by the 15th file taxes": None, "by end of day send report": None, "by may renew passport": None,
                "by the weekend clean garage": None, "bi weekly report": None, "byte budget": None, "by": None}
    fix_ok = 0
    for q, want in want_fix.items():
        got = fix_buy(q)
        good = got == (want or q)
        fix_ok += good
        print(f"  {'PASS' if good else 'FAIL'} fix_buy {q!r:30s} -> {got!r}")
    print(f"fix_buy {fix_ok}/{len(want_fix)} pass")
    grid = [f"Hey Jarvis, {o} {lst}{due}?" for o in NEVER_ADD_OPEN for lst in NEVER_ADD_LIST for due in NEVER_ADD_DUE]
    bad = [(t, r) for t in grid for r in [match(strip_wake(t, wake_audio=True)[0])] if r["intent"] == "task.add"]
    for t, r in bad:
        print(f"  FAIL never_add {t!r} -> {r}")
    print(f"never_add {len(grid) - len(bad)}/{len(grid)} pass")
    return 0 if ok == len(cases) and pick_ok == len(want_pick) and fix_ok == len(want_fix) and not bad else 1


if __name__ == "__main__":
    sys.exit(main())
