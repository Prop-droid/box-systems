"""intents.py: Tier 0 intent matcher for tablet-voice (regex plus fuzzy rules, no LLM, English only).

norm, lev, strip_wake (14d 6e), match (14d 7b, rules in that order) and best_task (14d 7c: act only at
score >= 0.72 with a lead >= 0.08). Started as the validated prototype (proto/intents.py, left as it was); the
F2 buy/by fix (2026-11-04, ~/personal/tablet-upgrade/reports/voice-build/f2-buyby) changed match(): fix_buy on every
task.add title, "by" as a due marker before today/tomorrow, P_ADD only with a spoken add verb (or a mishearing
of it) and never for text that starts like a question or another command (P_NOT_ADD), and no write when a
default-list or remind title still names a list.
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
    r"^(?:please\s+)?(?:(?P<verb>add|and|at|ad|ed|had|put|create)\s+)?(?:a\s+task\s+)?(?P<title>.+?)\s+"
    r"(?:to|on|onto|in|into|for)\s+(?:the\s+|my\s+)?" + LIST + r"\s*(?:list|tasks?|to\s?do(?:\s+list)?)?"
    r"(?:\s+(?:for\s+|due\s+|(?P<by>by)\s+)?(?P<due>today|tomorrow))?$")
# P_ADD's verb is optional and P_ADD runs first, so text that starts like a question (also after a misheard add), a
# completion or a remind skips it and reaches its own rule: "what's on my work list for tomorrow" is a read, not an add.
P_NOT_ADD = re.compile(r"(?:(?:and|at|ad|ed|had)\s+)?(?:what(?:'?s)?|which|when|where|who|why|how|is|are|do (?:i|we|you)|"
                       r"does|did|any(?:thing)?|i(?:'ve| have)? (?:finished|completed|done|did)|i'm done|i am done|done|"
                       r"(?:mark|tick|check|cross) off)\b|(?:remind me to|complete|finish)\b|"
                       r"(?:mark|tick|check|cross)\s+.+?\s+(?:as\s+)?(?:done|complete|completed|finished)\b")
P_ADD_DEFAULT = re.compile(r"^(?:add|put|create)\s+(?:a\s+task\s+)?(?P<title>.+?)(?:\s+(?:for\s+|due\s+|by\s+)?(?P<due>today|tomorrow))?$")
P_REMIND = re.compile(r"^remind me to\s+(?P<title>.+?)(?:\s+(?:by\s+)?(?P<due>today|tomorrow))?$")
# P_ADD missed, yet the title still names a list ("call the dentist to my work list next week"): refuse, never
# write that whole phrase into Personal. It needs the preposition and a list noun, so "drive to work tomorrow",
# "send the slides to my work email" and "check the shopping list" still write.
P_LIST_PHRASE = re.compile(r"\b(?:to|on|onto|in|into|for)\s+(?:the\s+|my\s+)?(?:personal|work|shopping|grocery|groceries)"
                           r"\s*(?:list|tasks?|to\s?do)\b")
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
# F2: Whisper hears "add buy milk" as "add by milk". A leading by/bye becomes buy unless a deadline follows. No "bi":
# it never fired on audio, and norm() turns "bi-weekly" into "bi weekly". Regex: the accuracy-first judge's, as given.
RULE_A = re.compile(r"^(?:by|bye)\s+(?!(?:today|tonight|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|"
                    r"sunday|next|this|noon|midnight|midday|morning|afternoon|evening|lunchtime|bedtime|weekend|eod|"
                    r"eow|then|later|now|soon|january|february|march|april|may|june|july|august|september|october|"
                    r"november|december|(?:end|close)\s+of|the\s+(?:end|weekend|time|morning|afternoon|evening|"
                    r"first|second|third|twenty|thirty|\w*(?:fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|"
                    r"twelfth|teenth|tieth))|(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|"
                    r"twelve)\s+(?:am|pm|a\s?m|p\s?m|o'?clock|thirty|fifteen|forty|oh))\b|the\s+\d|\d)\S")


def fix_buy(title: str) -> str:
    """task.add titles only (norm form): "by milk" -> "buy milk"; "by friday send the invoice" stays."""
    return re.sub(r"^\S+", "buy", title, count=1) if RULE_A.match(title) else title


def match(text: str) -> dict:
    """text = transcript AFTER strip_wake. Returns {'intent': ..., slots...} or {'intent': None}."""
    t = norm(text)
    if not t:
        return {"intent": None}
    if P_CANCEL.match(t):
        return {"intent": "cancel"}
    m = None if P_NOT_ADD.match(t) else P_ADD.match(t)
    # A write needs the add verb (or a mishearing of it): on the F2 audio all 18 verbless matches were wrong titles
    # ("goodbye milk", "i'd be rent"), and verbless text naming a list is mostly a question or a completion.
    if m and m.group("verb") and len(m.group("title")) >= 2:
        lst = {"grocery": "shopping", "groceries": "shopping"}.get(m.group("list"), m.group("list"))
        return {"intent": "task.add", "title": fix_buy(m.group("title")), "list": lst, "due": m.group("due")}
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
        if P_LIST_PHRASE.search(m.group("title")):
            return {"intent": None}
        return {"intent": "task.add", "title": fix_buy(m.group("title")), "list": "personal", "due": m.group("due")}
    m = P_ADD_DEFAULT.match(t)
    if m and len(m.group("title")) >= 2:
        if P_LIST_PHRASE.search(m.group("title")):
            return {"intent": None}
        return {"intent": "task.add", "title": fix_buy(m.group("title")), "list": "personal", "due": m.group("due")}
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


# Intent classes used by the server's decision table (spec 14 V4, section 0 item 11). "answer" comes only from the
# Opus layer (spec 16, llm.py); server.decide() also gives it the wake-text rule.
WRITE_INTENTS = frozenset({"task.add", "task.complete"})
READ_INTENTS = frozenset({"next.event", "schedule.tomorrow", "theme", "cancel", "answer"})
