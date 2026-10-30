import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
from gametodo.cycles import KST
from gametodo.live_data import Status, Gauge
from gametodo.account_watch import run_account_check

class Memory:
    def has_completed(self,key):return False
    def record_completion(self,*args):pass

class Todo:
    def __init__(self):self.calls=[]
    def all_tasks(self):return [{"id":"synthetic","content":"[젠존제] 시유방어전","labels":["젠레스존제로"],
        "due":{"date":"2026-10-30","string":"every 14 days","is_recurring":True}}]
    def complete_task(self,task,cycle):self.calls.append(cycle);return True

class ResetOccurrenceTests(unittest.TestCase):
    def run_case(self,now,start,end):
        api=Todo()
        status=Status("zzz","fixture",metrics={"shiyu":Gauge(4,4)},
            metric_expiries={"shiyu":int(end.timestamp())},
            metric_windows={"shiyu":(int(start.timestamp()),int(end.timestamp()))})
        config={"hoyolab":{"enabled":True,"uids":{"zzz":"1300000000"}}}
        with patch("gametodo.account_watch.read_hoyolab",return_value=("synthetic",status)):
            run_account_check(config,api,Memory(),now=now)
        return api.calls
    def test_previous_record_cannot_close_new_due_even_with_future_end(self):
        now=datetime(2026,10,30,6,tzinfo=KST)
        self.assertEqual(self.run_case(now,now-timedelta(days=14),now+timedelta(days=1)),[])
    def test_before_reset_and_expired_payload_never_close(self):
        reset=datetime(2026,10,30,5,tzinfo=KST)
        self.assertEqual(self.run_case(reset-timedelta(minutes=1),reset-timedelta(days=14),reset),[])
        self.assertEqual(self.run_case(reset+timedelta(minutes=30),reset-timedelta(days=14),reset),[])
    def test_first_current_record_after_grace_closes(self):
        reset=datetime(2026,10,30,5,tzinfo=KST)
        self.assertEqual(len(self.run_case(reset+timedelta(minutes=20),reset,reset+timedelta(days=14))),1)

    def test_source_preserves_api_period_start_not_just_expiry(self):
        from gametodo.account_sources import read_hoyolab
        from gametodo.endgame_records import EndgameProgress
        from unittest.mock import AsyncMock
        now=datetime.now(KST)
        start=int((now-timedelta(days=1)).timestamp());end=int((now+timedelta(days=7)).timestamp())
        row=EndgameProgress("shiyu",4,4,start,end,"fixture")
        with patch("gametodo.account_sources.read_secret",return_value="fixture"), patch(
                "gametodo.account_sources._read_hoyolab_async",new=AsyncMock(return_value=({}, {"shiyu":row}, {}))):
            _,state=read_hoyolab("zzz",{"hoyolab":{"uids":{"zzz":"1300000000"}}})
        self.assertEqual(state.metric_windows["shiyu"],(start,end))
        self.assertEqual(state.metric_expiries["shiyu"],end)
