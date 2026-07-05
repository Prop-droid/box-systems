# SHA Creative Strategist — Convention Lint (dry run)

- **Run:** 2026-07-03, report-only (`AUTOFILL_LINT=1 python3 autofill.py`), zero writes to ClickUp
- **List:** Shameless Snacks > Creative Marketing > Tomas | Creative Strategist (`901110066469`)
- **Scope:** 266 parent tasks in statuses ['to do', 'in progress', 'cs review', 'approved', 'sent to mb'], updated in last 30d (same fetch as autofill: parents only, no ClickBot, subtasks excluded)
- **Classes:** launch 212, brief 52 (research/brief/admin — name+default checks skipped), freeform 2
- **Result:** 309 violations (59 fail, 250 warn) across 214 tasks
- **By check:** `defaults`=210, `req-fields`=57, `name`=24, `em-dash`=13, `list`=5

## What each check means

| Check | Sev | Rule |
|-------|-----|------|
| `name` | fail/warn | SHA naming canon: `SHA_<yyyy>_S##_..._Tom` structure (year/sprint/owner) + a canon angle token present somewhere in the name. Angle canon sourced from `feedback_sha_task_angle_canon_naming.md` + `brain/wiki/shameless/creative-strategy/creative-angles.md` (15 canonical angles). WL creator tasks exempt from the angle rule. |
| `req-fields` | fail | Required custom fields empty for the task's type+status. Always: Brand, Product, Deliverable Type, Responsible. At `cs review`/`approved`/`sent to mb` also: FB Page, Headline, Text, LP (LP skipped when on LP_HOLD). |
| `defaults` | warn | Launch-task defaults (`feedback_launch_task_defaults.md`): assignee = Alejandra (114210317), priority = high, time estimate = 8h video / 3h image. |
| `list` | warn | Description contains a markdown ordered list (ClickUp ordered-list collapse bug — flag only). |
| `em-dash` | warn | Em/en dash present in a copy-facing field (Headline, Text, or task name). Brand rule: no em dashes in FB copy. |

## `defaults` — 210

