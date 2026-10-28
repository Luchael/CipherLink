"""네트워크 없이 한국 서버 픽업 파서·만료·중복·무료 플랜을 테스트."""
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
from pathlib import Path

from gametodo.banners import KST, Banner, parse_banners, character_name
from gametodo.banner_sync import sync_banners, parse_expiry, marker_key, description_for
from gametodo.store import Store


NOW = datetime(2026, 10, 27, 13, 0, tzinfo=KST)
BASE = "https://www.pickupcal.com/games/genshin/"


def li(title, start="2026-10-13 19:00", end="2026-11-03 15:59", typ="한국 서버"):
    return f'<li><a href="/a">{title}</a>원신 {typ} · 시작 {start} · 종료 {end} (KST)</li>'


class BannerParserTests(unittest.TestCase):
    def test_character_extraction(self):
        self.assertEqual(character_name('[복각] 원신 - 「도래한 허계의 별」 기원: 「허계의 별·스커크(얼음)」', '원신'), '스커크')
        self.assertEqual(character_name('[픽업] 젠레스 존 제로 - 「내던진 덧없는 삶」 - 피닉스', '젠레스 존 제로'), '피닉스')
        self.assertEqual(character_name('[픽업] 붕괴: 스타레일 - 「창해에서 맺은 진주」 펄', '붕괴: 스타레일'), '펄')

    def test_only_active_banners_no_event(self):
        html = '<h1>원신의 한국 서버 일정 KST</h1>' + li('[픽업] 원신 - 「전기」 - 캐릭터A') + li('[이벤트] 원신 - 이벤트B')
        found = parse_banners(html, 'genshin', '원신', BASE, now=NOW)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0].title, '[원신] 캐릭터A')

    def test_region_validation(self):
        with self.assertRaises(ValueError):
            parse_banners(li('[픽업] 원신 - 「전기」 - 캐릭터A', typ='중국 서버'), 'genshin','원신',BASE,now=NOW)

    def test_future_and_expired_rejected(self):
        html = '<h1>한국 KST</h1>' + li('[픽업] 원신 - 「가」 - 미래', start='2026-12-01 00:00') + li('[픽업] 원신 - 「나」 - 과거', end='2026-10-01 00:00')
        self.assertEqual(parse_banners(html,'genshin','원신',BASE,now=NOW), [])

    def test_end_exactly_equal_is_no_longer_active(self):
        html = '<h1>한국 KST</h1>' + li('[픽업] 원신 - 「가」 - 영웅', end='2026-10-27 13:00')
        self.assertEqual(parse_banners(html,'genshin','원신',BASE,now=NOW), [])

    def test_key_constant_if_end_extended(self):
        a = Banner('genshin', '스커크', NOW-timedelta(days=1), NOW+timedelta(days=1), BASE)
        b = Banner('genshin', '스커크', NOW-timedelta(days=1), NOW+timedelta(days=3), BASE)
        self.assertEqual(a.key, b.key)
        self.assertEqual(a.title, '[원신] 스커크')

    def test_source_only_and_legacy_expiry_parser(self):
        b = Banner('genshin','스커크', NOW-timedelta(days=1), NOW+timedelta(days=1), BASE)
        description = description_for(b)
        self.assertEqual(description, f"출처: {b.source_url}")
        self.assertIsNone(marker_key({'description': description}))
        self.assertIsNone(parse_expiry(description))
        self.assertIsNone(parse_expiry('가챠 종료(KST): 2026-10-01 00:00'))


class FakeAPI:
    project_id = 'project'
    section_id = 'section'
    def __init__(self, tasks=None):
        self.tasks = tasks or []
        self.operations=[]
    def locate(self): pass
    def all_tasks(self): return self.tasks
    def command(self, op, args, key, temp_id=None):
        self.operations.append((op, args, key))
        return 'task-123' if op=='item_add' else None
    def complete_task(self, task, occurrence):
        self.operations.append(('item_close', task['id'], occurrence))
        return True


class BannerSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(str(Path(self.temp.name) / 'test.db'))
        self.addCleanup(self.store.db.close)
        self.settings = {'game_settings': {'genshin': {'enabled': True,'name':'원신','slug':'genshin'}},
                         'section_name': '이벤트 / 기간 한정'}
        self.banner = Banner('genshin','스커크',NOW-timedelta(days=1),NOW+timedelta(days=1),BASE)

    def test_creation_due_on_banner_start_not_deadline(self):
        api=FakeAPI()
        with patch('gametodo.banner_sync.fetch_banners',return_value=[self.banner]):
            r=sync_banners(self.settings,self.store,api=api,now=NOW)
        self.assertEqual(r['created'], ['[원신] 스커크'])
        self.assertEqual(api.operations[0][1]['due'], {'date': self.banner.start.date().isoformat()})
        self.assertNotIn('deadline',api.operations[0][1])
        self.assertEqual(api.operations[0][1]['labels'],['원신'])

    def test_manual_task_preserved(self):
        api=FakeAPI([{'id':'manual','content':'[원신] 스커크','labels':['원신','중요'],
                      'section_id':'section','description':''}])
        with patch('gametodo.banner_sync.fetch_banners',return_value=[self.banner]):
            r=sync_banners(self.settings,self.store,api=api,now=NOW)
        self.assertFalse(api.operations)
        self.assertTrue(r['skipped'])

    def test_auto_close_after_end_even_when_source_empty(self):
        task = {'id':'task-1','content':self.banner.title,'labels':['원신'],
                'section_id':'section','description':description_for(self.banner),
                'due': {'date':self.banner.start.date().isoformat()}}
        self.store.record_banner(self.banner.key, task['id'], self.banner.end.isoformat(),
            self.banner.title, self.banner.start.date().isoformat(), self.banner.source_url)
        api=FakeAPI([task])
        after = self.banner.end+timedelta(minutes=1, seconds=1)
        with patch('gametodo.banner_sync.fetch_banners', return_value=[]):
            result=sync_banners(self.settings,self.store,api=api,now=after)
        self.assertEqual(len(result['closed']),1)
        self.assertEqual(api.operations[0][0],'item_close')
        with patch('gametodo.banner_sync.fetch_banners',return_value=[]):
            second=sync_banners(self.settings,self.store,api=api,now=after)
        self.assertEqual(second['closed'],[])

    def test_does_not_close_during_final_minute(self):
        old = Banner('genshin','스커크', self.banner.start, NOW, BASE)
        task = {'id':'task-1','content':old.title,'labels':['원신'],
                'section_id':'section','description':description_for(old),
                'due': {'date': old.start.date().isoformat()}}
        self.store.record_banner(old.key,task['id'],old.end.isoformat(),
            old.title,old.start.date().isoformat(),old.source_url)
        api=FakeAPI([task])
        with patch('gametodo.banner_sync.fetch_banners',return_value=[]):
            result=sync_banners(self.settings,self.store,api=api,now=NOW)
        self.assertEqual(result['closed'],[])

    def test_does_not_close_old_general_events(self):
        old = {'id':'event','content':'[원신] 과거 이벤트','labels':['원신'],
               'section_id':'section','description':'GameTodo-ID: abc\n가챠 종료(KST): 2026-01-01 00:00'}
        api=FakeAPI([old])
        with patch('gametodo.banner_sync.fetch_banners',return_value=[]):
            sync_banners(self.settings,self.store,api=api,now=NOW)
        self.assertEqual(api.operations,[])

    def test_not_close_if_extended(self):
        old = Banner('genshin','스커크', self.banner.start, NOW-timedelta(hours=1), BASE)
        task = {'id':'task-1','content':old.title,'labels':['원신'],'section_id':'section',
                'description':f"GameTodo-Banner-ID: {old.key}\n가챠 종료(KST): {old.end:%Y-%m-%d %H:%M}",
                'due':None}
        api=FakeAPI([task])
        with patch('gametodo.banner_sync.fetch_banners',return_value=[self.banner]):
            r=sync_banners(self.settings,self.store,api=api,now=NOW)
        self.assertEqual(r['closed'],[])
        self.assertEqual(api.operations[0][0],'item_update')


if __name__=='__main__':
    unittest.main()
