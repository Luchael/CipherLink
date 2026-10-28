"""최초 로그인 전용 브라우저(Windows Edge)를 애플리케이션에서 실행한다.

왜 별도 브라우저 프로필인가?
* 사용자가 API 키/쿠키를 복사할 필요가 없다.
* 크롬/웨일의 보호된 쿠키 DB를 복호화하거나 읽을 필요가 없다.
* 로그인 화면은 게임사의 HTTPS 원본 페이지 그대로 표시된다.
* 브라우저 창은 초기 연결 때만 실행하고 이후 API만 조회해 자원을 절약한다.

Playwright는 최초 로그인에만 필요한 선택 라이브러리다.
Windows의 기본 Edge(channel=msedge)를 우선 사용하므로 브라우저 다운로드는 보통 필요 없다.
이 함수는 실제 게임 계정 로그인 성공을 대신할 수 없으며 인증코드·캡차는 사용자에게 맡긴다.
"""
import asyncio
import time
from pathlib import Path

from .credentials import save_secret
from .account_setup import choose_hoyolab_uids, write_settings, select_asia_endfield_role

PROFILE_ROOT = Path.home() / '.gametodo' / 'browser_profiles'
HOYO_URL = 'https://www.hoyolab.com/'
SKPORT_URL = 'https://game.skport.com/endfield/sign-in'
SKPORT_TOKEN_URL = 'https://web-api.skport.com/cookie_store/account_token'


class LoginStepError(Exception):
    """민감 정보 없는 고정 진단 메시지만 노출하기 위한 오류."""

    def __init__(self, stage: str, reason: str):
        super().__init__(reason)
        self.stage = stage
        self.reason = reason


def _emit(notify, step: str, detail: str):
    if notify:
        notify(f'[{step}] {detail}')


