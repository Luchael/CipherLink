import unittest
from gametodo.endgame_records import parse, choose_record

class FixedLiveSchemaTests(unittest.TestCase):
    def test_deadly_preserves_top_level_score_when_list_present(self):
        data = {'start_time': 1791000000, 'end_time': 1801000000,
                'total_star': 9,'total_score': 65000,'list':[{'score':26000,'star':3}],
                'has_data': True}
        self.assertEqual(choose_record(data,'deadly')['total_star'],9)
        value=parse('deadly',data)
        self.assertIsNotNone(value)
        self.assertEqual((value.value,value.goal),(9,9))
        self.assertEqual(value.starts,1791000000)
    def test_theater_boolean_ints(self):
        record={'data':[{'schedule':{'start_time':1791000000,'end_time':1801000000,
                         'schedule_type':1}, 'stat':{'get_medal_round_list':[1]*11+[0]}}]}
        self.assertEqual(parse('theater',record).value,11)
    def test_theater_round_ids_not_stellas(self):
        record={'data':[{'schedule':{'start_time':1791000000,'end_time':1801000000,
                         'schedule_type':1}, 'stat':{'get_medal_round_list':list(range(1,13))}}]}
        self.assertIsNone(parse('theater',record))

if __name__=='__main__':unittest.main()
