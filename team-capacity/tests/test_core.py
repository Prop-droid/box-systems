import unittest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import metrics as M, capacity as CAP, spread as SP, air_count as A, config as C
H = 3600000
def hist(*pairs): return {"status_history": [{"status": s, "total_time": {"since": str(ts)}} for ts, s in pairs[:-1]], "current_status": {"status": pairs[-1][1], "total_time": {"since": str(pairs[-1][0])}}}
def task(i, est_h=8, people=("IGN",), name="SHA_x_vid", status="in progress", due=0):
    return {"id": i, "custom_id": "SH-" + i, "name": name, "status": {"status": status}, "time_estimate": est_h * H, "due_date": str(due) if due else None,
            "assignees": [{"id": C.POOL[p]} for p in people], "custom_fields": [], "markdown_description": "🟧 **OUTPUT:** 3 videos"}
class Finished(unittest.TestCase):
    def test_bounce_back_counts_once_in_first_week(self):
        W1 = (0, 7 * 24 * H - 1); W2 = (7 * 24 * H, 14 * 24 * H - 1)
        h = {"a": hist((1 * H, "in progress"), (2 * H, "cs review"), (3 * H, "mb - testing"), (8 * 24 * H, "needs fixing"), (9 * 24 * H, "mb - testing"))}
        t = [task("a")]
        m1 = M.compute(t, h, {}, *W1, *W2); m2 = M.compute(t, h, {}, *W2, W2[1] + 1, W2[1] + 7 * 24 * H)
        self.assertEqual(m1["kinds"]["vid"]["finished"], 1); self.assertEqual(m2["kinds"]["vid"].get("finished", 0), 0)
    def test_friday_handoff_monday_close_lands_in_handoff_week(self):
        W1 = (0, 7 * 24 * H - 1)
        h = {"a": hist((1 * H, "in progress"), (5 * 24 * H, "cs review"), (7 * 24 * H + 9 * H, "sent to mb"))}
        self.assertEqual(M.compute([task("a")], h, {}, *W1, W1[1] + 1, W1[1] + 7 * 24 * H)["kinds"]["vid"]["finished"], 1)
    def test_backlog_not_active(self):
        W1 = (0, 7 * 24 * H - 1); h = {"a": hist((1 * H, "to do"), (2 * H, "backlog"))}
        self.assertEqual(M.compute([task("a", status="backlog")], h, {}, *W1, W1[1] + 1, W1[1] + 7 * 24 * H)["kinds"]["vid"].get("active", 0), 0)
class Tracked(unittest.TestCase):
    def test_interval_booked_to_week_of_start(self):
        W1 = (0, 7 * 24 * H - 1)
        ivs = [(C.POOL["LEO"], W1[1] - H, W1[1] + H, "clickup")]  # Sun 23:00 -> Mon 01:00
        self.assertAlmostEqual(M.tracked_in(ivs, *W1)["LEO"], 2.0)
        self.assertEqual(M.tracked_in(ivs, W1[1] + 1, W1[1] + 7 * 24 * H).get("LEO", 0), 0)
class Air(unittest.TestCase):
    def test_formats_dedupe(self):
        names = ["SH-1-1_x_VID-1080x1920.mp4", "SH-1-1_x_VID-1080x1350.mp4", "SH-1-2_x_VID-1080x1920.mp4"]
        self.assertEqual(len({A.stem(n) for n in names}), 2)
class Capacity(unittest.TestCase):
    def test_half_day_and_saturday(self):
        d = CAP.days_off([("Karen half-day off", "karen@ejam.com", "2026-10-21", None), ("Leo OOO", "leonardo@ejam.com", "2026-10-24", None)], [])
        self.assertEqual(d["KAR"], [("2026-10-21", 3.6, "Karen half-day off")]); self.assertEqual(d["LEO"], [])
        self.assertAlmostEqual(CAP.capacity(d)["KAR"], 32.4)
    def test_holiday_needs_public_holiday_desc(self):
        d = CAP.days_off([], [("ANA", "DST ends", "Observance", "2026-10-26", "2026-10-27"), ("AYC", "Republic Day", "Public holiday", "2026-10-29", "2026-10-30")])
        self.assertEqual(d["ANA"], []); self.assertEqual(len(d["AYC"]), 1)
class Spread(unittest.TestCase):
    def test_carried_before_todo_and_overflow_friday(self):
        days = [1, 2, 3, 4, 5]; nws, nwe = 0, 10 ** 12
        ot = [{"id": "t", "custom_id": "SH-t", "status": "to do", "people": ["IGN"], "est_h": 8, "tracked_h": 0, "priority": 1, "due_ms": 5},
              {"id": "c", "custom_id": "SH-c", "status": "in progress", "people": ["IGN"], "est_h": 20, "tracked_h": 4, "priority": 9, "due_ms": 0},
              {"id": "z", "custom_id": "SH-z", "status": "to do", "people": ["IGN"], "est_h": 30, "tracked_h": 0, "priority": 2, "due_ms": 5}]
        p = SP.plan(ot, {"c": 16.0}, {"IGN": 36.0}, days, nws, nwe)
        by = {x["id"]: x for x in p}
        self.assertLessEqual(by["c"]["due_ms"], by["t"]["due_ms"]); self.assertTrue(by["z"]["overflow"]); self.assertEqual(by["z"]["due_ms"], 5)
        self.assertEqual(SP.plan(ot, {"c": 16.0}, {"IGN": 0.0}, days, nws, nwe)[0]["due_ms"], 5)
if __name__ == "__main__": unittest.main()
