"""회차·반복 Todoist 일정·주간 및 엔드콘텐츠에 대한 오판 방지 테스트."""
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from gametodo.account_watch import run_account_check
from gametodo.cycles import KST, current_period, due_is_eligible, before_today_reset
from gametodo.live_data import hsr_status, zzz_status, wuthering_status
from gametodo.store import Store
from gametodo.task_rules import configured_bindings


class Tasks:
    def __init__(self, items):
        self.items = items
        self.completed = []
        self.reads = 0

    def all_tasks(self):
        self.reads += 1
        return list(self.items)

    def complete_task(self, task, occurrence):
        self.completed.append((str(task["id"]), occurrence))
        # Todoist 반복 작업: 다음 회차로 넘어가는 모습을 모의한다.
        task["due"] = {"date": "2026-10-28"}
        return True


class AlwaysProven:
    def evidence_seen(self, *args, **kwargs):
        return True


HSR = {"hoyolab": {"enabled": True, "uids": {"hsr": "812345678"}}}
ZZZ = {"hoyolab": {"enabled": True, "uids": {"zzz": "1312345678"}}}
WUWA = {"account_data": {"enabled": True, "wuthering": {"enabled": True}}}


class CycleTests(unittest.TestCase):
    def test_kst_midnight_does_not_start_game_day(self):
        now = datetime(2026, 10, 28, 3, 0, tzinfo=KST)
        self.assertTrue(before_today_reset("genshin", now))
        self.assertIsNone(current_period("genshin", "daily", now))
        self.assertIsNone(current_period("genshin", "weekly", now))
        self.assertFalse(before_today_reset("genshin", now.replace(hour=5)))
        self.assertEqual(current_period("genshin", "daily", now.replace(hour=5)).key,
                         "daily:2026-10-28")

    def test_weekly_reset_is_monday_5am(self):
        mon = datetime(2026, 11, 2, 5, 25, tzinfo=KST)
        self.assertEqual(current_period("hsr", "weekly", mon).key, "weekly:2026-11-02")
        self.assertIsNone(current_period("hsr", "weekly", mon.replace(hour=4)))
        tue = mon + timedelta(days=1)
        self.assertEqual(current_period("hsr", "weekly", tue).key, "weekly:2026-11-02")

    def test_custom_reset_hour_and_minute(self):
        now = datetime(2026, 10, 27, 5, 20, tzinfo=KST)
        self.assertTrue(before_today_reset("endfield", now, times={"endfield": "06:30"}))
        self.assertFalse(before_today_reset("endfield", now, times={"endfield": "04:30"}))
        self.assertFalse(before_today_reset("endfield", now))  # 아시아 05:00 KST 출처 확인 완료
        self.assertFalse(before_today_reset("arknights", now))  # 한국 서버 04:00 KST 검증

    def test_limbus_weekly_resets_thursday_six(self):
        thu = datetime(2026, 10, 29, 6, 25, tzinfo=KST)
        self.assertEqual(current_period("limbus", "weekly", thu).key, "weekly:2026-10-29")
        self.assertIsNone(current_period("limbus", "weekly", thu.replace(hour=5)))
        fri = thu + timedelta(days=1)
        self.assertEqual(current_period("limbus", "weekly", fri).key, "weekly:2026-10-29")

    def test_due_today_past_future_absent_and_offset(self):
        now = datetime(2026, 10, 27, 12, 0, tzinfo=KST)
        self.assertTrue(due_is_eligible({"due": {"date": "2026-10-27"}}, now))
        self.assertTrue(due_is_eligible({"due": {"date": "2026-10-26"}}, now))
        self.assertFalse(due_is_eligible({"due": {"date": "2026-10-28"}}, now))
        self.assertFalse(due_is_eligible({}, now))
        # UTC 10/27 16:00은 KST 10/28 01:00 -> 미래로 거절.
        self.assertFalse(due_is_eligible({"due": {"datetime": "2026-10-27T16:00:00Z"}}, now))
        self.assertFalse(due_is_eligible({"due": {"datetime": "2026-10-27T12:00:00"}}, now))

    def test_rotation_without_future_refresh_is_not_valid(self):
        now = datetime(2026, 10, 27, 12, tzinfo=KST)
        self.assertIsNone(current_period("wuthering", "rotation", now))
        self.assertIsNone(current_period("wuthering", "rotation", now, until_timestamp=1234))
        future = int((now + timedelta(days=12)).timestamp())
        self.assertIn("rotation:until:", current_period("wuthering", "rotation", now,
                                                          until_timestamp=future).key)


