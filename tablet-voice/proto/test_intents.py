import sys; sys.path.insert(0, sys.argv[1])
from intents import strip_wake, match, best_task
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
]
ok = 0
for heard, want, slot in cases:
    rest, wake = strip_wake(heard, wake_audio=("travis" not in heard.lower() and heard not in ("You","Thank you."))); r = match(rest)
    got = r["intent"]
    if got == "task.add": s = f"{r['title']}|{r['list']}|{r['due']}"
    elif got == "task.complete": s = r["query"]
    elif got == "theme": s = r["value"]
    else: s = ""
    good = (got == want) and (s == slot)
    ok += good
    print(f"{'PASS' if good else 'FAIL'} wake_text={str(wake):5s} {heard!r:66s} -> {got} {s!r}")
print(f"{ok}/{len(cases)} pass")
tasks = [{"title": t, "id": str(i), "tl": "L", "list": "PERSONAL"} for i, t in enumerate(
    ["Buy milk", "Call the dentist", "Renew passport", "Tax return 2026", "Buy milk powder for Ema", "Book car service"])]
for q in ["buy milk", "by milke", "the dentist task", "the tax return", "passport", "car", "milk"]:
    print(f"  complete {q!r:20s} -> {best_task(q, tasks)}")
