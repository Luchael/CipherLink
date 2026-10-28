"""v0.10.5 regressions: partial sessions, provider schemas, unsupported source skip."""
import unittest
from unittest.mock import patch, AsyncMock
from tempfile import TemporaryDirectory
from pathlib import Path
from gametodo.embedded_login import extract_hoyolab_cookie, validate_gryphline_basic
from gametodo.account_setup import _direct_hoyolab_roles, choose_hoyolab_uids
from gametodo.banners import UnsupportedBannerSource, fetch_banners
from gametodo.banner_sync import sync_banners


class LoginRepairTests(unittest.TestCase):
    def test_incomplete_hoyolab_cookie_is_not_accepted(self):
        self.assertIsNone(extract_hoyolab_cookie([
            {'domain':'.hoyolab.com','name':'ltoken_v2','value':'token'}]))
        self.assertIsNotNone(extract_hoyolab_cookie([
            {'domain':'.hoyolab.com','name':'ltoken_v2','value':'token'},
            {'domain':'.hoyolab.com','name':'ltuid_v2','value':'111'}]))

    def test_gryphline_basic_schema_variants(self):
        for ok in ({'status':0,'data':{'basicUser':{'id':1}}},
                   {'code':0,'data':{'user':{'id':1}}},
                   {'code':0,'data':{'id':42}},
                   {'code':0,'data':{'basicUser':{}}}):
            self.assertTrue(validate_gryphline_basic(ok))
        self.assertFalse(validate_gryphline_basic({'status':1001,'data':{}}))
        self.assertIsNone(validate_gryphline_basic({'code':0,'data':{}}))

    def test_hoyolab_readonly_global_api(self):
        class API:
            calls=[]
            def request(self,url,**kwargs):
                self.calls.append((url,kwargs['headers']))
                if 'hk4e_global' in url:
                    return {'retcode':0,'data':{'list':[{'game_biz':'hk4e_global','game_uid':'812345678','region':'os_asia'}]}}
                return {'retcode':0,'data':{'list':[]}}
        api=API()
        roles=_direct_hoyolab_roles('cookie_token_v2=secret; account_id_v2=123',http=api)
        self.assertEqual(choose_hoyolab_uids(roles)[0],{'genshin':'812345678'})
        self.assertEqual(len(api.calls),3)
        self.assertTrue(all('api-account-os.hoyolab.com' in u for u,h in api.calls))

    def test_fallback_does_not_expose_token_in_error(self):
        class API:
            def request(self,*args,**kwargs):
                raise ConnectionError('token=secret')
        with self.assertRaises(RuntimeError) as ctx:
            _direct_hoyolab_roles('cookie_token_v2=secret;account_id_v2=123',http=API())
        self.assertNotIn('secret',str(ctx.exception))


class BannerSourceTests(unittest.TestCase):
    def test_unverified_banner_source_is_explained_as_unsupported(self):
        with self.assertRaises(UnsupportedBannerSource):
            fetch_banners(None,'wuthering',{'enabled':True,'source':'unverified'})

    def test_banner_sync_skips_unsupported_source_not_error(self):
        from datetime import datetime,timezone
        class Dummy:
            pass
        conf={'game_settings':{'wuthering':{'enabled':True,'name':'명조: 워더링 웨이브',
                                         'slug':'wuthering','source':'unverified'}}}
        with patch('gametodo.banner_sync.HttpClient'):
            out=sync_banners(conf,Dummy(),dry_run=True,now=datetime.now(timezone.utc))
        self.assertFalse(out['errors'])
        self.assertIn('wuthering',out['unsupported'])
