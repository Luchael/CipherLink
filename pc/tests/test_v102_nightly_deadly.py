import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from gametodo.cycles import KST
from gametodo.endgame_records import parse, deadly_detail
from gametodo.lookup_policy import enabled
from gametodo.nightly_arknights import eligible, once


class V102Deadly(unittest.TestCase):
    def setUp(self):
        self.from_date = datetime(2026,10,23,4,0,tzinfo=KST).timestamp()
        self.end_date = datetime(2026,11,6,4,0,tzinfo=KST).timestamp()

    def test_current_unplayed_returns_zero_and_dates(self):
        payload = {'has_data':False, 'has_hard':False, 'list':[], 'hard_list':[],
                   'total_star':0,'total_score':0,'start_time':self.from_date,
                   'end_time':self.end_date}
        result=parse('deadly',payload)
        self.assertEqual(result.value,0)
        self.assertEqual(result.goal,9)
        self.assertEqual(result.starts,self.from_date)
        info=deadly_detail(payload)
        self.assertEqual(info['state'],'not_attempted')
        self.assertEqual(info['normal_stars'],0)
        self.assertEqual(info['adversity_bosses'],[])

    def test_hard_does_not_complete_normal(self):
        payload={'has_data':True,'total_star':0,'total_score':0, 'list':[],
                 'hard_list':[{'score':33930,'star':3}],
                 'start_time':self.from_date,'end_time':self.end_date}
        self.assertEqual(parse('deadly',payload).value,0)
        self.assertEqual(deadly_detail(payload)['adversity_bosses'][0]['stars'],3)

    def test_bad_or_absent_records_no_fabricated_completion(self):
        self.assertIsNone(parse('deadly',{'has_data':False,'total_star':0,'list':[1]}))
        self.assertIsNone(parse('deadly',{'has_data':False,'total_star':0,'list':[], 'hard_list':[]}).starts)

    def test_lookup_toggle_preserves_legacy_games(self):
        self.assertTrue(enabled({},'zzz'))
        self.assertFalse(enabled({},'arknights'))
        self.assertFalse(enabled({'account_data':{'game_lookup':{'zzz':False}}},'zzz'))

class V102Arknights(unittest.TestCase):
    def test_exact_minute_and_opt_in(self):
        d={'account_data':{'enabled':True,'game_lookup':{'arknights':True},
                           'arknights':{'enabled':True}}}
        t=datetime(2026,10,28,23,59,tzinfo=KST)
        self.assertTrue(eligible(d,t))
        self.assertFalse(eligible(d,t-timedelta(minutes=1)))
        self.assertFalse(eligible(d,t+timedelta(minutes=1)))
        with tempfile.TemporaryDirectory() as tmp:
            with patch('gametodo.nightly_arknights.run_account_check',return_value=[]) as read:
                self.assertTrue(once(d,moment=t,directory=tmp))
                self.assertFalse(once(d,moment=t,directory=tmp))
                read.assert_called_once()
                self.assertEqual(len(list(Path(tmp).glob('*.attempt'))),1)

    def test_disabled_never_reads(self):
        d={'account_data':{'enabled':True, 'arknights':{'enabled':True}}}
        with patch('gametodo.nightly_arknights.run_account_check') as read:
            self.assertFalse(once(d,moment=datetime(2026,10,28,23,59,tzinfo=KST)))
            read.assert_not_called()

if __name__ == '__main__':unittest.main()
