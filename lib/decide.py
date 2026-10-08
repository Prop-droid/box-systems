#!/usr/bin/env python3
"""System-1 gate: ask the local Laya server (laya.service, open-source Jev) a typed question.

Stdlib only, so any ~/systems job can import it. Returns the decision, or None when the
server is down or the answer falls under the confidence floor -- the caller then escalates
to Claude (System 2). Never raises on transport errors: a gate must not break its job.

    sys.path.insert(0, os.path.expanduser("~/systems/lib")); from decide import yes, choose
    if yes(text, "Does the user correct the agent's behavior?", floor=0.85) is False: skip()

CLI: decide.py "<text>" "<yes/no question>"   -> prints probability or "abstain"
"""
import json
import os
import sys
import urllib.request

URL = os.environ.get("LAYA_URL", "http://127.0.0.1:8095/v1/systemone")
TIMEOUT = float(os.environ.get("LAYA_TIMEOUT", "90"))


def ask(state: str, questions: dict) -> dict | None:
    """Raw /v1/systemone call. questions = Jev-style {id: {type, instructions, criteria?}}."""
    body = json.dumps({"state": state, "questions": questions}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return json.load(r).get("answers")
    except Exception as e:  # server down, cold-load timeout, 4xx/5xx
        print(f"decide: laya unavailable ({e.__class__.__name__}), escalate", file=sys.stderr)
        return None


def ask_batch(states: list[str], questions: dict, chunk: int = 64) -> list[dict] | None:
    """Same questions over many states (server caps a batch at 64). None if any chunk fails."""
    out = []
    for i in range(0, len(states), chunk):
        body = json.dumps({"states": states[i:i + chunk], "questions": questions}).encode()
        req = urllib.request.Request(URL + "/batch", data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT * 10) as r:
                out += [x["answers"] for x in json.load(r)["results"]]
        except Exception as e:
            print(f"decide: laya batch failed at {i} ({e.__class__.__name__}), escalate", file=sys.stderr)
            return None
    return out


def prob(state: str, question: str) -> float | None:
    """P(yes) for a yes/no question, or None if Laya is unavailable."""
    a = ask(state, {"q": {"type": "noul", "instructions": question}})
    return None if a is None else float(a["q"]["noul"])


def yes(state: str, question: str, floor: float = 0.85) -> bool | None:
    """True/False only when P(yes) or P(no) clears `floor`; None = not sure, ask Claude."""
    p = prob(state, question)
    if p is None:
        return None
    return True if p >= floor else False if p <= 1 - floor else None


def choose(state: str, question: str, options: dict[str, str], floor: float = 0.7) -> str | None:
    """Pick one key of `options` ({label: description}); None when unsure or unavailable."""
    a = ask(state, {"q": {"type": "choice", "instructions": question, "criteria": options}})
    if a is None:
        return None
    ans = a["q"]
    conf = ans.get("answer_confidence", ans.get("confidence", 1.0))
    return ans["choice"] if conf is not None and conf >= floor else None


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    p = prob(sys.argv[1], sys.argv[2])
    print("abstain" if p is None else f"{p:.3f}")
