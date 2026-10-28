"""Login diagnostics expose protocol shape, never remote text or identity values."""
import unittest
from urllib.error import HTTPError


class LoginDiagnosticTests(unittest.TestCase):
    def test_response_summary_keeps_only_known_keys_types_and_numeric_codes(self):
        from gametodo.login_diagnostics import response_summary
        summary = response_summary({
            'retcode': -100, 'message': 'PRIVATE_TEXT',
            'data': {'uid': 'PRIVATE_UID', 'token': 'PRIVATE_TOKEN',
                     'PRIVATE_DYNAMIC_KEY': 'PRIVATE_VALUE', 'list': [{'region': 'PRIVATE_REGION'}]}})
        self.assertIn('retcode=-100', summary)
        self.assertIn('uid:str', summary)
        self.assertIn('token:str', summary)
        self.assertNotIn('PRIVATE', summary)

    def test_malicious_status_or_exception_text_is_not_formatted(self):
        from gametodo.login_diagnostics import response_summary, error_summary
        self.assertNotIn('PRIVATE', response_summary({'code': 'PRIVATE_TOKEN'}))
        error = HTTPError('https://example.invalid/?token=PRIVATE_TOKEN', 403,
                          'PRIVATE_TEXT', {'Authorization': 'PRIVATE_TOKEN'}, None)
        self.assertEqual(error_summary(error), 'HTTP=403')
        self.assertNotIn('PRIVATE', error_summary(RuntimeError('PRIVATE_TEXT')))

    def test_request_notifies_sanitized_shape_and_wraps_failure(self):
        from gametodo.login_diagnostics import login_request, LoginApiError
        from unittest.mock import Mock
        notify = Mock()
        api = Mock()
        api.request.return_value = {'code': 0, 'data': {'token': 'PRIVATE_TOKEN'}}
        login_request(api, 'skport_refresh', 'https://example.invalid', notify=notify)
        self.assertIn('skport_refresh', notify.call_args.args[0])
        self.assertNotIn('PRIVATE', notify.call_args.args[0])
        api.request.side_effect = RuntimeError('PRIVATE_TEXT')
        with self.assertRaises(LoginApiError) as ctx:
            login_request(api, 'skport_refresh', 'https://example.invalid', notify=notify)
        self.assertNotIn('PRIVATE', str(ctx.exception))

    def test_unknown_operations_and_exception_class_names_cannot_leak(self):
        from gametodo.login_diagnostics import LoginApiError
        secret_error = type('PRIVATE_TOKEN', (Exception,), {})('PRIVATE_TEXT')
        self.assertNotIn('PRIVATE', str(LoginApiError('PRIVATE_OPERATION', exc=secret_error)))


if __name__ == '__main__':
    unittest.main()
