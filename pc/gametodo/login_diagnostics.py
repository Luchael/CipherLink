"""Allowlisted login protocol diagnostics. Never render remote values or URLs.

Field *names* below are fixed protocol vocabulary. Unknown/dynamic keys and all
payload values are omitted, except bounded integer status/retcode values.
"""
from urllib.error import HTTPError, URLError

OPERATIONS = frozenset({
    'hoyolab_accounts', 'hoyolab_roles', 'hoyolab_roles_genshin',
    'hoyolab_roles_hsr', 'hoyolab_roles_zzz', 'gryphline_basic',
    'skport_oauth', 'skport_cred', 'skport_refresh', 'skport_binding', 'skport_detail',
})
FIELDS = frozenset({
    'code', 'status', 'retcode', 'data', 'basicUser', 'user', 'id', 'uid',
    'list', 'bindingList', 'defaultRole', 'roles', 'appCode', 'serverId',
    'roleId', 'token', 'cred', 'salt', 'content', 'game_biz', 'game_uid',
    'region', 'server', 'detail', 'message', 'msg',
})


def numeric_status(value):
    """Strict bounded protocol integer; bool and arbitrary response text are not codes."""
    if type(value) is int and abs(value) <= 999_999_999:
        return value
    if isinstance(value, str) and len(value) <= 10:
        digits = value[1:] if value.startswith('-') else value
        if digits and digits.isascii() and digits.isdigit():
            number = int(value)
            if abs(number) <= 999_999_999:
                return number
    return None


def _shape(value, depth=0):
    if type(value) is dict:
        if depth >= 4:
            return 'dict'
        keys = sorted(k for k in value if type(k) is str and k in FIELDS)
        return '{' + ','.join(k + ':' + _shape(value[k], depth + 1) for k in keys) + '}'
    if type(value) is list:
        # No array size or samples of scalar values; one schema sample suffices.
        return 'list[' + (_shape(value[0], depth + 1) if value and depth < 4 else '') + ']'
    return {str: 'str', int: 'int', float: 'float', bool: 'bool',
            type(None): 'null'}.get(type(value), 'unknown')


def response_summary(payload):
    codes = []
    if type(payload) is dict:
        for key in ('retcode', 'code', 'status'):
            if key in payload:
                number = numeric_status(payload[key])
                codes.append(key + '=' + (str(number) if number is not None else 'non_numeric'))
    return '; '.join(codes + ['schema=' + _shape(payload)])


def error_summary(exc):
    if isinstance(exc, LoginApiError):
        return exc.diagnostic
    if isinstance(exc, HTTPError):
        status = numeric_status(exc.code)
        return 'HTTP=' + (str(status) if status is not None else 'unknown')
    retcode = numeric_status(getattr(exc, 'retcode', None))
    if retcode is not None:
        return 'retcode=' + str(retcode)
    for kind in (TimeoutError, ConnectionError, URLError, ImportError,
                 AttributeError, TypeError, ValueError, RuntimeError):
        if isinstance(exc, kind):
            return 'error=' + kind.__name__
    # Do not print arbitrary third-party exception class names.
    # genshin.py carries a retcode, but its message/URL/header must not be used.
    return 'error=provider_error'


class LoginApiError(RuntimeError):
    def __init__(self, operation, response=None, exc=None):
        operation = operation if operation in OPERATIONS else 'login_api'
        detail = error_summary(exc) if exc is not None else response_summary(response)
        self.diagnostic = operation + ': ' + detail
        self.http_status = numeric_status(exc.code) if isinstance(exc, HTTPError) else None
        super().__init__(self.diagnostic)


def login_request(http, operation, url, notify=None, **kwargs):
    """Wrap a read-only/account-login request; do not cache any auth response."""
    try:
        response = http.request(url, **kwargs)
    except Exception as exc:
        error = LoginApiError(operation, exc=exc)
        if notify:
            notify(error.diagnostic)
        raise error from None
    if notify:
        label = operation if operation in OPERATIONS else 'login_api'
        status = numeric_status(getattr(http, 'last_status', None))
        prefix = ('HTTP=' + str(status) + '; ') if status is not None else ''
        notify(label + ': ' + prefix + response_summary(response))
    return response
