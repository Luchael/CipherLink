import unittest
from datetime import datetime,timedelta
from unittest.mock import patch
from gametodo.cycles import KST
from gametodo.fixed_cycles import fixed_occurrence
from gametodo.endfield_longterm import umbral_goal,crisis_progress,war_progress
from gametodo.live_data import endfield_status
from gametodo.account_watch import run_account_check
from gametodo.task_rules import AUTO_BINDINGS
class Memory:
    def __init__(self):self.done=set()
    def has_completed(self,key):return key in self.done
    def record_completion(self,key,task):self.done.add(key)
    def evidence_seen(self,*a,**k):raise AssertionError('No second observation')

NOW=datetime(2026,10,29,12,tzinfo=KST)
BEGIN=int(datetime(2026,10,29,9,tzinfo=KST).timestamp())
END=BEGIN+7*86400

def task(days=49,title='[엔필] 그림자 이정표',due='2026-10-29'):
    return {'id':'task','content':title,'labels':['명일방주:엔드필드'],'project_id':'project','section_id':'n',
            'due':{'date':due,'is_recurring':True,'string':f'every {days} days'}}

def detail(normal=True,hard=True):
    return {'base':{'roleId':'123'},'indieHard':{'indieHardGroups':[{
        'activityStartTs':str(BEGIN),'activityEndTs':str(END),
        'dungeonGroups':[{'normalDungeon':{'isPass':normal},'hardDungeon':{'isPass':hard}}]}]}}

def crisis(done=True):
    return {'code':0,'data':{'crisisContract':{'status':{'id':'fixture','startAtTs':str(BEGIN),'endAtTs':str(END),
        'weeklyMission':{'count':1,'total':1},'indicatorMission':{'count':1,'total':1},
        'stageMission':{'count':int(done),'total':1},'achieve':{'isPlated':done}}}}}

def war(done=True):
    return {'code':0,'data':{'warEchoes':{'seasons':[{'weeks':[{'id':'week','startTs':str(BEGIN),'endTs':str(END),
        'stars':9,'allPlusTasks':done,'dungeonGroups':[{'normalDungeon':{'isPass':True},
        'hardDungeon':{'isPass':True},'cruelDungeon':{'isPass':True}}]}]}]}}}

class FixedCycleTests(unittest.TestCase):
    def test_fixed_recurrence_matches_actual_api_window_without_rewriting(self):
        original=task()
        key=fixed_occurrence(original,49,(BEGIN,END),NOW)
        self.assertEqual(key,f'interval:49:{BEGIN}:{END}')
        self.assertEqual(original['due']['string'],'every 49 days')
        for text in ('every 7 weeks','매 49일','49일마다'):
            t=task();t['due']['string']=text
            self.assertEqual(fixed_occurrence(t,49,(BEGIN,END),NOW),key)
    def test_mismatch_future_overdue_and_old_api_window_fail(self):
        for t,window in [(task(days=21),(BEGIN,END)),(task(due='2026-10-30'),(BEGIN,END)),
                         (task(due='2026-08-01'),(BEGIN,END)),(task(),(BEGIN-7*86400,BEGIN+8*3600))]:
            self.assertIsNone(fixed_occurrence(t,49,window,NOW))
    def test_permanent_series_has_no_invented_end_and_does_not_repeat_old_clear(self):
        self.assertEqual(fixed_occurrence(task(),49,(BEGIN,None),NOW,'series_goal'),f'interval:49:series:{BEGIN}')
        future=NOW+timedelta(days=49)
        self.assertIsNone(fixed_occurrence(task(due=future.date().isoformat()),49,(BEGIN,None),future,'series_goal'))
        self.assertIsNone(fixed_occurrence(task(),49,(BEGIN,None),NOW,'goal'))
    def test_expiry_allowed_only_in_user_147_day_occurrence(self):
        now=NOW+timedelta(days=8)
        self.assertIsNotNone(fixed_occurrence(task(147),147,(BEGIN,END),now,'goal_or_expiry'))
        self.assertIsNone(fixed_occurrence(task(147),147,(BEGIN,END),now,'goal'))
        self.assertIsNone(fixed_occurrence(task(147,due='2026-11-10'),147,(BEGIN,END),now,'goal_or_expiry'))
    def test_weekly_word_is_supported_but_wrong_number_is_not(self):
        t=task(7);t['due']['string']='매주 목요일'
        self.assertIsNotNone(fixed_occurrence(t,7,(BEGIN,END),NOW))
        t['due']['string']='every 2 weeks'
        self.assertIsNone(fixed_occurrence(t,7,(BEGIN,END),NOW))

