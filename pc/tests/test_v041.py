"""v0.4.1: 목표 점수 충족 판정 / 제목 재설정 회귀 테스트."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from gametodo.arknights import parse_arknights
from gametodo.account_watch import run_account_check
from gametodo.live_data import hsr_status, genshin_status
from gametodo.settings import load_settings

KST = timezone(timedelta(hours=9))

class GoalPolicyTests(unittest.TestCase):
    def test_arknights_daily_gauge_only_when_explicit_max_available(self):
        complete = parse_arknights({"user": {"status": {"ap": 10, "maxAp": 200},
                     "mission": {"daily": {"progress": 100, "maxProgress": 100}}}})
        self.assertTrue(complete.safe_to_close)
        # 이성이 가득 차도 임무 점수가 없으면 완료되지 않는다.
        incomplete = parse_arknights({"user": {"status": {"ap": 200, "maxAp": 200}}})
        self.assertFalse(incomplete.safe_to_close)

    def test_task_name_override_and_reset_hours_independent(self):
        cfg = {"hoyolab": {"enabled": True, "uids": {"hsr": "812345678"}},
               "account_data": {"task_names": {"hsr": "[열차] 일일훈련"},
                                "reset_hours_kst": {"hsr": 5}}}
        class Todo:
            def __init__(self): self.calls=[]
            def all_tasks(self):
                return [{"id":"1", "content":"[열차] 일일훈련", "labels":["스타레일"],
                         "due":{"date":"2026-10-27"}}]
            def complete_task(self, task, cycle):
                self.calls.append((task["id"],cycle));return True
        class Store:
            def evidence_seen(self, *a, **kw): return True
        todo=Todo()
        state=hsr_status({"current_train_score":500,"max_train_score":500})
        with patch("gametodo.account_watch.read_hoyolab", return_value=("812345678",state)):
            result=run_account_check(cfg, todo, Store(), now=datetime(2026,10,27,12,tzinfo=KST))
        self.assertEqual(todo.calls,[("1","2026-10-27")])
        self.assertEqual(result[0]["action"],"Todoist 완료 적용")

    def test_goal_policy_can_be_reverted_if_user_changes_mind(self):
        cfg={"hoyolab":{"enabled":True,"uids":{"hsr":"812345678"}},
             "account_data":{"score_goal_counts_as_complete":False}}
        class Todo:
            def all_tasks(self): raise AssertionError("엄격 모드는 보상 미확인일 때 작업 조회 금지")
        with patch("gametodo.account_watch.read_hoyolab",return_value=("812345678",
                    hsr_status({"current_train_score":500,"max_train_score":500}))):
            result=run_account_check(cfg, Todo(), object(), now=datetime(2026,10,27,12,tzinfo=KST))
        self.assertFalse(result[0]["auto_complete_allowed"])
        self.assertIn("변경 안 함",result[0]["action"])

    def test_no_repeat_completion_before_next_cycle(self):
        cfg={"hoyolab":{"enabled":True,"uids":{"hsr":"812345678"}}}
        class Todo:
            def __init__(self): self.calls=[]
            def all_tasks(self):
                return [{"id":"1", "content":"[열차] 일퀘", "labels":["스타레일"],
                         "due":{"date":"2026-10-28"}}]
            def complete_task(self,*a): self.calls.append(a);return True
        class Store:
            def evidence_seen(self,*a,**kw): return True
        todo=Todo()
        with patch("gametodo.account_watch.read_hoyolab",return_value=("812345678",
                        hsr_status({"current_train_score":500,"max_train_score":500}))):
            result=run_account_check(cfg, todo, Store(), now=datetime(2026,10,27,12,tzinfo=KST))
        self.assertFalse(todo.calls)
        self.assertIn("다음 회차",result[0]["action"])

if __name__=="__main__": unittest.main()
