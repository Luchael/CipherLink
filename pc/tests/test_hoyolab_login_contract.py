"""Public genshin.py lifecycle/role contract; synthetic sessions, no network."""
import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from gametodo.account_setup import (
    _discover_hoyolab_accounts, _direct_hoyolab_roles, choose_hoyolab_uids,
)
from gametodo.hoyo_client import close_hoyo_client, hoyolab_auth_ready


class HoyoClientContractTests(unittest.TestCase):
    def test_successful_accounts_survive_client_without_close(self):
        class Client:
            def set_cookies(self, cookie):
                pass

            async def get_game_accounts(self):
                return [SimpleNamespace(game_biz='hk4e_global', uid=812345678,
                                        server='os_asia')]

        with patch.dict('sys.modules', {'genshin': SimpleNamespace(Client=Client)}), \
                patch('gametodo.account_setup.asyncio.to_thread', new_callable=AsyncMock,
                      side_effect=RuntimeError('synthetic fallback unavailable')) as fallback:
            accounts = asyncio.run(_discover_hoyolab_accounts(
                'ltoken_v2=synthetic;ltuid_v2=1'))
        self.assertEqual(choose_hoyolab_uids(accounts)[0], {'genshin': '812345678'})
        fallback.assert_not_called()

    def test_public_model_server_alias_cannot_bypass_asia_filter(self):
        account = SimpleNamespace(game_biz='hk4e_global', uid=812345678,
                                  server='os_euro')
        self.assertEqual(choose_hoyolab_uids([account]), ({}, []))

    def test_successful_empty_account_list_is_not_a_request_failure(self):
        class Client:
            def set_cookies(self, cookie):
                pass

            async def get_game_accounts(self):
                return []

        with patch.dict('sys.modules', {'genshin': SimpleNamespace(Client=Client)}), \
                patch('gametodo.account_setup.asyncio.to_thread', new_callable=AsyncMock,
                      side_effect=RuntimeError('synthetic fallback unavailable')) as fallback:
            self.assertEqual(asyncio.run(_discover_hoyolab_accounts(
                'ltoken_v2=synthetic;ltuid_v2=1')), [])
        fallback.assert_not_called()

    def test_auth_cookie_names_must_form_a_usable_same_version_pair(self):
        for cookies in (
            {'ltoken_v2': 'synthetic', 'ltuid_v2': '1'},
            {'ltoken': 'synthetic', 'ltuid': '1'},
            {'cookie_token_v2': 'synthetic', 'account_id_v2': '1'},
            {'cookie_token': 'synthetic', 'account_id': '1'},
        ):
            with self.subTest(names=list(cookies)):
                self.assertTrue(hoyolab_auth_ready(cookies))
        for cookies in (
            {'ltoken_v2': 'synthetic', 'ltuid': '1'},
            {'cookie_token': 'synthetic', 'account_id_v2': '1'},
            {'ltoken_v2': 'synthetic', 'ltmid_v2': 'synthetic-mid'},
            {'stoken_v2': 'synthetic', 'ltuid_v2': '1'},
        ):
            with self.subTest(names=list(cookies)):
                self.assertFalse(hoyolab_auth_ready(cookies))

    def test_cleanup_supports_optional_async_and_sync_adapters(self):
        sync_calls = []
        async_close = AsyncMock()
        asyncio.run(close_hoyo_client(SimpleNamespace()))
        asyncio.run(close_hoyo_client(SimpleNamespace(close=lambda: sync_calls.append(True))))
        asyncio.run(close_hoyo_client(SimpleNamespace(close=async_close)))
        self.assertEqual(sync_calls, [True])
        async_close.assert_awaited_once()

    def test_library_exception_diagnostic_never_renders_remote_text(self):
        class Client:
            def set_cookies(self, cookie):
                pass

            async def get_game_accounts(self):
                raise ValueError('synthetic-private-value https://example.invalid/?auth=synthetic')

        messages = []
        with patch.dict('sys.modules', {'genshin': SimpleNamespace(Client=Client)}), \
                patch('gametodo.account_setup.asyncio.to_thread', new_callable=AsyncMock,
                      return_value=[]) as fallback:
            self.assertEqual(asyncio.run(_discover_hoyolab_accounts(
                'ltoken_v2=synthetic;ltuid_v2=1', notify=messages.append)), [])
        self.assertEqual(messages, ['hoyolab_accounts error=ValueError'])
        self.assertIs(fallback.call_args.kwargs['notify'].__self__, messages)

    def test_legacy_note_lookup_without_close_preserves_success(self):
        from gametodo.hoyolab import request_genshin

        class Client:
            def set_cookies(self, cookie):
                pass

            async def get_genshin_notes(self, uid):
                return 'synthetic-notes'

        with patch.dict('sys.modules', {'genshin': SimpleNamespace(Client=Client)}):
            self.assertEqual(asyncio.run(request_genshin(812345678, 'synthetic')),
                             'synthetic-notes')

    def test_account_note_lookup_without_close_preserves_success(self):
        from gametodo.account_sources import _read_hoyolab_async

        class Client:
            def set_cookies(self, cookie):
                pass

            async def get_genshin_notes(self, uid):
                return 'synthetic-notes'

        with patch.dict('sys.modules', {'genshin': SimpleNamespace(Client=Client)}), \
                patch('gametodo.endgame_records.fetch', new_callable=AsyncMock,
                      return_value=({}, [])):
            self.assertEqual(asyncio.run(_read_hoyolab_async(812345678, 'synthetic', 'genshin')),
                             ('synthetic-notes', {}, []))

    def test_schema_diagnostic_without_close_completes(self):
        from gametodo.safe_diagnostic import collect

        class Client:
            def set_cookies(self, cookie):
                pass

        with patch.dict('sys.modules', {'genshin': SimpleNamespace(Client=Client)}), \
                patch('gametodo.safe_diagnostic.read_secret', return_value='synthetic'):
            result = asyncio.run(collect({'hoyolab': {'uids': {'genshin': '812345678'}}}))
        self.assertTrue(result['hoyolab_connected'])
        self.assertEqual({row['status'] for row in result['requests']}, {'method_unavailable'})


