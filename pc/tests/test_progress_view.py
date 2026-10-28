import unittest
from gametodo.progress_view import present, status_rows
from gametodo.live_data import Status, Gauge

class ProgressViewTests(unittest.TestCase):
    def test_zero_and_unknown_are_different(self):
        self.assertEqual(present('deadly',0,9).state,'진행 전')
        for value,goal in ((None,9),(0,0),(-1,9),(True,9)):
            self.assertEqual(present('deadly',value,goal).state,'확인 필요')
    def test_goal_and_overflow_display_are_clamped(self):
        self.assertEqual(present('shiyu',4,4).percent,100)
        self.assertEqual(present('shiyu',5,4).percent,100)
        self.assertEqual(present('shiyu',1,4).percent,25)
    def test_weekly_rewards_show_remaining_but_fill_after_all_used(self):
        row=present('weekly_boss_used',3,3)
        self.assertEqual(row.value,'잔여 0 / 3')
        self.assertEqual(row.percent,100)
        self.assertEqual(row.state,'목표 달성')
        self.assertEqual(present('weekly_boss_used',0,3).value,'잔여 3 / 3')

    def test_display_does_not_change_source_metrics(self):
        s=Status('zzz','fixture',Gauge(0,100),metrics={'deadly':Gauge(0,9)})
        rows=status_rows(s)
        self.assertEqual([r.title for r in rows],['일일 목표','위험한 강습전'])
        self.assertEqual(s.metrics['deadly'].current,0)
