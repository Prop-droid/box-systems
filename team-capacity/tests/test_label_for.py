import os, sys, unittest
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import weeks as W
TZ = ZoneInfo("Europe/Vilnius")
def at(*a): return W.ms(datetime(*a, tzinfo=TZ))
class LabelFor(unittest.TestCase):
    def test_first_run_sat(self): self.assertEqual(W.label_for(at(2026, 10, 31, 6, 0))[:2], ("2026-W44", 44))
    def test_second_run_sat_not_repeated(self): self.assertEqual(W.label_for(at(2026, 11, 7, 6, 0))[:2], ("2026-W45", 45))
    def test_late_monday_catchup(self): self.assertEqual(W.label_for(at(2026, 11, 9, 8, 0))[:2], ("2026-W45", 45))
    def test_replay_window_sunday_end(self): self.assertEqual(W.label_for(at(2026, 10, 25, 23, 59))[:2], ("2026-W43", 43))
    def test_header_starts_monday(self): self.assertEqual(W.label_for(at(2026, 11, 7, 6, 0))[2], at(2026, 11, 2, 0, 0))
if __name__ == "__main__": unittest.main()
