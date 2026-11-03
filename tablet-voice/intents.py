"""intents.py: Tier 0 intent matcher for tablet-voice (regex plus fuzzy rules, no LLM, English only).

norm, lev, strip_wake (14d 6e), match (14d 7b, rules in that order) and best_task (14d 7c: act only at
score >= 0.72 with a lead >= 0.08). Logic copied unchanged from the validated prototype (proto/intents.py).
"""
import re
from difflib import SequenceMatcher

def norm(t: str) -> str:
    t = t.lower().replace("’", "'")
    t = re.sub(r"[^\w\s']", " ", t)            # punctuation -> space (keeps apostrophes)
    return re.sub(r"\s+", " ", t).strip()

def lev(a: str, b: str) -> int:
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]

WAKE_LEAD = {"hey", "hi", "hay", "a", "okay", "ok", "oh", "they", "he", "yo"}
# tokens that can start a Tier 0 command (incl. Whisper mis-hearings of "add"); never stripped as wake residue
CMD_START = {"add", "and", "at", "ad", "ed", "had", "put", "create", "please", "mark", "tick", "check", "cross",
             "complete", "finish", "i", "done", "what", "what's", "whats", "next", "turn", "switch", "dark", "light",
             "night", "auto", "remind", "tomorrow", "tomorrow's", "never", "nevermind", "cancel", "stop", "the", "my"}
def strip_wake(text: str, wake_audio: bool = False, max_tokens: int = 5):
    """Drop a leading wake phrase. wake_audio=True when the box re-check (openWakeWord) says the phrase is
    in the audio, so unreadable residue like 'they jar this' / 'h r v s' may be dropped up to the first
    command word. Returns (rest, wake_text_found)."""
    toks = norm(text).split()
    for i, tok in enumerate(toks[:max_tokens]):
        if lev(tok, "jarvis") <= 1:                 # jarvis, jervis, jarvi, garvis; NOT travis (distance 3)
            return " ".join(toks[i + 1:]), True
    for n in range(2, max_tokens + 1):              # "hey jarvis" heard as one blob, e.g. "heyjarvis"
        blob = "".join(toks[:n])
        if 1 - lev(blob, "heyjarvis") / max(len(blob), 9) >= 0.75:
            return " ".join(toks[n:]), True
    k = 0
    if wake_audio:
        while k < min(max_tokens, len(toks) - 1) and toks[k] not in CMD_START:
            k += 1
    elif toks[:1] and toks[0] in WAKE_LEAD:
        k = 1
    return " ".join(toks[k:]), False

LIST = r"(?P<list>personal|work|shopping|grocery|groceries)"
P_ADD = re.compile(
    r"^(?:please\s+)?(?:(?:add|and|at|ad|ed|had|put|create)\s+)?(?:a\s+task\s+)?(?P<title>.+?)\s+"
    r"(?:to|on|onto|in|into|for)\s+(?:the\s+|my\s+)?" + LIST + r"\s*(?:list|tasks?|to\s?do(?:\s+list)?)?"
    r"(?:\s+(?:for\s+|due\s+)?(?P<due>today|tomorrow))?$")
P_ADD_DEFAULT = re.compile(r"^(?:add|put|create)\s+(?:a\s+task\s+)?(?P<title>.+?)(?:\s+(?:for\s+|due\s+)?(?P<due>today|tomorrow))?$")
P_REMIND = re.compile(r"^remind me to\s+(?P<title>.+?)(?:\s+(?P<due>today|tomorrow))?$")
P_DONE = [
    re.compile(r"^(?:mark|tick|check|cross)\s+(?:off\s+)?(?P<title>.+?)\s+(?:as\s+|has\s+|is\s+)?(?:done|complete|completed|finished)$"),
    re.compile(r"^(?:tick|check|cross)\s+off\s+(?P<title>.+)$"),
    re.compile(r"^(?:complete|finish|i finished|i did|i've done|done with)\s+(?P<title>.+)$"),
    re.compile(r"^(?P<title>.+?)\s+(?:is|are)\s+(?:done|finished|complete)$"),
]
P_NEXT = re.compile(r"\b(?:what'?s|what is|whats)\s+next\b|\bnext\s+(?:event|meeting|appointment|thing)\b|"
                    r"\bwhat do i have next\b|\bwhat'?s coming up\b|\bwhat is coming up\b")