def _open_context(provider):
    """Windows Edge를 독립 프로필로 연다. 외부 쿠키/암호 저장소에 접근하지 않는다."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise LoginStepError('환경 확인', '선택 모듈이 없습니다. python -m pip install playwright') from exc
    PROFILE_ROOT.mkdir(parents=True, exist_ok=True)
    profile = PROFILE_ROOT / provider
    profile.mkdir(parents=True, exist_ok=True)
    # 호출자가 with 컨텍스트를 닫아야 함. 실패하면 명시적으로 안내.
    return sync_playwright, profile


def extract_hoyolab_cookie(cookie_rows):
    """서드파티 영역 쿠키를 절대 보관하지 않고, 원본 HoYoLAB 토큰만 추출한다."""
    accepted = {
        'ltuid', 'ltuid_v2', 'ltoken', 'ltoken_v2', 'ltmid_v2',
        'account_id', 'account_id_v2', 'account_mid_v2',
        'cookie_token', 'cookie_token_v2', 'stoken', 'stoken_v2',
        'ltmid', 'account_mid', 'mid'
    }
    rows = {}
    for entry in cookie_rows:
        domain = str(entry.get('domain', '')).lstrip('.').lower()
        # 명시한 개발사 도메인만 허용: evilhoyolab.com 차단
        if not any(domain == d or domain.endswith('.' + d)
                   for d in ('hoyolab.com', 'hoyoverse.com', 'mihoyo.com')):
            continue
        key, value = entry.get('name'), entry.get('value')
        if key in accepted and value:
            rows[key] = value
    if not _complete_hoyo_auth(rows):
        return None
    return '; '.join(f'{k}={v}' for k, v in sorted(rows.items()))


def _complete_hoyo_auth(rows):
    """Never exit the login browser before both a session token and user identity exist.

    HoYoLAB sets cookies asynchronously; having only ltoken_v2 causes invalid
    get_game_accounts requests and was the most likely step-3 failure.
    """
    if not isinstance(rows, dict):
        return False
    token = any(rows.get(n) for n in ('ltoken_v2', 'ltoken', 'cookie_token_v2',
                                     'cookie_token', 'stoken_v2', 'stoken'))
    identity = any(rows.get(n) for n in ('ltuid_v2', 'ltuid', 'account_id_v2',
                                        'account_id', 'account_mid_v2', 'ltmid_v2'))
    return bool(token and identity)


def validate_gryphline_basic(rsp):
    """Classify basic auth without assuming response's user nesting or `code` key.

    None means unknown schema: only a successful OAuth+binding can validate it.
    Do not treat unknown as revoked credentials.
    """
    if not isinstance(rsp, dict):
        return None
    for key in ('status', 'code'):
        value = rsp.get(key)
        if value is not None:
            try:
                if int(value) != 0:
                    return False
            except (ValueError, TypeError):
                return None
    data = rsp.get('data')
    if isinstance(data, dict):
        if isinstance(data.get('basicUser'), dict):
            return True
        if isinstance(data.get('user'), dict):
            return True
        if data.get('id') or data.get('uid'):
            return True
    if isinstance(rsp.get('basicUser'), dict):
        return True
    return None


def extract_skport_token(payload):
    """SKPORT 문서의 {code:0, data:{content:'ACCOUNT_TOKEN'}}만 수용."""
    if not isinstance(payload, dict) or payload.get('code') != 0:
        return None
    data = payload.get('data')
    if not isinstance(data, dict):
        return None
    token = data.get('content')
    return token.strip() if isinstance(token, str) and len(token.strip()) >= 16 else None


def _launch(profile, start, progress):
    """호출된 Playwright context는 제공자의 로그인 화면만 연다."""
    try:
        context = start.chromium.launch_persistent_context(
            str(profile), channel='msedge', headless=False, viewport={'width': 1060, 'height': 800}
        )
    except Exception as exc:
        raise LoginStepError('내장 로그인 창',
                             'Microsoft Edge 실행 실패. Edge 설치 확인 또는 playwright 모듈 버전 확인') from exc
    page = context.pages[0] if context.pages else context.new_page()
    return context, page


def login_hoyolab(config_path, notify=None, timeout=180):
    """HoYoLAB 로그인 -> 쿠키 확인 -> UID 조회 -> 설정 저장을 순서대로 수행."""
    sync, profile = _open_context('hoyolab')
    _emit(notify, '1/4', 'HoYoLAB 원본 사이트를 별도 Edge 창으로 여는 중')
    with sync() as pw:
        context, page = _launch(profile, pw, notify)
        try:
            page.goto(HOYO_URL, wait_until='domcontentloaded', timeout=30_000)
            _emit(notify, '2/4', '로그인/인증코드/캡차를 공식 페이지에서 직접 완료해주세요')
            deadline = time.monotonic() + timeout
            cookie = None
            while time.monotonic() < deadline:
                cookie = extract_hoyolab_cookie(context.cookies())
                if cookie:
                    break
                time.sleep(2)
            if not cookie:
                raise LoginStepError('2/4 로그인', 'HoYoLAB 인증 쿠키를 확인하지 못했습니다 (로그인 미완료 또는 시간 초과)')
        finally:
            context.close()
    _emit(notify, '3/4', 'HoYoLAB 계정 API로 아시아 UID를 검증 중')
    try:
        from .account_setup import _discover_hoyolab_accounts
        accounts = asyncio.run(_discover_hoyolab_accounts(cookie))
    except ImportError as exc:
        raise LoginStepError('3/4 계정 확인', 'genshin 라이브러리가 필요합니다: python -m pip install genshin') from exc
    except Exception as exc:
        raise LoginStepError('3/4 계정 확인',
                             'HoYoLAB 아시아 UID 조회 실패: 로그인 쿠키 또는 게임 계정 API를 확인해주세요. 진단에서 오류 종류를 확인할 수 있습니다') from exc
    uids, uncertain = choose_hoyolab_uids(accounts)
    if not uids:
        raise LoginStepError('3/4 UID 확인', '연결된 아시아 서버 게임 UID가 발견되지 않았습니다')
    _emit(notify, '4/4', '검증된 UID와 세션을 로컬에 저장 중')
    save_secret('hoyolab', cookie)
    def update(cfg):
        hoyo = cfg.setdefault('hoyolab', {})
        hoyo.setdefault('uids', {}).update(uids)
        hoyo['enabled'] = True
        cfg.setdefault('account_data', {})['enabled'] = True
    write_settings(config_path, update)
    return ('HoYoLAB 연결 확인: ' + ', '.join(sorted(uids)) +
            (' · 다중 계정 수동 선택 필요: ' + ', '.join(uncertain) if uncertain else ''))


def login_skport(config_path, notify=None, timeout=210, choose_role=None):
    """SKPORT 공식 사이트 로그인 -> 공식 API 토큰 -> 바인딩 검사 -> 안전 저장."""
    sync, profile = _open_context('skport')
    _emit(notify, '1/5', 'SKPORT 공식 로그인 페이지를 별도 Edge 창으로 여는 중')
    with sync() as pw:
        context, page = _launch(profile, pw, notify)
        try:
            page.goto(SKPORT_URL, wait_until='domcontentloaded', timeout=30_000)
            _emit(notify, '2/5', '공식 사이트에서 이메일/비밀번호 및 인증코드 입력을 완료해주세요')
            deadline = time.monotonic() + timeout
            token = None
            while time.monotonic() < deadline:
                try:
                    # 게임사 서버만 호출. Playwright의 request는 이 컨텍스트 쿠키를 공유한다.
                    response = context.request.get(SKPORT_TOKEN_URL, timeout=8000,
                        headers={'Accept':'application/json', 'Referer':'https://game.skport.com/', 'x-language':'en-us'})
                    if response.status == 200 and response.url.startswith('https://web-api.skport.com/'):
                        token = extract_skport_token(response.json())
                except Exception:
                    # 공식 사이트에서 로그인 진행 중일 때 반환되는 오류는 반복 검사.
                    token = None
                if token:
                    break
                time.sleep(4)
            if not token:
                raise LoginStepError('2/5 로그인', 'SKPORT ACCOUNT_TOKEN을 발급받지 못했습니다. 로그인/2차 인증 여부를 확인해주세요')
        finally:
            context.close()
    _emit(notify, '3/5', 'GRYPHLINE 인증 토큰의 유효성 검증 중')
    try:
        from .http_client import HttpClient
        rsp = HttpClient(timeout=15).request('https://as.gryphline.com/user/info/v1/basic',
                         headers={'Authorization': f'Bearer {token}', 'x-language': 'en-us'})
        validated = validate_gryphline_basic(rsp)
        if validated is False:
            raise LoginStepError('3/5 토큰 검증', 'GRYPHLINE가 인증 실패 상태 코드를 반환했습니다. 공식 사이트에서 다시 로그인하세요.')
        if validated is None:
            _emit(notify, '3/5', '기본정보 응답 구조가 달라 OAuth와 실제 캐릭터 연결로 재검증합니다')
    except LoginStepError:
        raise
    except Exception as exc:
        # This endpoint is auxiliary: an HTTP 401/403 is a real auth error,
        # other failures are resolved by actual OAuth and binding verification.
        from urllib.error import HTTPError
        if isinstance(exc, HTTPError) and exc.code in (401, 403):
            raise LoginStepError('3/5 토큰 검증', f'계정 서버 인증 거부 (HTTP {exc.code}). 재로그인이 필요합니다.') from exc
        _emit(notify, '3/5', '기본정보 API 확인 실패 · OAuth 바인딩으로 계속 검증합니다')
    _emit(notify, '4/5', 'SKPORT OAuth 승인 및 아시아 캐릭터 바인딩 확인 중')
    try:
        from .skport import Skport
        binding = Skport(token).binding()
        from .account_setup import list_asia_endfield_roles
        roles = list_asia_endfield_roles(binding)
        if len(roles) == 1:
            selected = (roles[0]["role_id"], roles[0]["server_id"])
        elif len(roles) > 1 and choose_role:
            selected = choose_role(roles)
        else:
            selected = None
    except Exception as exc:
        raise LoginStepError('4/5 게임 연동', 'SKPORT OAuth/서명/캐릭터 목록 조회 실패 (API 변경 가능)') from exc
    if not selected:
        raise LoginStepError('4/5 아시아 서버', '아시아 캐릭터가 없거나 여러 계정 중 선택되지 않았습니다. 계정 목록을 확인하세요')
    _emit(notify, '5/5', '인증값과 아시아 캐릭터 정보 저장 중')
    def update(cfg):
        ad = cfg.setdefault('account_data', {})
        ad['enabled'] = True
        ad.setdefault('endfield', {}).update({'enabled': True, 'role_id': selected[0], 'server_id': selected[1]})
    save_secret('skport', token)
    write_settings(config_path, update)
    return 'SKPORT / 엔드필드 아시아 서버 연결 검증 완료'
