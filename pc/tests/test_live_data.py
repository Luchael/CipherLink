"""개인 계정 없이도 실행하는 API 구조/오판 방지 회귀 테스트."""
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from gametodo.live_data import (genshin_status, hsr_status, zzz_status,
                                wuthering_status, endfield_status, Gauge)
from gametodo.account_sources import _asia_uid, read_wuthering, read_endfield
from gametodo.account_watch import run_account_check
from gametodo.skport import Skport

KST = timezone(timedelta(hours=9))


class LiveDataTests(unittest.TestCase):
    def test_genshin_daily_goal_even_if_rewards_unclaimed(self):
        # 사용자가 선택한 완료 기준은 '점수 달성'. 실제 수령 플래그와 무관하다.
        result = genshin_status({"completed_commissions": 4, "max_commissions": 4,
                                 "claimed_commission_reward": False})
        self.assertTrue(result.safe_to_close)
        self.assertIs(result.all_rewards_claimed, False)  # 실제 수령 정보는 보존
        self.assertTrue(genshin_status({"completed_commissions": 4, "max_commissions": 4,
                                        "claimed_commission_reward": True}).safe_to_close)
        self.assertFalse(genshin_status({"completed_commissions": 3, "max_commissions": 4,
                                         "claimed_commission_reward": True}).safe_to_close)

    def test_hsr_score_goal_is_enough(self):
        note = {"current_train_score": 500, "max_train_score": 500,
                "current_rogue_score": 12000, "max_rogue_score": 12000}
        result = hsr_status(note)
        self.assertTrue(result.safe_to_close)
        self.assertIsNone(result.all_rewards_claimed)
        self.assertEqual(result.report()["completion_basis"], "goal_score")
        # 엄격 모드만 실제 수령 플래그를 요구한다.
        self.assertFalse(result.meets_completion(False))
        note["daily_training"] = {"all_rewards_claimed": False}
        self.assertTrue(hsr_status(note).safe_to_close)
        self.assertFalse(hsr_status({"current_train_score": 499, "max_train_score": 500}).safe_to_close)

    def test_zzz_engagement_goal_is_enough(self):
        obj = {"vitality": {"current": 400, "max": 400},
               "weekly_task": {"current": 100, "max": 100}}
        self.assertTrue(zzz_status(obj).safe_to_close)
        obj["vitality"]["all_rewards_claimed"] = False
        self.assertTrue(zzz_status(obj).safe_to_close)
        obj["vitality"]["current"] = 399
        self.assertFalse(zzz_status(obj).safe_to_close)

    def test_wuthering_and_endfield_goal(self):
        status = wuthering_status({"code": 200, "data": {"serverId": "asia-1",
                                  "roleId": "1888", "livenessData": {"cur": 100, "total": 100}}}, "asia-1")
        self.assertTrue(status.safe_to_close)
        self.assertFalse(wuthering_status({"code": 200, "data": {"serverId": "asia-1",
                          "roleId": "1888", "livenessData": {"cur": 99, "total": 100}}}, "asia-1").safe_to_close)
        s2 = endfield_status({"data": {"detail": {"base": {"roleId": "7788"},
                             "dailyMission": {"dailyActivation": 100, "maxDailyActivation": 100}}}}, "7788", "a")
        self.assertTrue(s2.safe_to_close)

    def test_maximum_must_be_explicit_and_nonzero(self):
        # 없거나 0인 최대 점수, bool 값을 숫자로 착각하는 경우 모두 미완료.
        for status in (
            hsr_status({"current_train_score": 500}),
            hsr_status({"current_train_score": 0, "max_train_score": 0}),
            hsr_status({"current_train_score": True, "max_train_score": 1}),
            zzz_status({"weekly_task": {"current": 100, "max": 100}}),
            genshin_status({"completed_commissions": 4}),
        ):
            self.assertFalse(status.safe_to_close)

    def test_uid_filter(self):
        self.assertTrue(_asia_uid("genshin", "812345678"))
        self.assertTrue(_asia_uid("hsr", "812345678"))
        self.assertTrue(_asia_uid("zzz", "1312345678"))
        self.assertFalse(_asia_uid("zzz", "1012345678"))
        self.assertFalse(_asia_uid("hsr", "712345678"))

    def test_wuwa_requires_confirmed_asia_region(self):
        cfg={"account_data": {"wuthering": {"role_id": "1888", "server_id": "someid"}}}
        class HTTP:
            def request(self,*a,**kw):
                return {"code":200,"data":{"serverId":"someid","roleId":"1888",
                        "serverName":"America","livenessData":{"cur":100,"total":100}}}
        with patch("gametodo.account_sources.read_secret",return_value="hidden"):
            with self.assertRaises(ValueError):
                read_wuthering(cfg,HTTP())

    def test_account_poll_closes_at_goal_even_if_unclaimed(self):
        cfg={"hoyolab": {"enabled":True,"uids":{"hsr":"812345678"}}}
        class FakeTodo:
            def __init__(self): self.calls=[]
            def all_tasks(self): return [{"id":"p","content":"[열차] 일퀘","labels":["스타레일"],"due":{"date":"2026-10-27"}}]
            def complete_task(self,*a): self.calls.append(a);return True
        class FakeStore:
            def evidence_seen(self,*a,**k):return True
        todo=FakeTodo()
        with patch("gametodo.account_watch.read_hoyolab",return_value=("812345678",hsr_status({"current_train_score":500,"max_train_score":500}))):
            results=run_account_check(cfg,todo,FakeStore(),now=datetime(2026,10,27,12,tzinfo=KST))
        self.assertEqual(len(todo.calls),1)
        self.assertEqual(results[0]["action"],"Todoist 완료 적용")

    def test_account_poll_closes_when_proved_twice(self):
        cfg={"hoyolab":{"enabled":True,"genshin_uid":"812345678"}}
        class Todo:
            def __init__(self): self.called=[]
            def all_tasks(self): return [{"id":"g","content":"[원신] 일퀘","labels":["원신"],"due":{"date":"2026-10-27"}}]
            def complete_task(self,*args): self.called.append(args);return True
        class Store:
            def __init__(self):self.calls=0
            def evidence_seen(self,*args,**kwargs):self.calls+=1;return self.calls>1
        todo, store=Todo(),Store()
        state=genshin_status({"completed_commissions":4,"max_commissions":4,"claimed_commission_reward":True})
        with patch("gametodo.account_watch.read_hoyolab",return_value=("812345678",state)):
            now=datetime(2026,10,27,12,tzinfo=KST)
            self.assertEqual(run_account_check(cfg,todo,store,now=now)[0]["action"],"완료 근거 확인: 2분 이상 후 재검증 대기")
            self.assertEqual(run_account_check(cfg,todo,store,now=now)[0]["action"],"Todoist 완료 적용")
        self.assertEqual(len(todo.called),1)

    def test_endfield_binding_region_blocks_non_asia(self):
        cfg={"account_data":{"endfield":{"role_id":"1234","server_id":"2"}}}
        class FakeSkport:
            def __init__(self,*a,**kw):pass
            def binding(self):return {"data":{"list":[{"appCode":"endfield","bindingList":[{"defaultRole":{"roleId":"1234","serverId":"2","serverName":"America/Europe"}}]}]}}
            def detail(self,*args):raise AssertionError("Wrong region should never request detail")
        with patch("gametodo.account_sources.read_secret",return_value="token"):
            with patch("gametodo.skport.Skport",FakeSkport):
                with self.assertRaises(ValueError):read_endfield(cfg)

    def test_skport_authorized_read_only_flow(self):
        class HTTP:
            def __init__(self):self.calls=[]
            def request(self,url,method='GET',payload=None,headers=None):
                self.calls.append((url,method,payload,headers))
                if url.endswith('/grant'):return {"data":{"code":"some_code"}}
                if url.endswith('/generate_cred_by_code'):return {"data":{"cred":"some_cred"}}
                if url.endswith('/refresh'):return {"data":{"salt":"some_salt"}}
                if url.endswith('/binding'):return {"data":{"list":[]}}
                return {"data":{"detail":{}}}
        http=HTTP()
        x=Skport('secret_account_token',http)
        x.binding()
        x.detail("10","asia01")
        self.assertEqual([m for u,m,*_ in http.calls], ["POST","POST","GET","GET","GET"])
        self.assertEqual(http.calls[-1][3]["sk-game-role"],"3_10_asia01")
        self.assertNotIn('secret_account_token',http.calls[-1][0])

if __name__=='__main__':unittest.main()

class EvidenceWindowTests(unittest.TestCase):
    def test_twenty_minute_poll_still_yields_second_evidence(self):
        import tempfile
        from pathlib import Path
        from gametodo.store import Store
        with tempfile.TemporaryDirectory() as tmp:
            db=Store(str(Path(tmp) / "data.sqlite"))
            self.assertFalse(db.evidence_seen("acct:x",1000, min_interval=120,max_age=5400))
            self.assertTrue(db.evidence_seen("acct:x",2200, min_interval=120,max_age=5400))
            self.assertFalse(db.evidence_seen("old:ocr",1000,min_interval=8))
            self.assertFalse(db.evidence_seen("old:ocr",2200,min_interval=8))
