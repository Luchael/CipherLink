import unittest
from gametodo.endgame_records import parse

class PublicSchemaContract(unittest.TestCase):
    def test_real_theater_alias_medals(self):
        rec={'data':[{'schedule':{'start_time':1791000000,'end_time':1801000000,'schedule_type':1},
                       'stat':{'get_medal_round_list':[True]*12,'medal_num':12}}],
             'is_unlock': True,'tarot_card_state': {}}
        data=parse('theater',rec)
        self.assertEqual((data.value,data.goal),(12,12))
        self.assertIsNotNone(data.starts)
    def test_mask_medal_num_only(self):
        self.assertIsNone(parse('theater',{'data':[{'stat':{'medal_num':12}}]}))
    def test_unknown_shiyu_not_completed(self):
        self.assertIsNone(parse('shiyu',{'hadal_ver':'v2','hadal_info_v2':{'brief_info':{'total_score':999999}}}))
    def test_nested_shiyu_dates(self):
        res=parse('shiyu',{'hadal_ver':'v2','hadal_info_v2':{'hadal_begin_time':1791000000,
            'hadal_end_time':1801000000, 'fourth_layer_detail':{'rating':'S'}}})
        self.assertEqual(res.starts,1791000000)

if __name__ == '__main__': unittest.main()
