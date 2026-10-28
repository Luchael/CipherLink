"""비공개 게임 계정 없이 실행하는 v0.6.2 연결 단계·서버 격리 회귀 테스트."""
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, AsyncMock

from gametodo.embedded_login import (extract_hoyolab_cookie, extract_skport_token,
                                      LoginStepError, login_skport, login_hoyolab)
from gametodo.account_sources import read_wuthering
from gametodo.skport import Skport
from gametodo.diagnostics import user_error
from gametodo.settings import load_settings


class ParseLoginTests(unittest.TestCase):
    def test_hoyo_only_official_domains(self):
        cookies = [{'domain':'.hoyolab.com', 'name':'ltoken_v2','value':'secret-a'},
                   {'domain':'.hoyolab.com', 'name':'ltuid_v2','value':'123456'},
                   {'domain':'evil-hoyolab.com', 'name':'ltoken_v2','value':'secret-b'},
                   {'domain':'.hoyolab.com', 'name':'track','value':'tracker'}]
        result=extract_hoyolab_cookie(cookies)
        self.assertIn('secret-a',result)
        self.assertNotIn('secret-b',result)
        self.assertNotIn('tracker',result)

    def test_missing_cookie_fails_closed(self):
        self.assertIsNone(extract_hoyolab_cookie([{'domain':'.hoyolab.com','name':'ltuid','value':'123'}]))

    def test_skport_success_token(self):
        self.assertEqual(extract_skport_token({'code':0,'data':{'content':'t'*40}}),'t'*40)

    def test_skport_error_not_saved(self):
        for payload in ({'code':10000,'data':{'content':'t'*40}},
                        {'code':0,'data':{'content':None}}, {'code':0,'data':{}}, []):
            self.assertIsNone(extract_skport_token(payload))

    def test_skport_salt_uses_token_field(self):
        class FakeHTTP:
            def request(self, url, **kwargs):
                if url.endswith('/grant'): return {'data':{'code':'oauth-ok'}}
                if url.endswith('/generate_cred_by_code'):return {'data':{'cred':'cred-ok'}}
                if url.endswith('/refresh'):return {'code':0,'data':{'token':'new-signing-key'}}
                if url.endswith('/binding'):return {'data':{'list':[]}}
                raise AssertionError(url)
        sk=Skport('account-token',http=FakeHTTP())
        sk.binding()
        self.assertEqual(sk._salt,'new-signing-key')

    def test_global_wuwa_blocks_cn_request(self):
        class FakeHTTP:
            def request(self,*args,**kwargs): raise AssertionError('CN API requested')
        with self.assertRaisesRegex(ValueError,'글로벌'):
            read_wuthering({'account_data':{'wuthering':{'enabled':True}}},FakeHTTP())

    def test_old_config_global_wuwa_off(self):
        with TemporaryDirectory() as t:
            cfg=Path(t)/'config.json'
            cfg.write_text(json.dumps({'account_data':{'wuthering':{'enabled':True}},'poll_hours':6}),encoding='utf-8')
            self.assertFalse(load_settings(str(cfg))['account_data']['wuthering']['enabled'])

    def test_safe_stage_error(self):
        msg=user_error(LoginStepError('2/5 인증코드', '확인되지 않음'),'SKPORT')
        self.assertIn('2/5 인증코드',msg)


class FakeContext:
    def __init__(self,cookies=None, token=None):self._cookies=cookies or [];self.token=token
    def cookies(self):return self._cookies
    def close(self):pass
    @property
    def request(self):return self
    def get(self,url,**kw):
        token=self.token
        class Response:
            status=200
            url='https://web-api.skport.com/cookie_store/account_token'
            def json(self):return {'code':0,'data':{'content':token}}
        return Response()

class FakePage:
    def goto(self,*args,**kwargs):return None

class FakePW:
    def __enter__(self):return self
    def __exit__(self,*args):return False

