"""HoYoLAB 로그인 정보 등록. 인증값 직접 붙여넣기 없이 브라우저 로그인 사용.

**개인정보 주의**: 쿠키는 HoYoLAB 계정 접근 권한이 있는 인증정보이다.
사용자가 이 기능을 명시적으로 누를 때만 로컬 브라우저에서 읽는다.
게임사에 로그인하는 과정의 비밀번호·캡차는 앱이 가로채지 않는다.
필요한 HoYoLAB 쿠키만 로컬 보안 저장소에 남긴다.
"""
import asyncio
import json
import webbrowser

from .credentials import save_secret


def open_login_page():
    webbrowser.open("https://www.hoyolab.com/")


def import_logged_in_browser():
    """genshin.py의 공식 문서에 있는 get_browser_cookies 함수 사용.

    Chrome/Edge 계열의 로컬 브라우저 보호 정책이 변경되면 작동하지 않을 수 있다.
    이 경우 비밀번호 입력을 요청하거나 보안 기능을 우회하지 않는다.
    """
    try:
        import genshin
    except ImportError as exc:
        raise RuntimeError("선택 기능을 쓰려면 python -m pip install 'genshin[cookies]' 실행") from exc
    getter = getattr(genshin.utility, "get_browser_cookies", None)
    if getter is None:
        raise RuntimeError("설치된 genshin.py에 브라우저 쿠키 읽기 기능이 없습니다")
    cookies = getter()
    if isinstance(cookies, str):
        items = dict(item.strip().split("=", 1) for item in cookies.split(";") if "=" in item)
    else:
        items = dict(cookies)
    # 신형(v2)과 구형 이름을 모두 허용. 빈/잘못된 쿠키는 기록하지 않는다.
    auth_keys = ("ltoken", "ltoken_v2", "cookie_token", "cookie_token_v2", "stoken", "stoken_v2")
    if not any(items.get(k) for k in auth_keys):
        raise RuntimeError("현재 브라우저에서 HoYoLAB 로그인 정보를 찾지 못했습니다")
    # browser_cookie 유틸이 반환하는 HoYoLAB 인증 쿠키만 저장한다.
    allowed = set(auth_keys) | {"ltuid", "ltuid_v2", "ltmid_v2", "account_id", "account_id_v2", "account_mid_v2", "cookie_token_v2"}
    limited = {k: v for k, v in items.items() if k in allowed and v}
    save_secret("hoyolab", "; ".join(f"{k}={v}" for k, v in limited.items()))
    return True
