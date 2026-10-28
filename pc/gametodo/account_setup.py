"""게임 계정 첫 연결 자동화 (가능한 공급자만).

* HoYoLAB: 사용자 브라우저 로그인 -> 필수 쿠키 가져오기 -> 계정 목록에서
  아시아 서버 UID만 자동 선택. 사용자 UID 수동 입력 불필요.
* SKPORT: 사용자가 공식 페이지에서 로그인한 브라우저의 *해당 사이트* 쿠키만
  로컬에서 읽어 계정 토큰을 얻을 수 있는 환경에서만 연결한다.
* KuroBBS: 게임사 앱/웹 로그인 토큰이 쿠키로 제공되는 환경에서만 조회한다.
* 명일방주: 사용자가 Yostar 이메일 확인 코드를 직접 확인한 뒤 세션을 저장.

타사 로그인 페이지를 위조하거나 비밀번호/캡차를 가로채지 않는다.
아시아 서버를 검증할 수 없는 계정은 자동 활성화하지 않는다.
"""
import asyncio
import json
from pathlib import Path
import webbrowser

from .credentials import save_secret, read_secret
from .settings import load_settings
from .hoyo_client import close_hoyo_client, hoyolab_ds_headers, hoyolab_token_ready


PROVIDERS = {
    "hoyolab": "https://www.hoyolab.com/",
    "skport": "https://game.skport.com/endfield/sign-in",
    "kurobbs": "https://www.kurobbs.com/",
}


def open_provider(provider: str):
    """사용자 기기의 기존 웹 브라우저에서 게임사 공식 로그인만 연다."""
    if provider not in PROVIDERS:
        raise ValueError("지원하지 않는 로그인 공급자")
    webbrowser.open(PROVIDERS[provider])


def write_settings(path, mutate):
    """설정 파일을 원자적으로 바꾸고 나머지 사용자 설정은 보존한다."""
    p = Path(path)
    cfg = json.loads(p.read_text(encoding="utf-8"))
    mutate(cfg)
    temp = p.with_name(p.name + ".new")
    temp.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(p)


def _hoyo_cookie_dict(cookie):
    if not isinstance(cookie, str):
        return {}
    return {k.strip(): v.strip() for item in cookie.split(';') if '=' in item
            for k, v in [item.split('=', 1)]}


