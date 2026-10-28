"""v0.8.7 회차 조건: 환상극은 스텔라 12개. 공연 메달은 카운트하지 않는다."""
import unittest
import json
from pathlib import Path
from gametodo.endgame_goals import GOALS, achieved, target

class EndgameGoalsTests(unittest.TestCase):
    def test_theater_stella_target(self):
        self.assertEqual(target('theater'),12)
        self.assertEqual(GOALS['theater']['unit'],'stella')
        self.assertFalse(achieved('theater',11))
        self.assertTrue(achieved('theater',12))
        self.assertTrue(achieved('theater',13))

    def test_do_not_infer_from_non_stella(self):
        self.assertFalse(achieved('theater',None))
        self.assertFalse(achieved('theater',True))
        self.assertIsNone(target('stygian'))

    def test_starrail_and_spiral(self):
        self.assertFalse(achieved('moc',35))
        self.assertTrue(achieved('moc',36))
        self.assertTrue(achieved('pure_fiction',12))
        self.assertFalse(achieved('apocalyptic',11))
        self.assertTrue(achieved('apocalyptic',12))
        self.assertEqual(GOALS['stygian']['difficulty'],'dire')

    def test_android_pc_share_identical_rules(self):
        mirror=Path(__file__).resolve().parents[2]/'android'/'app'/'src'/'main'/'assets'/'endgame_goals.json'
        self.assertEqual(GOALS,json.loads(mirror.read_text(encoding='utf8')))