| Task | Type | Status | Sev | Detail |
|------|------|--------|-----|--------|
| SH-12878 | video | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-13681 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-14895 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-15456 | image | approved | warn | assignee != Alejandra; priority=normal (want high); estimate=4h (want 3h) |
| SH-15512 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-15514 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high); estimate=4h (want 3h) |
| SH-15598 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-15680 | image | approved | warn | assignee != Alejandra; priority=normal (want high) |
| SH-15686 | video | to do | warn | assignee != Alejandra; priority=low (want high) |
| SH-15693 | image | approved | warn | assignee != Alejandra; priority=normal (want high) |
| SH-15783 | image | cs review | warn | priority=normal (want high) |
| SH-15934 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-15961 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-15962 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high); estimate=3h (want 3h) |
| SH-15965 | image | in progress | warn | assignee != Alejandra; priority=normal (want high); estimate=3h (want 3h) |
| SH-15966 | image | approved | warn | assignee != Alejandra; priority=normal (want high) |
| SH-15970 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high); estimate=3h (want 3h) |
| SH-16033 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16034 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16035 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16036 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16037 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16038 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16039 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16040 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16041 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16131 | image | sent to mb | warn | assignee != Alejandra; priority=none (want high); estimate=1h (want 3h) |
| SH-16179 | video | sent to mb | warn | assignee != Alejandra; estimate=1h (want 8h) |
| SH-16185 | video | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16192 | video | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16204 | video | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16208 | video | sent to mb | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 8h) |
| SH-16212 | video | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16298 | video | cs review | warn | assignee != Alejandra; estimate=10h (want 8h) |
| SH-16304 | video | to do | warn | assignee != Alejandra |
| SH-16308 | video | to do | warn | assignee != Alejandra |
| SH-16310 | video | sent to mb | warn | assignee != Alejandra |
| SH-16313 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16315 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16316 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16317 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16318 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16319 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16320 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16321 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16323 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16324 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16325 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16326 | image | cs review | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16328 | video | to do | warn | assignee != Alejandra |
| SH-16331 | video | to do | warn | assignee != Alejandra |
| SH-16332 | video | cs review | warn | assignee != Alejandra; estimate=11h (want 8h) |
| SH-16338 | video | to do | warn | assignee != Alejandra |
| SH-16348 | video | to do | warn | assignee != Alejandra |
| SH-16350 | video | sent to mb | warn | assignee != Alejandra |
| SH-16352 | video | in progress | warn | assignee != Alejandra |
| SH-16354 | video | in progress | warn | assignee != Alejandra |
| SH-16356 | video | in progress | warn | assignee != Alejandra |
| SH-16361 | video | cs review | warn | assignee != Alejandra |
| SH-16362 | video | sent to mb | warn | assignee != Alejandra |
| SH-16363 | video | in progress | warn | assignee != Alejandra |
| SH-16367 | video | in progress | warn | assignee != Alejandra |
| SH-16368 | video | to do | warn | assignee != Alejandra |
| SH-16369 | video | to do | warn | assignee != Alejandra |
| SH-16372 | video | in progress | warn | assignee != Alejandra |
| SH-16374 | video | cs review | warn | assignee != Alejandra |
| SH-16376 | video | to do | warn | assignee != Alejandra |
| SH-16378 | video | to do | warn | assignee != Alejandra |
| SH-16380 | video | to do | warn | assignee != Alejandra |
| SH-16382 | video | to do | warn | assignee != Alejandra |
| SH-16384 | video | to do | warn | assignee != Alejandra |
| SH-16386 | video | to do | warn | assignee != Alejandra |
| SH-16388 | video | to do | warn | assignee != Alejandra |
| SH-16391 | video | to do | warn | assignee != Alejandra |
| SH-16393 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16394 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16395 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16396 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16401 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16419 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16420 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16421 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16422 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16423 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16424 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16425 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16426 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16427 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16428 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16429 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16430 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16431 | video | sent to mb | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 8h) |
| SH-16439 | video | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16443 | video | cs review | warn | assignee != Alejandra; priority=normal (want high); estimate=5h (want 8h) |
| SH-16446 | video | in progress | warn | assignee != Alejandra; priority=normal (want high); estimate=12h (want 8h) |
| SH-16452 | image | sent to mb | warn | assignee != Alejandra |
| SH-16456 | image | sent to mb | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16462 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16463 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16464 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16465 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16466 | video | to do | warn | assignee != Alejandra; priority=low (want high); estimate=4h (want 8h) |
| SH-16476 | video | to do | warn | assignee != Alejandra |
| SH-16477 | video | to do | warn | assignee != Alejandra |
| SH-16478 | video | cs review | warn | assignee != Alejandra |
| SH-16479 | video | sent to mb | warn | assignee != Alejandra; estimate=1h (want 8h) |
| SH-16480 | video | to do | warn | assignee != Alejandra |
| SH-16483 | video | to do | warn | assignee != Alejandra |
| SH-16484 | video | to do | warn | assignee != Alejandra |
| SH-16485 | video | to do | warn | assignee != Alejandra |
| SH-16486 | image | in progress | warn | assignee != Alejandra |
| SH-16489 | image | sent to mb | warn | assignee != Alejandra |
| SH-16490 | image | in progress | warn | assignee != Alejandra |
| SH-16515 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16516 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16517 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16518 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16521 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16522 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16523 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16524 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16525 | image | approved | warn | assignee != Alejandra |
| SH-16526 | image | approved | warn | assignee != Alejandra |
| SH-16527 | image | approved | warn | assignee != Alejandra |
| SH-16528 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16529 | video | to do | warn | assignee != Alejandra |
| SH-16530 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16531 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16532 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16533 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16534 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16535 | image | in progress | warn | assignee != Alejandra |
| SH-16536 | image | to do | warn | assignee != Alejandra |
| SH-16537 | image | to do | warn | assignee != Alejandra |
| SH-16538 | image | to do | warn | assignee != Alejandra; priority=urgent (want high); estimate=none (want 3h) |
| SH-16540 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16541 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16542 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16543 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16544 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16545 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16546 | image | to do | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16547 | video | to do | warn | assignee != Alejandra |
| SH-16553 | video | to do | warn | assignee != Alejandra |
| SH-16554 | video | in progress | warn | assignee != Alejandra |
| SH-16587 | video | to do | warn | priority=none (want high) |
| SH-16592 | image | approved | warn | assignee != Alejandra; priority=normal (want high) |
| SH-16595 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16601 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16602 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16603 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16604 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16615 | video | in progress | warn | assignee != Alejandra; priority=urgent (want high) |
| SH-16616 | video | to do | warn | assignee != Alejandra; priority=urgent (want high) |
| SH-16645 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16646 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16647 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16648 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16649 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16650 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16651 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16652 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16653 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16654 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16655 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16656 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16657 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16658 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16659 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16660 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16661 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16662 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16663 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16664 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16665 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16666 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16667 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16668 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16669 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16670 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16671 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16672 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16673 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16674 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16675 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16676 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16677 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16678 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16679 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16680 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16681 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16682 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16683 | image | to do | warn | assignee != Alejandra; priority=normal (want high); estimate=none (want 3h) |
| SH-16684 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16685 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16686 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16687 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16688 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16689 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16690 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16691 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16692 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16693 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16694 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16695 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16696 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16697 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16698 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-16699 | image | to do | warn | assignee != Alejandra; priority=none (want high); estimate=none (want 3h) |
| SH-379 | video | to do | warn | priority=none (want high) |