P_TOMORROW = re.compile(r"\btomorrow'?s?\s+(?:schedule|calendar|plan|agenda|events?|meetings?)\b|"
                        r"\b(?:schedule|calendar|agenda|plan|events?)\b.*\btomorrow\b|"
                        r"\bwhat(?:'s| is| do i have)\b.*\btomorrow\b")
P_THEME = re.compile(r"\b(?:(?P<off>turn off|disable)\s+)?(?P<mode>dark|night|light|bright|day|auto|automatic)\s*(?:mode|theme)\b")
P_CANCEL = re.compile(r"^(?:never ?mind|cancel|stop|nothing|forget it)$")

def match(text: str) -> dict:
    """text = transcript AFTER strip_wake. Returns {'intent': ..., slots...} or {'intent': None}."""
    t = norm(text)
    if not t:
        return {"intent": None}
    if P_CANCEL.match(t):
        return {"intent": "cancel"}
    m = P_ADD.match(t)
    if m and len(m.group("title")) >= 2:
        lst = {"grocery": "shopping", "groceries": "shopping"}.get(m.group("list"), m.group("list"))
        return {"intent": "task.add", "title": m.group("title"), "list": lst, "due": m.group("due")}
    for p in P_DONE:
        m = p.match(t)
        if m:
            return {"intent": "task.complete", "query": m.group("title")}
    m = P_THEME.search(t)
    if m:
        mode = {"night": "dark", "bright": "light", "day": "light", "automatic": "auto"}.get(m.group("mode"), m.group("mode"))
        if m.group("off") and mode == "dark":
            mode = "light"
        return {"intent": "theme", "value": mode}
    if P_NEXT.search(t):
        return {"intent": "next.event"}
    if P_TOMORROW.search(t):
        return {"intent": "schedule.tomorrow"}
    m = P_REMIND.match(t)
    if m:
        return {"intent": "task.add", "title": m.group("title"), "list": "personal", "due": m.group("due")}
    m = P_ADD_DEFAULT.match(t)
    if m and len(m.group("title")) >= 2:
        return {"intent": "task.add", "title": m.group("title"), "list": "personal", "due": m.group("due")}
    return {"intent": None}

def best_task(query: str, tasks: list) -> dict:
    """Fuzzy-pick one task. tasks = [{'title','id','tl','list'}]. Conservative: no undo endpoint exists."""
    q = norm(query)
    q = re.sub(r"^(?:the|my|a)\s+", "", q); q = re.sub(r"\s+(?:task|item|one)$", "", q)
    qs = [w for w in q.split() if len(w) >= 4 or len(q.split()) > 1]
    scored = []
    for tk in tasks:
        t = norm(tk["title"])
        if t == q:
            scored.append((1.0, tk)); continue
        r = SequenceMatcher(None, q, t).ratio()
        ts = set(t.split())
        cont = 0.9 * sum(w in ts for w in qs) / len(qs) if qs else 0.0   # spoken words found in the title
        scored.append((max(r, cont), tk))
    scored.sort(key=lambda x: -x[0])
    if not scored or scored[0][0] < 0.72:
        return {"status": "none", "best": scored[0][1]["title"] if scored else None,
                "score": round(scored[0][0], 2) if scored else 0}
    if len(scored) > 1 and scored[0][0] - scored[1][0] < 0.08:
        return {"status": "ambiguous", "options": [x[1]["title"] for x in scored[:2]]}
    return {"status": "ok", "task": scored[0][1], "score": round(scored[0][0], 2)}


# Intent classes used by the server's decision table (spec 14 V4, section 0 item 11).
WRITE_INTENTS = frozenset({"task.add", "task.complete"})
READ_INTENTS = frozenset({"next.event", "schedule.tomorrow", "theme", "cancel"})
