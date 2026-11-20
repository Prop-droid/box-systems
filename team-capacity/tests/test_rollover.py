import os, sys, unittest
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weeks as W, rollover as RO
TZ = ZoneInfo("Europe/Vilnius"); H = 3600000
def at(*a, tz=TZ): return W.ms(datetime(*a, tzinfo=tz))
MON = at(2026, 11, 9)
def task(tid, status="in progress", due=None, est_h=8, who=81523936):
    return {"id": tid, "custom_id": tid, "status": {"status": status}, "due_date": str(due or at(2026, 11, 6, 4)),
            "time_estimate": int(est_h * H) if est_h else None, "assignees": [{"id": who}], "custom_fields": [], "name": tid}
class Shift(unittest.TestCase):
    def test_same_weekday_next_week(self): self.assertEqual(RO.shift_due(at(2026, 11, 6, 4), MON), at(2026, 11, 13, 4))
    def test_keeps_time_across_dst(self): self.assertEqual(RO.shift_due(at(2026, 10, 21, 4), MON), at(2026, 11, 11, 4))
    def test_weekend_to_friday(self): self.assertEqual(RO.shift_due(at(2026, 11, 8, 10), MON), at(2026, 11, 13, 10))
    def test_date_only_vilnius_and_istanbul(self):
        self.assertTrue(RO.date_only(at(2026, 11, 6, 4)))
        self.assertTrue(RO.date_only(at(2026, 10, 30, 4, tz=ZoneInfo("Europe/Istanbul"))))
        self.assertFalse(RO.date_only(at(2026, 11, 6, 17)))
class Plan(unittest.TestCase):
    def run_plan(self, tasks, ivs, cuts=None): return {r["id"]: r for r in RO.plan(tasks, ivs, cuts or {}, MON, MON)}
    def test_estimate_minus_tracked(self):
        r = self.run_plan([task("a", est_h=12)], {"a": [(1, at(2026, 11, 3, 10), at(2026, 11, 3, 15), None)]})["a"]
        self.assertEqual(r["est_after_ms"], 7 * H); self.assertEqual(r["due_new"], at(2026, 11, 13, 4))
    def test_floor_and_never_blank(self):
        r = self.run_plan([task("a", est_h=6)], {"a": [(1, at(2026, 11, 3, 8), at(2026, 11, 3, 16), None)]})["a"]
        self.assertEqual(r["est_after_ms"], 1 * H)
    def test_never_raises_small_estimate(self):
        r = self.run_plan([task("a", est_h=0.17)], {"a": [(1, at(2026, 11, 3, 8), at(2026, 11, 3, 16), None)]})["a"]
        self.assertEqual(r["est_after_ms"], int(0.17 * H))
    def test_no_estimate_moves_date_only(self):
        r = self.run_plan([task("a", est_h=None)], {})["a"]
        self.assertEqual(r["est_after_ms"], 0); self.assertEqual(r["est_after_ms"], r["est_before_ms"])
    def test_second_cut_only_subtracts_new_time(self):
        ivs = {"a": [(1, at(2026, 11, 3, 8), at(2026, 11, 3, 12), None), (1, at(2026, 11, 10, 8), at(2026, 11, 10, 10), None)]}
        cuts = {"a": [{"id": "a", "tracked_total_ms": 4 * H, "est_before_ms": 12 * H}]}
        mon2 = at(2026, 11, 16)
        r = {x["id"]: x for x in RO.plan([task("a", due=at(2026, 11, 13, 4), est_h=8)], ivs, cuts, mon2, mon2)}["a"]
        self.assertEqual(r["delta_ms"], 2 * H); self.assertEqual(r["est_after_ms"], 6 * H)
    def test_skips_blocked_handed_off_future_and_non_pool(self):
        ts = [task("b", status="blocked"), task("c", status="cs review"), task("d", due=at(2026, 11, 11, 4)), task("e", who=1)]
        self.assertEqual(self.run_plan(ts, {}), {})
    def test_rolls_todo_and_needs_fixing(self):
        self.assertEqual(set(self.run_plan([task("t", status="to do"), task("n", status="needs fixing")], {})), {"t", "n"})
if __name__ == "__main__": unittest.main()
