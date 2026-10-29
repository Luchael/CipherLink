import unittest
from types import SimpleNamespace as Obj
from gametodo.live_data import genshin_status, zzz_status, hsr_status
from gametodo.endgame_records import parse
from gametodo.progress_view import status_rows

class PublicModelContractTests(unittest.TestCase):
    def test_raw_genshin_commissions_and_claim_flag_preserved(self):
        state=genshin_status({'finished_task_num':4,'total_task_num':4,'is_extra_task_reward_received':True})
        self.assertTrue(state.meets_completion(False))

    def test_genshin_sdk_weekly_boss_fields(self):
        status=genshin_status(Obj(completed_commissions=4,max_commissions=4,
                                 remaining_resin_discounts=0,max_resin_discounts=3))
        self.assertEqual((status.metrics['weekly'].current,status.metrics['weekly'].maximum),(3,3))

    def test_zzz_real_weekly_task_fields(self):
        for weekly in ({'cur_point':800,'max_point':2100},Obj(cur_point=800,max_point=2100)):
            notes=Obj(weekly_task=weekly)
            status=zzz_status(notes)
            self.assertEqual((status.metrics['weekly_task'].current,status.metrics['weekly_task'].maximum),(800,2100))

    def test_shiyu_sdk_raw_response_is_unwrapped(self):
        raw={'hadal_begin_time':1791000000,'hadal_end_time':1801000000,
             'fourth_layer_detail':{'rating':'S'},'pass_fifth_floor':True,
             'fitfh_layer_detail':{'layer_challenge_info_list':[{'score':26390},{'score':48516},{'score':45724}]}}
        result=parse('shiyu',raw)
        self.assertIsNotNone(result)
        self.assertEqual((result.value,result.goal),(4,4))

    def test_sdk_raw_timestamp_wrappers_keep_current_period(self):
        from datetime import datetime,timezone
        now=int(datetime.now(timezone.utc).timestamp())
        raw={'hadal_begin_time':{'timestamp':now-3600,'tzinfo':timezone.utc},
             'hadal_end_time':{'timestamp':now+3600,'tzinfo':timezone.utc},
             'fourth_layer_detail':{'rating':'S'},'pass_fifth_floor':True,
             'fitfh_layer_detail':{'layer_challenge_info_list':[{'score':26000}]*3}}
        self.assertTrue(parse('shiyu',raw).current())
        raw['hadal_end_time']['timestamp']=now-1
        self.assertFalse(parse('shiyu',raw).current())

    def test_internal_combined_weekly_is_not_a_visible_metric(self):
        state=hsr_status({'current_rogue_score':18000,'remaining_weekly_discounts':0})
        self.assertTrue(state.metrics['weekly'].filled)
        rows=status_rows(state)
        self.assertNotIn('주간 목표',[row.title for row in rows])
        boss=next(row for row in rows if '주간 보스' in row.title)
        self.assertEqual(boss.value,'3 / 3')
        self.assertEqual(boss.percent,100)

    def test_raw_boss_limit_is_not_ignored(self):
        state=hsr_status({'current_rogue_score':18000,'weekly_cocoon_cnt':0,'weekly_cocoon_limit':2})
        self.assertFalse(state.metrics['weekly'].filled)

    def test_endfield_weekly_only_when_both_fields_exist(self):
        from gametodo.live_data import endfield_status
        def status(weekly):return endfield_status({'data':{'detail':{'base':{'roleId':'123'},
            'weeklyMission':weekly}}},'123','asia')
        self.assertEqual(status({'score':50,'total':100}).metrics['weekly_mission'].current,50)
        self.assertNotIn('weekly_mission',status({'total':100}).metrics)
        self.assertNotIn('weekly_mission',status({'score':50,'total':0}).metrics)
        self.assertNotIn('weekly',status({'score':100,'total':100}).metrics)

    def test_umbral_only_displays_actual_current_window_and_boolean_clears(self):
        from gametodo.live_data import endfield_periodic
        def data(end=1800003600,flag=True):return {'indieHard':{'indieHardGroups':[{
            'activityStartTs':'1799996400','activityEndTs':str(end),
            'dungeonGroups':[{'normalDungeon':{'isPass':flag},'hardDungeon':{'isPass':False}}]}]}}
        metrics,titles,notes=endfield_periodic(data(),1800000000)
        self.assertEqual([g.current for g in metrics.values()],[1,0])
        self.assertIn('그림자 이정표 · 일반',titles.values())
        self.assertTrue(all('반복 주기 미확인' in n for n in notes.values()))
        self.assertEqual(endfield_periodic(data(end=1800000000),1800000000),({},{},{}))
        self.assertEqual(len(endfield_periodic(data(flag='true'),1800000000)[0]),1)

    def test_genshin_weekly_is_named_boss(self):
        state=genshin_status({'remain_resin_discount_num':2,'resin_discount_num_limit':3})
        self.assertIn('주간 보스',[r.title for r in status_rows(state)])
