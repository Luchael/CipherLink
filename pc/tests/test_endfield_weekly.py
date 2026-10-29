import unittest
from datetime import datetime
from unittest.mock import patch
from gametodo.cycles import KST
from gametodo.live_data import endfield_status
from gametodo.task_rules import AUTO_BINDINGS
from gametodo.account_watch import run_account_check

class Memory:
    def __init__(self):self.done=set()
    def has_completed(self,key):return key in self.done
    def record_completion(self,key,task):self.done.add(key)
    def evidence_seen(self,*args,**kwargs):raise AssertionError('Do not wait for second score observation')

class Todo:
    def __init__(self,title='[엔필] 주간퀘스트',due='2026-10-26'):
        self.calls=[];self.title=title;self.due=due
    def all_tasks(self):return [{'id':'weekly','content':self.title,'labels':['명일방주:엔드필드'],
                                 'due':{'date':self.due,'string':'매주 월요일','is_recurring':True}}]
    def complete_task(self,task,cycle):self.calls.append((task['id'],cycle));return True

class EndfieldWeeklyTests(unittest.TestCase):
    cfg={'account_data':{'enabled':True,'endfield':{'enabled':True}}}
    def state(self,score=100):
        return endfield_status({'data':{'detail':{'base':{'roleId':'123'},
            'weeklyMission':{'score':score,'total':100}}}},'123','asia')
    def test_exact_user_title_has_weekly_binding(self):
        self.assertTrue(any(b.game=='endfield' and b.title=='[엔필] 주간퀘스트'
                            and b.kind=='weekly' and b.metric=='weekly_mission' for b in AUTO_BINDINGS))
    def test_first_goal_closes_once_for_monday_cycle(self):
        api,store=Todo(),Memory()
        with patch('gametodo.account_watch.read_endfield',return_value=('123',self.state())):
            for _ in range(2):run_account_check(self.cfg,api,store,now=datetime(2026,10,29,12,tzinfo=KST))
        self.assertEqual(api.calls,[('weekly','weekly:2026-10-26')])
    def test_future_due_wrong_title_or_low_score_never_closes(self):
        for api,state in [(Todo(due='2026-11-02'),self.state()),
                          (Todo(title='[엔필] 다른 임무'),self.state()),(Todo(),self.state(99))]:
            with patch('gametodo.account_watch.read_endfield',return_value=('123',state)):
                run_account_check(self.cfg,api,Memory(),now=datetime(2026,10,29,12,tzinfo=KST))
            self.assertEqual(api.calls,[])
    def test_monday_reset_and_grace_preserved(self):
        for hour,minute in [(4,59),(5,0),(5,19)]:
            api=Todo(due='2026-11-02')
            with patch('gametodo.account_watch.read_endfield',return_value=('123',self.state())):
                run_account_check(self.cfg,api,Memory(),now=datetime(2026,11,2,hour,minute,tzinfo=KST))
            self.assertEqual(api.calls,[])