class ExecutionTests(unittest.TestCase):
    def test_3am_does_not_fetch_or_complete_previous_cycle(self):
        todo = Tasks([{"id": 1, "content": "[열차] 일퀘", "labels": ["스타레일"],
                       "due": {"date": "2026-10-27"}}])
        with patch("gametodo.account_watch.read_hoyolab", side_effect=AssertionError("API 호출 금지")):
            rows = run_account_check(HSR, todo, AlwaysProven(), now=datetime(2026,10,28,3,tzinfo=KST))
        self.assertFalse(todo.completed)
        self.assertEqual(todo.reads, 0)
        self.assertIn("초기화 전", rows[0]["action"])

    def test_reset_grace_period_avoids_stale_hoyolab(self):
        with patch("gametodo.account_watch.read_hoyolab", side_effect=AssertionError("호출 금지")):
            results = run_account_check(HSR, Tasks([]), AlwaysProven(),
                                        now=datetime(2026,10,27,5,5,tzinfo=KST))
        self.assertIn("감지 보류", results[0]["action"])

    def test_due_eligibility_and_next_day_behavior(self):
        task = {"id":"a", "content":"[열차] 일퀘", "labels":["스타레일"],
                "due":{"date":"2026-10-27"}}
        todo = Tasks([task])
        sample = hsr_status({"current_train_score":500,"max_train_score":500})
        now = datetime(2026,10,27,12,tzinfo=KST)
        with patch("gametodo.account_watch.read_hoyolab", return_value=("812345678",sample)):
            run_account_check(HSR,todo,AlwaysProven(),now=now)
            run_account_check(HSR,todo,AlwaysProven(),now=now)
        self.assertEqual(len(todo.completed),1)
        self.assertEqual(task["due"]["date"], "2026-10-28")

    def test_weekly_zzz_from_specific_weekly_metric(self):
        task = {"id":"weekly-z", "content":"[젠존제] 주간퀘", "labels":["젠레스존제로"],
                "due":{"date":"2026-10-26"}}
        todo = Tasks([task])
        status = zzz_status({"vitality":{"current":300,"max":400},
                             "weekly_task":{"cur_point":800,"max_point":2100},
                             "bounty_commission":{"total_score":8000}})
        with patch("gametodo.account_watch.read_hoyolab", return_value=("1312345678",status)):
            data = run_account_check(ZZZ, todo, AlwaysProven(),now=datetime(2026,10,27,12,tzinfo=KST))
        self.assertEqual(len(todo.completed),1)
        self.assertIn("weekly:2026-10-26",todo.completed[0][1])
        self.assertIn("Todoist 완료 적용",data[0]["other_tasks"][0]["action"])

    def test_wuthering_tower_only_with_expiration_timestamp(self):
        now=datetime(2026,10,27,12,tzinfo=KST)
        task={"id":"tower","content":"[명조] 탑","labels":["명조:워더링웨이브"],
              "due":{"date":"2026-10-20"}}
        todo=Tasks([task])
        status=wuthering_status({"code":200,"data":{"serverId":"asia-1","roleId":"12",
               "towerData":{"cur":36,"total":36,
                            "refreshTimeStamp":int((now+timedelta(days=7)).timestamp())}}},"asia-1")
        with patch("gametodo.account_watch.read_wuthering",return_value=("12",status)):
            out=run_account_check(WUWA,todo,AlwaysProven(),now=now)
        self.assertEqual(todo.completed[0][0],"tower")
        self.assertIn("rotation:until:",todo.completed[0][1])
        self.assertIn("완료 적용",out[0]["other_tasks"][0]["action"])

    def test_cannot_complete_unknown_weekly_or_endgame(self):
        # 통합 주간 점수만으로는 부족하다. 역전의 여운 남은 횟수까지 확인해야 한다.
        task={"id":"hsr-w","content":"[열차] 주간퀘스트","labels":["스타레일"],
              "due":{"date":"2026-10-26"}}
        todo=Tasks([task])
        status=hsr_status({"current_train_score":500,"max_train_score":500,
                           "current_rogue_score":10000,"max_rogue_score":10000})
        with patch("gametodo.account_watch.read_hoyolab",return_value=("812345678",status)):
            run_account_check(HSR,todo,AlwaysProven(),now=datetime(2026,10,27,12,tzinfo=KST))
        self.assertFalse(todo.completed)
        self.assertIn("[열차] 주간퀘스트",[b.title for b in configured_bindings(HSR)])

    def test_completed_occurrence_ledger_prevents_double_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(str(Path(tmp)/"db.sqlite"))
            try:
                key="game:uid:weekly:2026-10-26"
                self.assertFalse(store.has_completed(key))
                store.record_completion(key,"123")
                store.record_completion(key,"123")
                self.assertTrue(store.has_completed(key))
                count=store.db.execute("SELECT COUNT(*) FROM completed_occurrences").fetchone()[0]
                self.assertEqual(count,1)
            finally:
                store.db.close()