class WorkflowTests(unittest.TestCase):
    def test_hoyo_saves_only_after_uid_verified(self):
        with TemporaryDirectory() as t:
            path=Path(t)/'config.json';path.write_text('{}',encoding='utf-8')
            ctx=FakeContext([{'domain':'.hoyolab.com','name':'ltoken_v2','value':'secret'},
                             {'domain':'.hoyolab.com','name':'ltuid_v2','value':'123'}])
            from types import SimpleNamespace
            accounts=[SimpleNamespace(game_biz='hk4e_global',uid='812345678',region='os_asia')]
            with patch('gametodo.embedded_login._open_context',return_value=(lambda:FakePW(),Path(t))), \
                 patch('gametodo.embedded_login._launch',return_value=(ctx,FakePage())), \
                 patch('gametodo.account_setup._discover_hoyolab_accounts',new_callable=AsyncMock,return_value=accounts), \
                 patch('gametodo.embedded_login.save_secret') as saved:
                text=login_hoyolab(str(path),timeout=2)
            self.assertIn('genshin',text)
            self.assertEqual(saved.call_count,1)
            self.assertTrue(json.loads(path.read_text())['hoyolab']['enabled'])

    def test_hoyo_invalid_uid_does_not_save_secret(self):
        with TemporaryDirectory() as t:
            path=Path(t)/'config.json';path.write_text('{}',encoding='utf-8')
            ctx=FakeContext([{'domain':'.hoyolab.com','name':'ltoken_v2','value':'secret'},
                             {'domain':'.hoyolab.com','name':'ltuid_v2','value':'123'}])
            with patch('gametodo.embedded_login._open_context',return_value=(lambda:FakePW(),Path(t))), \
                 patch('gametodo.embedded_login._launch',return_value=(ctx,FakePage())), \
                 patch('gametodo.account_setup._discover_hoyolab_accounts',new_callable=AsyncMock,return_value=[]), \
                 patch('gametodo.embedded_login.save_secret') as saved:
                with self.assertRaises(LoginStepError):login_hoyolab(str(path),timeout=2)
            saved.assert_not_called()
            self.assertNotIn('hoyolab',json.loads(path.read_text()))

    def test_skport_saves_after_binding(self):
        with TemporaryDirectory() as t:
            path=Path(t)/'config.json';path.write_text('{}',encoding='utf-8')
            ctx=FakeContext(token='tok'*20)
            roles={'data':{'list':[{'appCode':'endfield','bindingList':[
                {'defaultRole':{'roleId':'123','serverId':'asia1','serverName':'Asia'}}]}]}}
            with patch('gametodo.embedded_login._open_context',return_value=(lambda:FakePW(),Path(t))), \
                 patch('gametodo.embedded_login._launch',return_value=(ctx,FakePage())), \
                 patch('gametodo.skport.Skport.binding',return_value=roles), \
                 patch('gametodo.http_client.HttpClient.request',return_value={'code':0,'data':{'basicUser':{}}}), \
                 patch('gametodo.embedded_login.save_secret') as saved:
                msg=login_skport(str(path),timeout=2)
            self.assertIn('완료',msg)
            saved.assert_called_once()
            self.assertTrue(json.loads(path.read_text())['account_data']['endfield']['enabled'])

    def test_skport_rejects_unconfirmed_region_without_saving(self):
        with TemporaryDirectory() as t:
            path=Path(t)/'config.json';path.write_text('{}',encoding='utf-8')
            ctx=FakeContext(token='tok'*20)
            roles={'data':{'list':[{'appCode':'endfield','bindingList':[
                {'defaultRole':{'roleId':'123','serverId':'america1','serverName':'America'}}]}]}}
            with patch('gametodo.embedded_login._open_context',return_value=(lambda:FakePW(),Path(t))), \
                 patch('gametodo.embedded_login._launch',return_value=(ctx,FakePage())), \
                 patch('gametodo.skport.Skport.binding',return_value=roles), \
                 patch('gametodo.http_client.HttpClient.request',return_value={'code':0,'data':{'basicUser':{}}}), \
                 patch('gametodo.embedded_login.save_secret') as saved:
                with self.assertRaises(LoginStepError):login_skport(str(path),timeout=2)
            saved.assert_not_called()
            self.assertNotIn('account_data',json.loads(path.read_text()))

if __name__=='__main__':unittest.main()
