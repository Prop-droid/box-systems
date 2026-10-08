# laya

Open-source Jev (TypeSafe's typed-decision model). Laya v0.3.28, Apache-2.0, ModernBERT ~400M
on CPU. Serves the Jev wire protocol `/v1/systemone` on 127.0.0.1:8095 via `laya.service`.
It loads lazily and unloads after 15 min idle. About 2 GB resident, 5 s cold, 0.5 s per warm yes/no question.

- Client: `~/systems/lib/decide.py` (stdlib only). `yes()`/`choose()` return None when unsure
  or down, so the job escalates to Claude. Pattern: Laya = System 1 gate, Claude = System 2.
- Test: `python3 ~/systems/lib/decide.py "<text>" "<yes/no question>"`
- Health: `curl -s localhost:8095/health`

## Measured 2026-10-06 (zero-shot vs mechanism-tagger Haiku labels)

- Full 23-device prompt, long instructions: P 0.15 / R 1.00. It says yes to everything. Unusable.
- 8 concrete devices, short questions (`eval_crisp.py 30`): micro F1 0.57, 5.1 s/item.
  stat P 0.90, taste F1 0.76, urgency F1 0.77. callout/authority 0.
- Verdict: zero-shot is fine for crisp, single yes/no gates. It does NOT replace an LLM tagger.
  For nuanced labels, fine-tune on our own labels first:
  `laya-train --data <jsonl> --base convaiinnovations/laya --out ft/<name>` (README claims 0.36 -> 0.77).

## Wired in

- comments-digest (2026-10-06): `flag_comments.py` asks 4 yes/no flags per comment and sorts each into 3 bands:
  AUTO >= 0.80 is counted, REVIEW 0.55-0.80 goes to Claude to confirm, the rest is dropped.
  Subscription and price are first narrowed by a keyword shortlist: alone, Laya scored "Sucralose is a hard pass" 1.00.
  On 398 real comments, 46 of 50 AUTO flags were correct (Laya alone: 45 of 58). A run takes about 10 min.
