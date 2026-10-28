import unittest
from gametodo.endgame_records import parse

NOW_START=1791000000
NOW_END=1801000000
class ShiyuSGradeTests(unittest.TestCase):
    def record(self, scores, fourth='S', passed=True, grades=None):
        rooms=[{'score':v, **({'rating':grades[i]} if grades else {})} for i,v in enumerate(scores)]
        return {'hadal_ver':'v2','hadal_info_v2':{
            'begin_time':NOW_START,'end_time':NOW_END,
            'fourth_layer_detail':{'rating':fourth},
            'fitfh_layer_detail':{'layer_challenge_info_list':rooms},
            'pass_fifth_floor':passed,'brief':{'score':sum(scores)}}}
    def test_user_real_scores_all_s(self):
        p=parse('shiyu',self.record([26390,48516,45724]));self.assertEqual((p.value,p.goal),(4,4))
    def test_90k_alone_does_not_count_as_three_s(self):
        p=parse('shiyu',self.record([50000,20000,20000]));self.assertEqual((p.value,p.goal),(2,4))
    def test_fourth_A_does_not_autocomplete(self):
        p=parse('shiyu',self.record([26390,48516,45724],fourth='A'));self.assertEqual((p.value,p.goal),(3,4))
    def test_rating_overrides_score(self):
        p=parse('shiyu',self.record([30000,30000,30000],grades=['S','A','S']));self.assertEqual((p.value,p.goal),(3,4))
    def test_unknown_rating_does_not_autocomplete(self):
        self.assertIsNone(parse('shiyu',self.record([30000,30000,30000],fourth='?')))
    def test_fifth_floor_uncertain_does_not_complete(self):
        p=parse('shiyu',self.record([30000,30000,30000],passed=False));self.assertFalse(p.filled)
