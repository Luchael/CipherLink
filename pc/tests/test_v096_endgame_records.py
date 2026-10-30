import unittest
from datetime import datetime, timezone
from gametodo.endgame_records import parse, choose_record, date_value

S=1791000000; E=1801000000

class EndgameDataTests(unittest.TestCase):
    def test_theater_real_world_data_array(self):
        rec={'is_unlock':True,'links':[], 'tarot_card_state':{},'data':[
            {'schedule': {'schedule_type':2,'start_time':S-2000000,'end_time':S-1000000},'stat':{'star_challenge_stellas':[True]*12}},
            {'schedule': {'schedule_type':1,'start_time':S,'end_time':E},'stat':{'star_challenge_stellas':[True]*11+[False]}}]}
        g=parse('theater',rec)
        self.assertEqual((g.value,g.goal,g.starts,g.ends),(11,12,S,E))
        self.assertFalse(g.filled)
        self.assertEqual(parse('theater',{'data':[{'stat':{'medal_num':12}}]}),None)

    def test_deadly_per_boss_3_20k(self):
        g=parse('deadly',{'start_time':S,'end_time':E,'challenges':[{'score':20000},{'score':21000},{'score':31000}]})
        self.assertEqual((g.value,g.goal),(9,9));self.assertTrue(g.filled)
        g=parse('deadly',{'challenges':[{'score':40000},{'score':10000},{'score':10000}]})
        self.assertEqual(g.value,5);self.assertFalse(g.filled)
        self.assertIsNone(parse('deadly',{'total_score':120000}))
        self.assertIsNone(parse('deadly',{'challenges':[{'score':30000}]}))

    def test_moc_total_stars(self):
        g=parse('moc',{'begin_time':S,'end_time':E,'total_star':36,'starward_stars':3})
        self.assertEqual(g.value,36)
        self.assertTrue(g.current(datetime.fromtimestamp(S+3600,timezone.utc)))
        self.assertFalse(g.current(datetime.fromtimestamp(S+30,timezone.utc)))
        self.assertFalse(g.current(datetime.fromtimestamp(E+1,timezone.utc)))

    def test_wrong_season_cannot_auto(self):
        g=parse('pure_fiction',{'total_star':12})
        self.assertTrue(g.filled);self.assertFalse(g.current())
        self.assertIsNone(parse('moc',{'list':[{'total_star':36},{'total_star':36}]}))

    def test_zzz_v2_stars_are_not_s_ratings(self):
        self.assertIsNone(parse('shiyu',{'hadal_ver':'v2','hadal_begin_time':S,'hadal_end_time':E,
                         'hadal_info_v2':{'brief_info':{'total_star':5,'max_star':5}}}))
        self.assertIsNone(parse('shiyu',{'hadal_ver':'v2','hadal_info_v2':{'total_score':999999}}))

    def test_nested_shiyu_season_and_dynamic_starward_target(self):
        s=parse('shiyu',{'hadal_ver':'v2','hadal_info_v2':{'begin_time':S,'end_time':E,
                          'fourth_layer_detail':{'rating':'S'}}})
        self.assertEqual((s.starts,s.ends),(S,E))
        self.assertTrue(s.current(datetime.fromtimestamp(S+3600,timezone.utc)))
        future=parse('moc',{'begin_time':S,'end_time':E,'total_star':36,'max_star':48})
        self.assertEqual((future.value,future.goal),(36,48))
        self.assertFalse(future.filled)

    def test_correct_api_mapping(self):
        from gametodo.endgame_records import METHODS
        self.assertEqual(METHODS['genshin']['spiral'],'get_genshin_spiral_abyss')
        self.assertEqual(METHODS['hsr']['arbitration'],'get_anomaly_arbitration')
        self.assertEqual(METHODS['zzz']['deadly'],'get_deadly_assault')

if __name__=='__main__':unittest.main()
