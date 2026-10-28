"""Synthetic provider envelopes exercise login failures without account secrets."""
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from gametodo.account_setup import list_asia_endfield_roles
from gametodo.skport import Skport


class ReplayHTTP:
    def __init__(self, override=None):
        self.calls = []
        self.responses = {
            'grant': {'code': 0, 'data': {'code': 'synthetic-oauth'}},
            'generate_cred_by_code': {'code': 0, 'data': {'cred': 'synthetic-cred'}},
            'refresh': {'code': 0, 'data': {'token': 'synthetic-signing-key'}},
            'binding': {'code': 0, 'data': {'list': []}},
            'detail': {'code': 0, 'data': {'detail': {}}},
        }
        self.responses.update(override or {})

    def request(self, url, **kwargs):
        stage = url.split('?', 1)[0].rsplit('/', 1)[-1]
        self.calls.append((stage, kwargs))
        return self.responses[stage]


class SkportContractTests(unittest.TestCase):
    def test_oauth_status_code_is_never_used_as_authorization_code(self):
        for response in ({'code': '10001', 'data': {}},
                         {'code': 10001, 'data': {'code': 'synthetic-oauth'}},
                         {'status': 10001, 'data': {'code': 'synthetic-oauth'}}):
            with self.subTest(response=response):
                http = ReplayHTTP({'grant': response})
                with self.assertRaises(RuntimeError):
                    Skport('synthetic-account-token', http).binding()
                self.assertEqual([stage for stage, _ in http.calls], ['grant'])

    def test_each_session_error_stops_before_next_stage(self):
        for stage, expected in (
                ('generate_cred_by_code', ['grant', 'generate_cred_by_code']),
                ('refresh', ['grant', 'generate_cred_by_code', 'refresh'])):
            with self.subTest(stage=stage):
                http = ReplayHTTP({stage: {'code': 10001, 'data': {
                    'cred': 'synthetic-cred', 'token': 'synthetic-signing-key'}}})
                client = Skport('synthetic-account-token', http)
                with self.assertRaises(RuntimeError):
                    client.binding()
                self.assertEqual([s for s, _ in http.calls], expected)
                self.assertIsNone(client._cred)
                self.assertIsNone(client._salt)

    def test_binding_rejects_failed_and_unknown_envelopes(self):
        for response in ({'code': 10001, 'data': {'list': []}},
                         {'code': True, 'data': {'list': []}},
                         {'code': 'unknown', 'data': {'list': []}},
                         {'data': []}, {'data': {}}, {'data': {'list': {}}}):
            with self.subTest(response=response):
                with self.assertRaises(RuntimeError):
                    Skport('synthetic-account-token', ReplayHTTP({'binding': response})).binding()

    def test_malformed_session_data_is_a_safe_stage_error(self):
        for response in ([], {'code': 0, 'data': []}, {'code': 0, 'data': {}}):
            with self.subTest(response=response):
                with self.assertRaises(RuntimeError) as failure:
                    Skport('synthetic-account-token', ReplayHTTP({'grant': response})).binding()
                self.assertNotIn('synthetic-account-token', str(failure.exception))

    def test_success_keeps_public_oauth_and_read_only_signing_contract(self):
        http = ReplayHTTP()
        client = Skport('synthetic-account-token', http)
        with patch('gametodo.skport.time.time', return_value=1700000000):
            self.assertEqual(client.binding()['data']['list'], [])
            client.detail('123', '2')
        self.assertEqual([stage for stage, _ in http.calls],
                         ['grant', 'generate_cred_by_code', 'refresh', 'binding', 'detail'])
        self.assertEqual(http.calls[0][1]['payload']['appCode'], '6eb76d4e13aa36e6')
        self.assertEqual(http.calls[-1][1]['headers']['sk-game-role'], '3_123_2')
        self.assertEqual(http.calls[-1][1]['headers']['timestamp'], '1700000000')
        self.assertEqual(http.calls[-1][1]['headers']['sign'],
                         'c0905398e30ea33d398375e158a5e5c5')

    def test_stage_diagnostics_do_not_render_credentials(self):
        messages = []
        Skport('synthetic-account-token', ReplayHTTP(), notify=messages.append).binding()
        self.assertEqual([message.split(':', 1)[0] for message in messages],
                         ['skport_oauth', 'skport_cred', 'skport_refresh', 'skport_binding'])
        text = '\n'.join(messages)
        self.assertNotIn('synthetic-', text)
        self.assertNotIn('https://', text)
        self.assertIn('code=0', text)

    def test_http_error_preserves_stage_and_status_without_url(self):
        class DeniedHTTP(ReplayHTTP):
            def request(self, url, **kwargs):
                if url.endswith('/refresh'):
                    raise HTTPError(url + '?token=synthetic-private-value', 403,
                                    'synthetic-private-value', {}, None)
                return super().request(url, **kwargs)
        with self.assertRaises(RuntimeError) as failure:
            Skport('synthetic-account-token', DeniedHTTP()).binding()
        text = str(failure.exception)
        self.assertIn('skport_refresh', text)
        self.assertIn('403', text)
        self.assertNotIn('synthetic-', text)
        self.assertNotIn('https://', text)

    def test_zero_string_status_and_legacy_salt_remain_compatible(self):
        http = ReplayHTTP({'refresh': {'status': '0', 'data': {'salt': 'synthetic-legacy-key'}}})
        client = Skport('synthetic-account-token', http)
        self.assertEqual(client.binding()['data']['list'], [])
        self.assertEqual(client._salt, 'synthetic-legacy-key')

    def test_asia_selection_rejects_explicit_conflicting_region(self):
        for name in ('America/Europe', 'Europe', '北美', '中国', '미주', '유럽'):
            binding = {'data': {'list': [{'appCode': 'endfield', 'bindingList': [{
                'defaultRole': {'roleId': '123', 'serverId': '2', 'serverName': name}}]}]}}
            with self.subTest(name=name):
                self.assertEqual(list_asia_endfield_roles(binding), [])

    def test_asia_selection_preserves_valid_deduplicated_roles(self):
        role = {'roleId': '123', 'serverId': '2', 'serverName': 'Asia'}
        binding = {'data': {'list': [{'appCode': 'endfield', 'bindingList': [{
            'defaultRole': role, 'roles': [role]}]}]}}
        self.assertEqual(len(list_asia_endfield_roles(binding)), 1)


if __name__ == '__main__':
    unittest.main()
