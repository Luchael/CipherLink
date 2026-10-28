"""Official-browser seams use synthetic sessions; no live account is requested."""
import json
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from urllib.error import HTTPError

from gametodo.embedded_login import login_hoyolab, login_skport, LoginStepError
from gametodo.diagnostics import user_error


class LoginFlowTests(unittest.TestCase):
    def test_numeric_error_wins_over_another_unknown_status(self):
        from gametodo.embedded_login import validate_gryphline_basic
        for unknown in ('unknown', False, [], {}):
            self.assertIs(validate_gryphline_basic({'status': unknown, 'code': 1001}), False)

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        tmp = self.stack.enter_context(TemporaryDirectory())
        self.path = Path(tmp) / 'config.json'
        self.path.write_text(json.dumps({'existing': 'setting', 'hoyolab': {'enabled': True}}))
        self.before = self.path.read_bytes()
        self.save = self.stack.enter_context(patch('gametodo.embedded_login.save_secret'))
        self.stack.enter_context(patch('gametodo.embedded_login._open_context', return_value=(MagicMock(), Path(tmp))))
        self.browser = Mock()
        self.stack.enter_context(patch('gametodo.embedded_login._launch', return_value=(self.browser, Mock())))
        self.browser.cookies.return_value = [
            {'domain': '.hoyolab.com', 'name': 'ltoken_v2', 'value': 'SYNTHETIC_PRIVATE_TOKEN'},
            {'domain': '.hoyolab.com', 'name': 'ltuid_v2', 'value': '123'}]
        response = self.browser.request.get.return_value
        response.status = 200
        response.url = 'https://web-api.skport.com/cookie_store/account_token'
        response.json.return_value = {'code': 0, 'data': {'content': 'SYNTHETIC_PRIVATE_TOKEN'}}
        self.http = self.stack.enter_context(patch('gametodo.http_client.HttpClient')).return_value
        self.sk = self.stack.enter_context(patch('gametodo.skport.Skport')).return_value
        self.sk.binding.return_value = {'code': 0, 'data': {'list': [{
            'appCode': 'endfield', 'bindingList': [{'roles': [
                {'roleId': '123', 'serverId': '2', 'serverName': 'Asia'}]}]}]}}
        self.messages = []

    def assert_unchanged(self):
        self.assertEqual(self.path.read_bytes(), self.before)
        self.save.assert_not_called()

    def test_nonzero_basic_response_retains_code_and_shape_without_saving(self):
        self.http.request.return_value = {
            'status': 1001, 'message': 'SYNTHETIC_PRIVATE_MESSAGE', 'data': {'uid': 'SYNTHETIC_PRIVATE_UID'}}
        with self.assertRaises(LoginStepError) as ctx:
            login_skport(self.path, self.messages.append)
        rendered = user_error(ctx.exception)
        self.assertIn('status=1001', rendered)
        self.assertIn('uid:str', rendered)
        self.assertNotIn('SYNTHETIC_PRIVATE', rendered + '\n'.join(self.messages))
        self.sk.binding.assert_not_called()
        self.browser.close.assert_called_once()
        self.assert_unchanged()

    def test_basic_http_auth_denial_stops_before_oauth(self):
        for status in (401, 403):
            with self.subTest(status=status):
                self.http.request.side_effect = HTTPError('https://example.invalid/?secret=PRIVATE', status, 'PRIVATE', {}, None)
                with self.assertRaises(LoginStepError) as ctx:
                    login_skport(self.path, self.messages.append)
                self.assertIn('HTTP ' + str(status), user_error(ctx.exception))
                self.sk.binding.assert_not_called()
                self.assert_unchanged()

    def test_auxiliary_basic_failure_requires_successful_binding(self):
        self.http.request.side_effect = HTTPError('https://example.invalid', 503, 'PRIVATE', {}, None)
        login_skport(self.path, self.messages.append)
        self.sk.binding.assert_called_once()
        self.save.assert_called_once()
        cfg = json.loads(self.path.read_text())
        self.assertEqual(cfg['existing'], 'setting')
        self.assertEqual(cfg['account_data']['endfield']['server_id'], '2')
        self.assertIn('HTTP=503', '\n'.join(self.messages))
        self.assertNotIn('PRIVATE', '\n'.join(self.messages))

    def test_unknown_basic_schema_and_failed_oauth_preserve_existing_settings(self):
        from gametodo.login_diagnostics import LoginApiError
        self.http.request.return_value = {'status': 0, 'data': {}}
        self.sk.binding.side_effect = LoginApiError('skport_oauth', response={'status': 1001, 'message': 'PRIVATE'})
        with self.assertRaises(LoginStepError) as ctx:
            login_skport(self.path, self.messages.append)
        self.assertIn('skport_oauth', user_error(ctx.exception))
        self.assertNotIn('PRIVATE', user_error(ctx.exception))
        self.assert_unchanged()

    def test_hoyo_failure_exposes_only_safe_retcode_and_keeps_previous_connection(self):
        class ProviderError(Exception):
            retcode = -10001
        with patch('gametodo.account_setup._discover_hoyolab_accounts',
                   new=AsyncMock(side_effect=ProviderError('PRIVATE_URL_AND_TOKEN'))):
            with self.assertRaises(LoginStepError) as ctx:
                login_hoyolab(self.path, self.messages.append)
        self.assertIn('retcode=-10001', user_error(ctx.exception))
        self.assertNotIn('PRIVATE', user_error(ctx.exception))
        self.assert_unchanged()


if __name__ == '__main__':
    unittest.main()
