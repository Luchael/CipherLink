"""2026-10-28 Todoist DoDoGames 화면에 표시된 제목 연결. PC·Android 동기화 검증."""
import json
import unittest
from pathlib import Path
from gametodo.task_rules import AUTO_BINDINGS, configured_bindings
from gametodo.live_data import genshin_status, hsr_status, zzz_status

ROOT = Path(__file__).resolve().parents[2]


class ScreenshotBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((ROOT / 'pc/todoist_bindings.json').read_text(encoding='utf8'))
        cls.rows = {x['title']:x for x in cls.catalog['tasks']}

    def test_pc_android_identical(self):
        other=json.loads((ROOT/'android/app/src/main/assets/todoist_bindings.json').read_text(encoding='utf8'))
        self.assertEqual(self.catalog,other)

    def test_actual_screenshot_titles(self):
        titles = [
            '[원신] 일퀘','[열차] 일퀘','[젠존제] 일퀘','[명조] 일퀘',
            '[명방] 일퀘','[립9] 일퀘','[림컴] 엔케팔린 소모','[스소] 일퀘',
            '[엔필] 일퀘','[색지뢰] 일퀘','[원신] 주간보스','[열차] 주간퀘스트',
            '[젠존제] 주간퀘','[명조] 주간퀘','[림컴] 거던','[명방] 섬멸작전 1800개',
            '[원신] 환상극','[립9] 심면구역','[스소] 연합토벌','[원신] 지제전',
            '[열차] 이상중재','[열차] 혼돈','[열차] 허구','[열차] 종말',
            '[젠존제] 시유방어전','[젠존제] 강습전',
            '[명조] 탑','[명조] 폐허','[명조] 매트릭스',
            '[스소] 재앙의전선','[스소] 종언의 노래',
            '[립9] 갈기의 게시판1','[립9] 갈기의 게시판2','[립9] 갈기의 게시판3'
        ]
        self.assertTrue(set(titles).issubset(self.rows))

    def test_only_supported_games_autocomplete(self):
        actual={(v.game,v.title,v.metric) for v in AUTO_BINDINGS}
        for row in self.catalog['tasks']:
            key=(row['game'],row['title'],row['metric'])
            if row['status']=='manual':
                self.assertNotIn(key,actual)
            else:
                self.assertIn(key,actual)
        self.assertFalse(any(x.game=='colorsweeper' for x in AUTO_BINDINGS))
        self.assertNotIn('주간퀘스트(폴리크롬 최대치)', [x.title for x in AUTO_BINDINGS])

    def test_pc_starrail_weekly_requires_both(self):
        def weekly(note): return hsr_status(note).metrics['weekly']
        self.assertFalse(weekly({'current_rogue_score':18000,'max_rogue_score':18000}).filled)
        self.assertFalse(weekly({'current_rogue_score':18000,'max_rogue_score':18000,'remaining_weekly_discounts':1}).filled)
        self.assertFalse(weekly({'current_rogue_score':17000,'max_rogue_score':18000,'remaining_weekly_discounts':0}).filled)
        self.assertTrue(weekly({'current_rogue_score':18000,'max_rogue_score':18000,'remaining_weekly_discounts':0}).filled)

    def test_pc_genshin_weekly_boss_use_three_discounts(self):
        def weekly(remain):
            return genshin_status({'remain_resin_discount_num':remain,'resin_discount_num_limit':3}).metrics['weekly']
        self.assertFalse(weekly(1).filled)
        self.assertTrue(weekly(0).filled)
        self.assertFalse(genshin_status({}).metrics['weekly'].filled)

    def test_pc_zzz_weekly_requires_both(self):
        def weekly(ridu,bounty):
            return zzz_status({'weekly_task':{'cur_point':ridu,'max_point':2100},
                               'bounty_commission':{'total_score':bounty}}).metrics['weekly']
        self.assertFalse(weekly(800,7999).filled)
        self.assertFalse(weekly(799,8000).filled)
        self.assertTrue(weekly(800,8000).filled)
        self.assertFalse(zzz_status({'weekly_task':{'cur_point':800}}).metrics['weekly'].filled)

    def test_daily_override_remains_functional(self):
        names={'account_data':{'task_names':{'genshin':'[원신] 맞춤일퀘'}}}
        binding=configured_bindings(names)
        self.assertIn('[원신] 맞춤일퀘', [b.title for b in binding if b.game=='genshin' and b.kind=='daily'])


if __name__=='__main__': unittest.main()
