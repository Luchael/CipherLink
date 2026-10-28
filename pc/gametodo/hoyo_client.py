"""Small compatibility boundary for the optional public genshin.py client."""
import inspect


def hoyolab_token_ready(cookies, family):
    """A token needs a same-version account ID, not just an unrelated mid."""
    if not isinstance(cookies, dict) or family not in ('ltoken', 'cookie_token'):
        return False
    return any(cookies.get(token) and any(cookies.get(name) for name in ids)
               for token, ids in (
                   (family + '_v2', ('ltuid_v2', 'account_id_v2')),
                   (family, ('ltuid', 'account_id'))))


def hoyolab_auth_ready(cookies):
    """Only close the login browser when a supported role API can authenticate."""
    return any(hoyolab_token_ready(cookies, family)
               for family in ('ltoken', 'cookie_token'))


async def close_hoyo_client(client):
    """genshin.py 1.7.31 scopes HTTP sessions per request and has no close().

    Retain compatibility with adapters that do expose synchronous/async cleanup.
    A missing cleanup method must never discard a successful API response.
    """
    close = getattr(client, 'close', None)
    if callable(close):
        result = close()
        if inspect.isawaitable(result):
            await result


def hoyolab_ds_headers():
    """Use upstream's normal overseas request headers, without bypassing DS."""
    from genshin import types
    from genshin.utility.ds import get_ds_headers
    return get_ds_headers(region=types.Region.OVERSEAS, lang='ko-kr')