## `req-fields` — 57

| Task | Type | Status | Sev | Detail |
|------|------|--------|-----|--------|
| SH-16033 | image | to do | fail | empty: brand, product, deliv_type, responsible |
| SH-16034 | image | to do | fail | empty: brand, product, deliv_type, responsible |
| SH-16035 | image | to do | fail | empty: brand, product, deliv_type, responsible |
| SH-16036 | image | to do | fail | empty: brand, product, deliv_type, responsible |
| SH-16037 | image | to do | fail | empty: brand, product, deliv_type, responsible |
| SH-16038 | image | to do | fail | empty: brand, product, deliv_type, responsible |
| SH-16039 | image | to do | fail | empty: brand, product, deliv_type, responsible |
| SH-16040 | image | to do | fail | empty: brand, product, deliv_type, responsible |
| SH-16041 | image | to do | fail | empty: brand, product, deliv_type, responsible |
| SH-16344 | video | to do | fail | empty: responsible |
| SH-16396 | image | sent to mb | fail | empty: fb_page, headline, text, lp |
| SH-16419 | image | sent to mb | fail | empty: product |
| SH-16420 | image | sent to mb | fail | empty: product |
| SH-16421 | image | sent to mb | fail | empty: product |
| SH-16422 | image | sent to mb | fail | empty: product |
| SH-16423 | image | sent to mb | fail | empty: product |
| SH-16424 | image | sent to mb | fail | empty: product |
| SH-16425 | image | sent to mb | fail | empty: product |
| SH-16426 | image | sent to mb | fail | empty: product |
| SH-16427 | image | sent to mb | fail | empty: product |
| SH-16428 | image | sent to mb | fail | empty: product |
| SH-16429 | image | sent to mb | fail | empty: product |
| SH-16430 | image | sent to mb | fail | empty: product |
| SH-16443 | video | cs review | fail | empty: fb_page, headline, text, lp |
| SH-16452 | image | sent to mb | fail | empty: product |
| SH-16456 | image | sent to mb | fail | empty: product |
| SH-16462 | image | to do | fail | empty: product |
| SH-16463 | image | to do | fail | empty: product |
| SH-16464 | image | to do | fail | empty: product |
| SH-16465 | image | to do | fail | empty: product |
| SH-16476 | video | to do | fail | empty: product |
| SH-16477 | video | to do | fail | empty: product |
| SH-16478 | video | cs review | fail | empty: product |
| SH-16479 | video | sent to mb | fail | empty: product |
| SH-16480 | video | to do | fail | empty: product |
| SH-16483 | video | to do | fail | empty: product |
| SH-16484 | video | to do | fail | empty: product |
| SH-16485 | video | to do | fail | empty: product |
| SH-16486 | image | in progress | fail | empty: product |
| SH-16489 | image | sent to mb | fail | empty: product |
| SH-16490 | image | in progress | fail | empty: product |
| SH-16525 | image | approved | fail | empty: product |
| SH-16526 | image | approved | fail | empty: product |
| SH-16527 | image | approved | fail | empty: product |
| SH-16529 | video | to do | fail | empty: product |
| SH-16535 | image | in progress | fail | empty: product |
| SH-16536 | image | to do | fail | empty: product |
| SH-16537 | image | to do | fail | empty: product |
| SH-16538 | image | to do | fail | empty: brand, product, deliv_type, responsible |
| SH-16540 | image | to do | fail | empty: product |
| SH-16541 | image | to do | fail | empty: product |
| SH-16542 | image | to do | fail | empty: product |
| SH-16543 | image | to do | fail | empty: product |
| SH-16544 | image | to do | fail | empty: product |
| SH-16545 | image | to do | fail | empty: product |
| SH-16546 | image | to do | fail | empty: product |
| SH-16592 | image | approved | fail | empty: product |

