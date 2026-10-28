"""GUI 로그인 및 안전한 진단 로직 오프라인 테스트 (외부 계정/네트워크 불필요)."""
import json
from types import SimpleNamespace
from urllib.error import HTTPError
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import unittest

from gametodo.diagnostics import user_error
from gametodo.account_setup import (
    choose_hoyolab_uids, select_asia_endfield_role, select_asia_kuro_role,
    write_settings, _single_token, connect_skport,
)


class LoginTests(unittest.TestCase):
    def test_hoyolab_discover_asian_accounts(self):
        records = [
            SimpleNamespace(game_biz='hk4e_global', uid='812345678', region='os_asia'),
            SimpleNamespace(game_biz='hkrpg_global', uid='812345679', region='prod_official_asia'),
            SimpleNamespace(game_biz='nap_global', uid='1301234567', region='prod_gf_jp'),
            SimpleNamespace(game_biz='hk4e_global', uid='612345678', region='os_usa'),
        ]
        found, uncertain = choose_hoyolab_uids(records)
        self.assertEqual(found, {'genshin':'812345678','hsr':'812345679','zzz':'1301234567'})
        self.assertFalse(uncertain)

    def test_hoyolab_multiple_accounts_not_guessed(self):
        records = [SimpleNamespace(game_biz='hk4e_global',uid='812345678',region='os_asia'),
                   SimpleNamespace(game_biz='hk4e_global',uid='812345679',region='os_asia')]
        found, uncertain = choose_hoyolab_uids(records)
        self.assertNotIn('genshin',found)
        self.assertIn('genshin',uncertain)

    def test_skport_select_verified_asia_only(self):
        payload = {'data': {'list': [{'appCode': 'endfield', 'bindingList': [
            {'defaultRole': {'roleId': '12345', 'serverId': 'as1', 'serverName': 'Asia'},
             'roles': [{'roleId': '67890', 'serverId': 'am1', 'serverName': 'America'}]}
        ]}]}}
        self.assertEqual(select_asia_endfield_role(payload), ('12345','as1'))
        self.assertIsNone(select_asia_endfield_role({'data': {'list': []}}))

    def test_kuro_verified_asia_only(self):
        payload = {'data': {'list': [{'roleId': '456', 'serverId': 'as', 'serverName': 'ASIA'},
                                     {'roleId':'789', 'serverId':'eu','serverName':'Europe'}]}}
        self.assertEqual(select_asia_kuro_role(payload), ('456','as'))

    def test_unambiguous_cookie_only(self):
        self.assertEqual(_single_token([('token','a'*25)], {'token'}), 'a'*25)
        self.assertIsNone(_single_token([('token','a'*25),('token','b'*25)], {'token'}))

    def test_settings_merge_keeps_manual_fields(self):
        with TemporaryDirectory() as d:
            path=Path(d)/'config.json'
            path.write_text(json.dumps({'section_name':'특별', 'custom': 'keep','account_data':{}}),encoding='utf8')
            write_settings(path,lambda cfg:cfg.setdefault('account_data',{}).update({'enabled':True}))
            cfg=json.loads(path.read_text(encoding='utf8'))
            self.assertEqual(cfg['custom'],'keep')
            self.assertTrue(cfg['account_data']['enabled'])

    def test_skport_connect_only_after_verification(self):
        payload = {'data': {'list': [{'appCode': 'endfield', 'bindingList': [
            {'defaultRole': {'roleId': '12345', 'serverId': 'asia-server', 'serverName': 'Asia'}}]}]}}
        with TemporaryDirectory() as d:
            path=Path(d)/'config.json'
            path.write_text('{}',encoding='utf8')
            with patch('gametodo.account_setup._browser_domain_cookies',return_value=[('account_token','a'*40)]), \
                 patch('gametodo.skport.Skport.binding',return_value=payload), \
                 patch('gametodo.account_setup.save_secret') as save:
                msg=connect_skport(path)
            self.assertIn('연결 완료',msg)
            self.assertTrue(save.called)
            cfg=json.loads(path.read_text(encoding='utf8'))
            self.assertEqual(cfg['account_data']['endfield']['role_id'],'12345')

    def test_error_http_status_without_secret(self):
        err=HTTPError('https://api.todoist.com/sync?access_token=TOPSECRET', 401, 'unauthorized',None,None)
        msg=user_error(err,'Todoist 확인')
        self.assertIn('HTTP 401',msg)
        self.assertNotIn('TOPSECRET',msg)

    def test_error_missing_section_hint(self):
        msg=user_error(ValueError("'이벤트 / 기간 한정' 섹션 0개 발견"), '동기화')
        self.assertIn('대상 위치 선택',msg)

if __name__ == '__main__':
    unittest.main()