def _direct_hoyolab_roles(cookie, http=None, notify=None):
    """Read-only role fallback with the credential family each API expects.

    The public genshin.py get_game_accounts uses the ltoken binding API; the
    separate account CookieToken API requires cookie_token, not merely ltoken.
    """
    from urllib.parse import urlencode
    from types import SimpleNamespace
    from .http_client import HttpClient
    http = http or HttpClient(timeout=10)
    from .login_diagnostics import LoginApiError, login_request
    cookies = _hoyo_cookie_dict(cookie)
    ltoken_ready = hoyolab_token_ready(cookies, 'ltoken')
    cookie_token_ready = hoyolab_token_ready(cookies, 'cookie_token')
    if not (ltoken_ready or cookie_token_ready):
        raise ValueError('HoYoLAB 인증 쿠키/계정 ID 조합 부족')
    headers = {'Cookie': cookie, 'Origin': 'https://www.hoyolab.com',
               'Referer': 'https://www.hoyolab.com/', 'Accept':'application/json',
               'x-rpc-client_type': '5', 'x-rpc-language': 'ko-kr'}
    result = []
    errors = []
    if ltoken_ready:
        try:
            ltoken_headers = dict(headers)
            ltoken_headers.update(hoyolab_ds_headers())
            rsp = login_request(http, 'hoyolab_accounts',
                'https://api-os-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie',
                headers=ltoken_headers, notify=notify)
            if (not isinstance(rsp, dict) or type(rsp.get('retcode')) is not int
                    or rsp['retcode'] != 0 or not isinstance(rsp.get('data'), dict)
                    or not isinstance(rsp['data'].get('list'), list)):
                raise LoginApiError('hoyolab_accounts', response=rsp)
            return [SimpleNamespace(game_biz=row.get('game_biz') or '',
                        uid=str(row.get('game_uid') or row.get('uid') or ''),
                        region=str(row.get('region') or ''))
                    for row in rsp['data']['list'] if isinstance(row, dict)]
        except Exception as exc:
            errors.append(exc if isinstance(exc, LoginApiError)
                          else LoginApiError('hoyolab_accounts', exc=exc))
            if not cookie_token_ready:
                raise errors[-1] from None
    url = 'https://api-account-os.hoyolab.com/account/binding/api/getUserGameRolesByCookieToken'
    operations = {'hk4e_global': 'hoyolab_roles_genshin',
                  'hkrpg_global': 'hoyolab_roles_hsr', 'nap_global': 'hoyolab_roles_zzz'}
    for biz in ('hk4e_global', 'hkrpg_global', 'nap_global'):
        try:
            rsp = login_request(http, operations[biz],
                url + '?' + urlencode({'game_biz': biz}), headers=headers, notify=notify)
            if (not isinstance(rsp, dict) or type(rsp.get('retcode')) is not int
                    or rsp['retcode'] != 0 or not isinstance(rsp.get('data'), dict)
                    or not isinstance(rsp['data'].get('list'), list)):
                raise LoginApiError(operations[biz], response=rsp)
            rows = rsp['data']['list']
            for row in rows:
                if not isinstance(row, dict):
                    continue
                result.append(SimpleNamespace(game_biz=row.get('game_biz') or biz,
                    uid=str(row.get('game_uid') or row.get('uid') or ''),
                    region=str(row.get('region') or '')))
        except Exception as exc:
            errors.append(exc if isinstance(exc, LoginApiError)
                          else LoginApiError(operations[biz], exc=exc))
    if not result and errors:
        raise errors[-1] from None
    return result


async def _discover_hoyolab_accounts(cookie, notify=None):
    """Prefer genshin.py; fall back to verified global read-only role API."""
    try:
        import genshin
        client = genshin.Client()
        client.set_cookies(cookie)
        try:
            accounts = await client.get_game_accounts()
        finally:
            await close_hoyo_client(client)
        # A valid empty/non-Asia list is an account-selection outcome, not an
        # auth error. Do not turn it into a failure from a different token API.
        if accounts is not None:
            return accounts
    except Exception as exc:
        # Do not emit library exception text: it may contain cookies or URLs.
        if notify:
            from .login_diagnostics import error_summary
            notify('hoyolab_accounts ' + error_summary(exc))
    return await asyncio.to_thread(_direct_hoyolab_roles, cookie, notify=notify)


def choose_hoyolab_uids(accounts):
    """게임 종류/UID/지역이 동시에 맞는 *아시아* 캐릭터만 반환한다.

    계정 목록에 여러 아시아 캐릭터가 있으면 임의 선택하지 않는다.
    그런 경우 관리자가 후속 설정을 할 수 있게 후보 개수를 보고한다.
    """
    from .account_sources import _asia_uid
    grouped = {"genshin": [], "hsr": [], "zzz": []}
    for acct in accounts:
        biz = str((acct.get("game_biz", "") if isinstance(acct, dict) else getattr(acct, "game_biz", "")) or "").lower()
        uid = str((acct.get("game_uid") or acct.get("uid") if isinstance(acct, dict) else getattr(acct, "uid", "")) or "")
        region = str((acct.get("region") or acct.get("server", "") if isinstance(acct, dict)
                      else getattr(acct, "region", "") or getattr(acct, "server", "")) or "").lower()
        match = ("genshin" if "hk4e" in biz or "genshin" in biz else
                 "hsr" if "hkrpg" in biz or "starrail" in biz else
                 "zzz" if "nap" in biz or "zzz" in biz else None)
        if match and _asia_uid(match, uid):
            # genshin.py exposes API `region` as `server`. Match the public
            # server identifiers; an unknown supplied region must not enable sync.
            expected = {'genshin': 'os_asia', 'hsr': 'prod_official_asia',
                        'zzz': 'prod_gf_jp'}[match]
            if region and region not in (expected, 'asia'):
                continue
            grouped[match].append(uid)
    resolved = {game: ids[0] for game, ids in grouped.items() if len(set(ids)) == 1}
    uncertain = [game for game, ids in grouped.items() if len(set(ids)) > 1]
    return resolved, uncertain