class LongTermEvidenceTests(unittest.TestCase):
    def test_umbral_requires_every_normal_and_hard_flag(self):
        self.assertTrue(umbral_goal(detail(),NOW.timestamp())[0].filled)
        self.assertFalse(umbral_goal(detail(hard=False),NOW.timestamp())[0].filled)
        self.assertIsNone(umbral_goal(detail(hard='true'),NOW.timestamp()))
        old=detail();old['indieHard']['indieHardGroups'][0]['activityEndTs']=BEGIN
        self.assertTrue(umbral_goal(old,NOW.timestamp())[0].filled)  # bonus end does not erase permanent clears
    def test_crisis_early_complete_or_verified_end_without_inventing_goals(self):
        self.assertTrue(crisis_progress(crisis(),NOW.timestamp())[0]['crisis_complete'].filled)
        self.assertFalse(crisis_progress(crisis(False),NOW.timestamp())[0]['crisis_complete'].filled)
        minimal=crisis_progress(crisis(),NOW.timestamp())[2]
        self.assertFalse(crisis_progress(minimal,NOW.timestamp())[0]['crisis_complete'].filled)
        self.assertTrue(crisis_progress(minimal,END)[0]['crisis_complete'].filled)
    def test_crisis_gameplay_end_precedes_exchange_end_and_survives_safe_cache(self):
        payload=crisis(False);payload['data']['crisisContract']['status']['gameplayEndAtTs']=str(END-86400)
        parsed=crisis_progress(payload,END-86400)
        self.assertTrue(parsed[0]['crisis_complete'].filled)
        self.assertEqual(parsed[1][1],END-86400)
        self.assertTrue(crisis_progress(parsed[2],END-86400)[0]['crisis_complete'].filled)
    def test_failed_api_envelope_and_missing_window_cannot_complete(self):
        bad=crisis();bad['code']=1001
        self.assertIsNone(crisis_progress(bad,NOW.timestamp()))
        missing=crisis();del missing['data']['crisisContract']['status']['endAtTs']
        self.assertIsNone(crisis_progress(missing,NOW.timestamp()))
    def test_war_uses_unique_current_week_and_requires_plus_tasks(self):
        self.assertTrue(war_progress(war(),NOW.timestamp())[0]['war_complete'].filled)
        self.assertFalse(war_progress(war(False),NOW.timestamp())[0]['war_complete'].filled)
        duplicate=war();duplicate['data']['warEchoes']['seasons']*=2
        self.assertIsNone(war_progress(duplicate,NOW.timestamp()))

