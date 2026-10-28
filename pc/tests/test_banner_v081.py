"""v0.8.1: 무료 Todoist 날짜, 출처 전용 설명, 종료 저장소 테스트."""
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from gametodo.banners import Banner, KST
from gametodo.banner_sync import description_for, due_date_for, sync_banners
from gametodo.store import Store


class FakeApi:
    project_id = 'project'
    section_id = 'section'
    def __init__(self, tasks):
        self.tasks = tasks
        self.operations = []
    def locate(self): pass
    def all_tasks(self): return self.tasks
    def command(self, operation, args, key, temp_id=None):
        self.operations.append((operation, args))
        return 'new-id' if operation == 'item_add' else None
    def complete_task(self, task, occurrence):
        self.operations.append(('close', task['id']))
        return True


class BannerV081Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(str(Path(self.temp.name) / 'a.db'))
        self.addCleanup(self.store.db.close)
        self.start = datetime(2026,10,27,5,0,tzinfo=KST)
        self.end = datetime(2026,11,3,10,59,tzinfo=KST)
        self.banner = Banner('genshin','테스트',self.start,self.end,'https://source.example/news')
        self.settings = {'section_name':'이벤트 / 기간 한정',
                         'game_settings':{'genshin':{'enabled':True,'name':'원신','slug':'genshin'}}}

    def task(self, description=None):
        return {'id':'abc123','content':self.banner.title,'labels':['원신'],
                'section_id':'section','project_id':'project',
                'due':{'date':due_date_for(self.banner)},
                'description': description if description is not None else description_for(self.banner)}

    def test_start_is_normal_due_date_and_only_source_description(self):
        api = FakeApi([])
        with patch('gametodo.banner_sync.fetch_banners',return_value=[self.banner]):
            sync_banners(self.settings,self.store,api=api,now=self.start+timedelta(hours=1))
        operation,args = api.operations[0]
        self.assertEqual(operation,'item_add')
        self.assertEqual(args['due'],{'date':'2026-10-27'})
        self.assertNotIn('deadline_date',args)
        self.assertEqual(args['description'],'출처: https://source.example/news')

    def test_finish_only_after_end(self):
        api=FakeApi([self.task()])
        self.store.record_banner(self.banner.key,'abc123',self.end.isoformat(),
            self.banner.title,due_date_for(self.banner),self.banner.source_url)
        with patch('gametodo.banner_sync.fetch_banners',return_value=[]):
            sync_banners(self.settings,self.store,api=api,now=self.end+timedelta(seconds=30))
            self.assertEqual(api.operations,[])
            sync_banners(self.settings,self.store,api=api,now=self.end+timedelta(minutes=1,seconds=1))
        self.assertEqual(api.operations,[('close','abc123')])

    def test_dont_complete_user_modified_source(self):
        api=FakeApi([self.task('출처: https://other.example')])
        self.store.record_banner(self.banner.key,'abc123',self.end.isoformat(),
            self.banner.title,due_date_for(self.banner),self.banner.source_url)
        with patch('gametodo.banner_sync.fetch_banners',return_value=[]):
            sync_banners(self.settings,self.store,api=api,now=self.end+timedelta(days=1))
        self.assertEqual(api.operations,[])

    def test_pc_reconnects_android_banner_using_shared_signature(self):
        api=FakeApi([self.task()])
        with patch('gametodo.banner_sync.fetch_banners',return_value=[self.banner]):
            report=sync_banners(self.settings,self.store,api=api,now=self.start+timedelta(hours=1))
        self.assertEqual(report['created'],[])
        self.assertEqual(self.store.open_banners()[0][1],'abc123')


if __name__ == '__main__': unittest.main()