def connect_hoyolab(config_path):
    """실제 로그인이 확인된 경우에만 설정 enabled=True를 보존한다."""
    from .hoyolab_login import import_logged_in_browser
    import_logged_in_browser()
    cookie = read_secret("hoyolab")
    accounts = asyncio.run(_discover_hoyolab_accounts(cookie))
    uids, uncertain = choose_hoyolab_uids(accounts)
    if not uids:
        raise RuntimeError("로그인 계정에서 지원되는 아시아 서버 캐릭터를 찾지 못했습니다")
    def apply(cfg):
        h = cfg.setdefault("hoyolab", {})
        h.setdefault("uids", {}).update(uids)
        h["enabled"] = True
        cfg.setdefault("account_data", {})["enabled"] = True
    write_settings(config_path, apply)
    return f"HoYoLAB 연결: {', '.join(uids)}" + (f" (중복 계정 확인 필요: {', '.join(uncertain)})" if uncertain else "")


def _browser_domain_cookies(domains):
    """요청한 특정 게임사 도메인 쿠키만 반환. 브라우저 전체 쿠키는 저장 금지."""
    try:
        import browser_cookie3
    except ImportError as exc:
        raise RuntimeError("python -m pip install browser-cookie3 필요") from exc
    output = []
    for browser in ("edge", "chrome", "firefox", "chromium"):
        loader = getattr(browser_cookie3, browser, None)
        if loader is None:
            continue
        for domain in domains:
            try:
                # 도메인별 필터링. 브라우저 보호 정책으로 읽을 수 없으면 다음 브라우저 시도.
                for c in loader(domain_name=domain):
                    if any(c.domain.lstrip('.').endswith(d) for d in domains):
                        output.append((c.name, c.value))
            except Exception:
                continue
    return output


def _single_token(cookies, names):
    tokens = {v for name, v in cookies if name in names and isinstance(v, str) and len(v) > 15}
    return next(iter(tokens)) if len(tokens) == 1 else None


def list_asia_endfield_roles(binding):
    """SKPORT 바인딩의 모든 Asia 캐릭터를 닉네임과 함께 반환한다.

    동일 UID가 defaultRole과 roles에 중복되는 사례를 제거한다.
    글로벌 서버는 serverId=2이며, 서버명 언어가 달라도 찾아낸다.
    """
    found = {}
    for entry in (binding.get("data") or {}).get("list", []):
        if entry.get("appCode") != "endfield":
            continue
        for group in entry.get("bindingList", []):
            for role in [group.get("defaultRole") or {}, *(group.get("roles") or [])]:
                server_name = str(role.get("serverName") or "").lower()
                rid = str(role.get("roleId") or "")
                sid = str(role.get("serverId") or "")
                # An explicit region name wins over a legacy serverId hint.
                if any(t in server_name for t in ("america", "europe", "美服", "欧服", "北美", "유럽", "미주", "china", "中国")):
                    continue
                if sid != "2" and not any(t in server_name for t in ("asia", "亚洲", "亞洲", "아시아", "アジア")):
                    continue
                if rid.isdigit() and sid:
                    found[(rid, sid)] = {"role_id": rid, "server_id": sid,
                                        "nickname": str(role.get("nickname") or "이름 없음")}
    return list(found.values())


