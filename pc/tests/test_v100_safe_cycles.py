import unittest
from datetime import datetime, timezone
from gametodo.endgame_records import parse
from gametodo.safe_diagnostic import sanitize

class RealWorldSafeCycleTests(unittest.TestCase):
    def setUp(self):
        self.now=int(datetime.now(timezone.utc).timestamp())
    def test_arbitration_multiple_seasons(self):
        n=self.now
        def rec(s,e,mobs,boss):return {'group':{'begin_time':s,'end_time':e},'mob_stars':mobs,'boss_stars':boss}
        g=parse('arbitration',{'challenge_peak_records':[
            rec(n-500000,n-10000,9,2),rec(n-3600,n+7200,9,3),rec(n-1000000,n-600000,9,3)]})
        self.assertEqual((g.value,g.goal),(12,12))
        self.assertEqual((g.starts,g.ends),(n-3600,n+7200))
        stale=parse('arbitration',{'challenge_peak_records':[rec(n-50000,n-10000,9,3)]})
        self.assertFalse(stale.current())
    def test_pure_fiction_group_ranges(self):
        n=self.now
        result=parse('pure_fiction',{'star_num':12,'groups':[
            {'begin_time':n-100000,'end_time':n-3000},
            {'begin_time':n-3500,'end_time':n+9000}]})
        self.assertTrue(result.current())
    def test_zzz_actual_v2(self):
        n=self.now
        record={'hadal_ver':'v2','hadal_info_v2':{'begin_time':n-3600,'end_time':n+3600,
            'pass_fifth_floor':True,'brief':{'score':120630,'max_score':150000},
            'fourth_layer_detail':{'rating':'S'},
            'fitfh_layer_detail':{'layer_challenge_info_list':[
                {'score':26390},{'score':48516},{'score':45724}]}}}
        result=parse('shiyu',record)
        self.assertEqual((result.value,result.goal),(4,4))
        self.assertTrue(result.current())
        record['hadal_info_v2']['fourth_layer_detail']['rating']='A'
        self.assertFalse(parse('shiyu',record).filled)
    def test_previous_deadly_does_not_check_current(self):
        n=self.now
        self.assertIsNone(parse('deadly',{'has_data':False,'total_star':0,'list':[]}))
        prev=parse('deadly',{'has_data':True,'total_star':9,'start_time':n-900000,'end_time':n-3600})
        self.assertTrue(prev.filled)
        self.assertFalse(prev.current())
    def test_safe_reporting_grade_date(self):
        payload={'uid':'12345','jwt_token':'very_secret','fourth_layer_detail':{'rating':'S+'},
                 'schedule':{'begin_time':{'year':2026,'month':10,'day':28,'hour':5}},
                 'score':120630}
        obj=sanitize(payload)
        self.assertEqual(obj['fourth_layer_detail']['rating'],'S+')
        self.assertEqual(obj['schedule']['begin_time']['month'],10)
        self.assertNotIn('12345',str(obj))