if __name__ == "__main__":
    unittest.main()

class OcrDateTests(unittest.TestCase):
    def test_ocr_daily_cannot_close_yesterday_at_3am(self):
        from gametodo.observer import Observer
        task={"id":"ocr-daily","content":"[원신] 일퀘","labels":["원신"],
              "due":{"date":"2026-10-27"}}
        todo=Tasks([task])
        cfg={"screen_rules":[{"enabled":True,"game":"genshin", "kind":"task",
              "task_name":"[원신] 일퀘","context_patterns":["일일 의뢰"],
              "all_claimed_patterns":["보상 모두 받음"]}]}
        obj=Observer(cfg,todo,AlwaysProven())
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None):
                return datetime(2026,10,28,3,tzinfo=KST)
        with patch("gametodo.observer.datetime",Clock):
            self.assertEqual(obj.evaluate("genshin","일일 의뢰 보상 모두 받음"),[])
        self.assertEqual(todo.reads,0)

    def test_ocr_daily_cannot_close_tomorrow_due_at_noon(self):
        from gametodo.observer import Observer
        task={"id":"ocr-daily","content":"[원신] 일퀘","labels":["원신"],
              "due":{"date":"2026-10-28"}}
        todo=Tasks([task])
        cfg={"screen_rules":[{"enabled":True,"game":"genshin", "kind":"task",
              "task_name":"[원신] 일퀘","context_patterns":["일일 의뢰"],
              "all_claimed_patterns":["보상 모두 받음"]}]}
        obj=Observer(cfg,todo,AlwaysProven())
        class Clock(datetime):
            @classmethod
            def now(cls,tz=None):
                return datetime(2026,10,27,12,tzinfo=KST)
        with patch("gametodo.observer.datetime",Clock):
            self.assertEqual(obj.evaluate("genshin","일일 의뢰 보상 모두 받음"),[])
        self.assertFalse(todo.completed)

class ServerTimestampTests(unittest.TestCase):
    def test_wuwa_previous_day_cache_never_completes_even_at_noon(self):
        today = datetime(2026, 10, 27, 12, tzinfo=KST)
        old_timestamp = int(datetime(2026, 10, 27, 4, 50, tzinfo=KST).timestamp())
        state = wuthering_status({"code":200,"data":{"roleId":"12","serverId":"asia",
              "serverTime":old_timestamp,"livenessData":{"cur":100,"total":100}}}, "asia")
        todo=Tasks([{"id":"wu-d","content":"[명조] 일퀘","labels":["명조:워더링웨이브"],
                     "due":{"date":"2026-10-27"}}])
        with patch("gametodo.account_watch.read_wuthering",return_value=("12",state)):
            result=run_account_check(WUWA,todo,AlwaysProven(),now=today)
        self.assertIn("전날 서버 캐시",result[0]["action"])
        self.assertEqual(todo.reads,0)