def select_asia_endfield_role(binding):
    """기존 CLI와의 호환을 위해 한 개일 때만 자동 선택."""
    found = list_asia_endfield_roles(binding)
    return (found[0]["role_id"], found[0]["server_id"]) if len(found) == 1 else None


def _skport_browser_account_token():
    """SKPORT 웹사이트의 *공식* 계정 토큰 응답만 읽는다.

    일부 브라우저는 account_token 쿠키를 보관하지 않고 서버의
    /cookie_store/account_token 응답에서만 토큰을 반환한다.
    로그인된 사용자가 가진 같은 도메인의 쿠키를 SKPORT에만 전송한다.
    """
    cookies = _browser_domain_cookies(("skport.com",))
    if not cookies:
        return None
    from urllib.request import Request, urlopen
    # SKPORT 도메인 이외로 Cookie 전송 금지. 비밀을 로컬 로그에 남기지 않음.
    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies)
    request = Request("https://web-api.skport.com/cookie_store/account_token",
                      headers={"Cookie": cookie_header,
                               "Accept": "application/json", "User-Agent": "GameTodo/0.6.1"})
    with urlopen(request, timeout=12) as response:
        if not response.url.startswith("https://web-api.skport.com/"):
            raise ValueError("SKPORT가 아닌 외부 주소로 변경된 로그인 응답")
        data = json.load(response)
    if not isinstance(data, dict):
        return None
    candidate = data.get("data", data)
    if isinstance(candidate, dict):
        candidate = candidate.get("content") or candidate.get("account_token")
    return candidate if isinstance(candidate, str) and len(candidate) > 15 else None


def connect_skport(config_path):
    """공식 웹 로그인 후 사용자 브라우저에 실린 계정 토큰이 보이면 자동 연결."""
    cookies = _browser_domain_cookies(("skport.com", "gryphline.com"))
    token = _single_token(cookies, ("account_token", "accountToken"))
    if not token:
        token = _skport_browser_account_token()
    if not token:
        raise RuntimeError("SKPORT 웹 로그인에서 토큰 확인 불가. 브라우저 보호 정책 또는 사이트 변경 가능")
    from .skport import Skport
    # 비밀값을 저장하기 전에 API가 읽기 전용 계정 바인딩에 성공하는지 검증.
    roles = Skport(token).binding()
    selected = select_asia_endfield_role(roles)
    if not selected:
        raise RuntimeError("연결된 아시아 서버 엔드필드 캐릭터가 없거나 여러 개입니다")
    def apply(cfg):
        ad = cfg.setdefault("account_data", {})
        ad["enabled"] = True
        ad.setdefault("endfield", {}).update({"enabled": True, "role_id": selected[0], "server_id": selected[1]})
    save_secret("skport", token)
    write_settings(config_path, apply)
    return "SKPORT/엔드필드 아시아 서버 연결 완료"


def select_asia_kuro_role(data):
    """KuroBBS role 목록의 서버명이 명시적 Asia인 경우만 자동 선택."""
    rows = (data.get("data") or []) if isinstance(data, dict) else []
    if isinstance(rows, dict):
        rows = rows.get("list") or rows.get("roleList") or []
    found = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("serverName") or "").lower()
        if not any(v in name for v in ("asia", "sea", "亚洲", "아시아", "东南亚")):
            continue
        rid = str(row.get("roleId") or "")
        sid = str(row.get("serverId") or "")
        if rid.isdigit() and sid:
            found.append((rid, sid))
    return next(iter(set(found))) if len(set(found)) == 1 else None


def connect_kurobbs(config_path):
    """중국 KuroBBS 로그인은 글로벌 명조 데이터 연결 기능이 아니다."""
    raise RuntimeError("명조 글로벌 로그인 기반 일일 데이터 API 미확인: KuroBBS 중국 서비스는 사용하지 않습니다")