## `name` — 24

| Task | Type | Status | Sev | Detail |
|------|------|--------|-----|--------|
| SH-16538 | image | to do | fail | missing 4-digit year token |
| SH-16538 | image | to do | fail | missing S## sprint token |
| SH-15496 | video | sent to mb | warn | non-SHA name, not a recognized brief family (review) |
| SH-16313 | image | to do | warn | no canon angle token in name (review) |
| SH-16396 | image | sent to mb | warn | no canon angle token in name (review) |
| SH-16466 | video | to do | warn | no canon angle token in name (review) |
| SH-16475 | image | approved | warn | non-SHA name, not a recognized brief family (review) |
| SH-16476 | video | to do | warn | no canon angle token in name (review) |
| SH-16477 | video | to do | warn | no canon angle token in name (review) |
| SH-16478 | video | cs review | warn | no canon angle token in name (review) |
| SH-16479 | video | sent to mb | warn | no canon angle token in name (review) |
| SH-16484 | video | to do | warn | no canon angle token in name (review) |
| SH-16485 | video | to do | warn | no canon angle token in name (review) |
| SH-16515 | image | to do | warn | no canon angle token in name (review) |
| SH-16517 | image | to do | warn | no canon angle token in name (review) |
| SH-16522 | image | to do | warn | no canon angle token in name (review) |
| SH-16523 | image | to do | warn | no canon angle token in name (review) |
| SH-16524 | image | to do | warn | no canon angle token in name (review) |
| SH-16528 | image | to do | warn | no canon angle token in name (review) |
| SH-16531 | image | to do | warn | no canon angle token in name (review) |
| SH-16534 | image | to do | warn | no canon angle token in name (review) |
| SH-16538 | image | to do | warn | no canon angle token in name (review) |
| SH-16615 | video | in progress | warn | no canon angle token in name (review) |
| SH-16616 | video | to do | warn | no canon angle token in name (review) |

## `em-dash` — 13

| Task | Type | Status | Sev | Detail |
|------|------|--------|-----|--------|
| SH-15680 | image | approved | warn | em/en dash in: headline, text |
| SH-15693 | image | approved | warn | em/en dash in: headline, text |
| SH-15965 | image | in progress | warn | em/en dash in: headline, text |
| SH-15970 | image | sent to mb | warn | em/en dash in: text |
| SH-16604 | image | to do | warn | em/en dash in: text |
| SH-16684 | image | to do | warn | em/en dash in: text |
| SH-16685 | image | to do | warn | em/en dash in: text |
| SH-16686 | image | to do | warn | em/en dash in: text |
| SH-16687 | image | to do | warn | em/en dash in: text |
| SH-16688 | image | to do | warn | em/en dash in: text |
| SH-16689 | image | to do | warn | em/en dash in: text |
| SH-16690 | image | to do | warn | em/en dash in: text |
| SH-16691 | image | to do | warn | em/en dash in: text |

## `list` — 5

| Task | Type | Status | Sev | Detail |
|------|------|--------|-----|--------|
| SH-12878 | video | to do | warn | markdown ordered list in description (collapse risk) |
| SH-15598 | image | sent to mb | warn | markdown ordered list in description (collapse risk) |
| SH-15680 | image | approved | warn | markdown ordered list in description (collapse risk) |
| SH-15686 | video | to do | warn | markdown ordered list in description (collapse risk) |
| SH-16539 | image | approved | warn | markdown ordered list in description (collapse risk) |