class HoyoDirectRoleContractTests(unittest.TestCase):
    def test_ltoken_uses_upstream_binding_route_and_normal_ds_headers(self):
        class API:
            def __init__(self):
                self.calls = []

            def request(self, url, **kwargs):
                self.calls.append((url, kwargs))
                return {'retcode': 0, 'data': {'list': [
                    {'game_biz': 'hk4e_global', 'game_uid': '812345678', 'region': 'os_asia'},
                    {'game_biz': 'hkrpg_global', 'game_uid': '812345679', 'region': 'prod_official_asia'},
                    {'game_biz': 'nap_global', 'game_uid': '1301234567', 'region': 'prod_gf_jp'},
                ]}}

        api = API()
        with patch('gametodo.account_setup.hoyolab_ds_headers', return_value={'ds': 'synthetic-ds'}) as ds:
            result = _direct_hoyolab_roles('ltoken_v2=synthetic;ltuid_v2=1', http=api)
        ds.assert_called_once()
        self.assertEqual(len(api.calls), 1)
        self.assertEqual(api.calls[0][0],
                         'https://api-os-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie')
        self.assertEqual(api.calls[0][1]['headers']['ds'], 'synthetic-ds')
        self.assertEqual(set(choose_hoyolab_uids(result)[0]), {'genshin', 'hsr', 'zzz'})

    def test_unsupported_cookie_family_never_makes_an_http_request(self):
        api = SimpleNamespace(request=unittest.mock.Mock())
        with self.assertRaises(ValueError):
            _direct_hoyolab_roles('stoken_v2=synthetic;ltuid_v2=1', http=api)
        api.request.assert_not_called()

    def test_api_error_reports_only_status_and_schema(self):
        from gametodo.login_diagnostics import LoginApiError

        class API:
            def request(self, url, **kwargs):
                return {'retcode': -100, 'message': 'synthetic-private-value',
                        'data': {'uid': 'synthetic-private-value'}}

        messages = []
        with self.assertRaises(LoginApiError) as caught:
            _direct_hoyolab_roles('cookie_token_v2=synthetic;account_id_v2=1',
                                  http=API(), notify=messages.append)
        output = str(caught.exception) + ''.join(messages)
        self.assertIn('retcode=-100', output)
        self.assertNotIn('synthetic', output)

    def test_missing_retcode_or_list_does_not_masquerade_as_no_accounts(self):
        from gametodo.login_diagnostics import LoginApiError
        for response in ({'data': {'list': []}}, {'retcode': 0, 'data': {}},
                         {'retcode': 0, 'data': {'list': 'synthetic-private-value'}}):
            api = SimpleNamespace(request=lambda *args, **kwargs: response)
            with self.subTest(response=response):
                with self.assertRaises(LoginApiError):
                    _direct_hoyolab_roles('cookie_token_v2=synthetic;account_id_v2=1', http=api)


if __name__ == '__main__':
    unittest.main()