class FixedCompletionTests(unittest.TestCase):
    cfg={'account_data':{'enabled':True,'endfield':{'enabled':True}}}
    def run_state(self,one,state,when=NOW,location=('project','n'),store=None):
        class API:
            def __init__(self):self.calls=[]
            def all_tasks(self):return [one]
            def named_location(self,*args):return location
            def complete_task(self,t,cycle):self.calls.append((t['id'],cycle));return True
        api=API();store=store or Memory()
        with patch('gametodo.account_watch.read_endfield',return_value=('123',state)):
            for _ in range(2):run_account_check(self.cfg,api,store,now=when)
        return api.calls
    def test_umbral_first_goal_only_once(self):
        state=endfield_status({'data':{'detail':detail()}},'123','asia',now_seconds=NOW.timestamp())
        self.assertEqual(self.run_state(task(),state),[('task',f'interval:49:series:{BEGIN}')])
    def test_crisis_goal_or_end_respects_exact_project_section(self):
        def state(done,now):return endfield_status({'data':{'detail':{'base':{'roleId':'123'}}}},'123','asia',crisis(done),now.timestamp())
        one=task(147,'[엔필] 위기 협약')
        self.assertEqual(len(self.run_state(one,state(True,NOW))),1)
        self.assertEqual(self.run_state(one,state(True,NOW),location=('wrong','n')),[])
        self.assertEqual(self.run_state(one,state(False,NOW)),[])
        later=NOW+timedelta(days=8)
        self.assertEqual(len(self.run_state(one,state(False,later),when=later)),1)
    def test_war_display_is_independent_of_crisis_api_availability(self):
        state=endfield_status({'data':{'detail':{'base':{'roleId':'123'}}}},'123','asia',war=war(),now_seconds=NOW.timestamp())
        self.assertTrue(state.metrics['war_complete'].filled)
        self.assertIn('매주 반복',state.details['metric_notes']['war_status'])
    def test_binding_periods_and_war_exact_title(self):
        expected={'[엔필] 그림자 이정표':49,'[엔필] 위기 협약':147,'[엔필] 전쟁의 메아리':7}
        self.assertEqual({r.title:r.interval_days for r in AUTO_BINDINGS if r.title in expected},expected)

class OptionalProviderTests(unittest.TestCase):
    def test_optional_endpoints_are_signed_global_reads_using_existing_session(self):
        from gametodo.skport import Skport
        from test_skport_login_contract import ReplayHTTP
        http=ReplayHTTP({'indie-hard':{'code':0,'data':{'indieHard':{}}},
                         'crisis-contract':crisis(), 'war-echoes':war()})
        client=Skport('synthetic-account-token',http)
        client.indie_hard('123','2');client.crisis_contract('123','2');client.war_echoes('123','2')
        self.assertEqual([name for name,_ in http.calls],['grant','generate_cred_by_code','refresh','indie-hard','crisis-contract','war-echoes'])
        for _,options in http.calls[-3:]:
            self.assertEqual(options['headers']['sk-game-role'],'3_123_2')
            self.assertEqual(options.get('method','GET'),'GET')
    def test_missing_detail_field_falls_back_and_optional_failure_keeps_daily(self):
        from gametodo.account_sources import read_endfield
        from gametodo import account_sources
        from unittest.mock import Mock
        cfg={'account_data':{'endfield':{'role_id':'123','server_id':'2'}}}
        provider=Mock()
        provider.binding.return_value={'data':{'list':[{'appCode':'endfield','bindingList':[{'defaultRole':{'roleId':'123','serverId':'2','serverName':'Asia'}}]}]}}
        provider.detail.return_value={'data':{'detail':{'base':{'roleId':'123'},'dailyMission':{'dailyActivation':100,'maxDailyActivation':100}}}}
        provider.indie_hard.return_value={'code':0,'data':{'indieHard':detail()['indieHard']}}
        provider.crisis_contract.side_effect=RuntimeError('Unavailable')
        provider.war_echoes.side_effect=RuntimeError('Unavailable')
        with patch('gametodo.account_sources.read_secret',return_value='synthetic-token'),patch('gametodo.skport.Skport',return_value=provider),patch.dict(account_sources._CRISIS_CACHE,{},clear=True),patch.dict(account_sources._WAR_RETRY,{},clear=True),patch.dict(account_sources._INDIE_RETRY,{},clear=True):
            _,state=read_endfield(cfg)
            self.assertTrue(state.daily.filled)
            self.assertIn('umbral_complete',state.metrics)
            _,state=read_endfield(cfg)
            self.assertTrue(state.daily.filled)
            self.assertEqual(provider.crisis_contract.call_count,1)
            self.assertEqual(provider.war_echoes.call_count,1)
