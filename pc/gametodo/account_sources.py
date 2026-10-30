"""게임 계정 데이터 제공자. 모든 요청은 상태 조회 전용 (POST도 읽기 전용 endpoint만).

비공식 API 이용은 이용 약관·서버 변경 및 계정 세션 만료의 영향을 받을 수 있다.
외부 서버에 Todoist 토큰을 전송하지 않는다.
"""
import asyncio
import time
_CRISIS_CACHE = {}
_WAR_RETRY = {}
_INDIE_RETRY = {}
from urllib.parse import urlencode

from .credentials import read_secret
from .http_client import HttpClient
from .hoyo_client import close_hoyo_client
from .live_data import (genshin_status, hsr_status, zzz_status,
                        wuthering_status, endfield_status)


async def _read_hoyolab_async(uid, cookie, game):
    try:
        import genshin
    except ImportError as exc:
        raise RuntimeError("선택 의존성 필요: python -m pip install genshin") from exc
    client = genshin.Client()
    client.set_cookies(cookie)
    try:
        methods = {"genshin": ("get_genshin_notes", "get_notes"),
                   "hsr": ("get_starrail_notes",),
                   "zzz": ("get_zzz_notes",)}
        method = next((getattr(client, n) for n in methods[game] if callable(getattr(client, n, None))), None)
        if method is None:
            raise RuntimeError("설치된 genshin.py 라이브러리가 이 게임의 상태 조회를 지원하지 않습니다")
        notes = await method(int(uid),return_raw_data=True,autoauth=False,lang="ko-kr")
        from .endgame_records import fetch as endgame_fetch
        endgame, errors = await endgame_fetch(client, uid, game)
        return notes, endgame, errors
    finally:
        await close_hoyo_client(client)


def _asia_uid(game, uid):
    v = str(uid).strip()
    # 2026년 글로벌 서버 기준: HoYoLAB 사용자 계정의 동일한 쿠키라도 UID별 서버 다름
    return v.isdigit() and {"genshin": v.startswith(("8", "18")),
                            "hsr": v.startswith(("8", "18")),
                            "zzz": v.startswith("13")}.get(game, False)


def read_hoyolab(game, config):
    cfg = config.get("hoyolab") or {}
    uid = str((cfg.get("uids") or {}).get(game) or
              (cfg.get("genshin_uid") if game == "genshin" else "") or "").strip()
    if not _asia_uid(game, uid):
        raise ValueError(f"{game}: 아시아 서버 UID가 미설정이거나 형식이 맞지 않음")
    cookie = read_secret("hoyolab")
    if not cookie:
        raise ValueError("HoYoLAB 쿠키 미설정: auth hoyolab")
    result = asyncio.run(_read_hoyolab_async(uid, cookie, game))
    notes, endgames, errors = result if isinstance(result, tuple) and len(result) == 3 else (result, {}, {})
    parser = {"genshin": genshin_status, "hsr": hsr_status, "zzz": zzz_status}[game]
    from .live_data import Gauge
    from dataclasses import replace
    status = parser(notes)
    # Diagnostics include only aggregate scores/errors, not raw account JSON or cookie.
    metrics = dict(status.metrics)
    expiry = dict(status.metric_expiries)
    windows = dict(status.metric_windows)
    for mode, row in endgames.items():
        metrics[mode] = Gauge(row.value, row.goal)
        if row.current() and row.ends is not None:
            expiry[mode] = row.ends
            windows[mode] = (row.starts, row.ends)
    details = dict(status.details)
    details['endgame_diagnostics'] = errors
    details['endgame_display'] = {mode: row.display_detail for mode,row in endgames.items()}
    details['endgame_scores'] = {k: f"{v.value}/{v.goal} ({v.basis}; {'현재' if v.current() else '회차 미확인'})" for k,v in endgames.items()}
    return uid, replace(status, metrics=metrics, metric_expiries=expiry, metric_windows=windows, details=details)


def read_wuthering(config, http=None):
    """중국 KuroBBS 조회 대신 글로벌 명조의 미지원 상태를 안전하게 알린다.

    기존 중국 `api.kurobbs.com` 토큰을 글로벌 API로 오인해 사용하는
    문제를 막는다. 검증된 글로벌 게임 플레이 API가 발견되기 전에는
    해당 게임의 자동 Todoist 체크를 건너뛰도록 호출자가 처리한다.
    """
    raise ValueError("명조 글로벌: 외부 일일 진행도 API 미확인, 중국 KuroBBS 호출 차단")


def read_endfield(config, http=None):
    cfg = (config.get("account_data") or {}).get("endfield") or {}
    role_id, server_id = str(cfg.get("role_id") or ""), str(cfg.get("server_id") or "")
    if not role_id.isdigit() or not server_id or len(server_id) > 80:
        raise ValueError("엔드필드 SKPORT role_id / Asia server_id를 설정하세요")
    account_token = read_secret("skport")
    if not account_token:
        raise ValueError("SKPORT 토큰 미설정: auth skport")
    from .skport import Skport
    service = Skport(account_token, http=http)
    # 계정 바인딩 서버를 먼저 확인하고, 동일 role/server에 대해서만 요청한다.
    info = service.binding()
    roles = []
    for entry in (info.get("data") or {}).get("list", []):
        if entry.get("appCode") != "endfield":
            continue
        for grp in entry.get("bindingList", []):
            roles.append(grp.get("defaultRole") or {})
            roles.extend(grp.get("roles") or [])
    selected = next((r for r in roles if str(r.get("roleId")) == role_id
                     and str(r.get("serverId")) == server_id), None)
    if not selected:
        raise ValueError("SKPORT 캐릭터 바인딩 미확인")
    server_name = str(selected.get("serverName") or "").lower()
    if any(x in server_name for x in ("america", "europe", "美服", "欧服", "北美", "유럽", "미주", "china", "中国")):
        raise ValueError("엔드필드 응답에 아시아 이외의 서버명이 있음")
    if not any(region in server_name for region in ("asia", "亚洲", "아시아", "アジア")) and not cfg.get("asia_server_verified", False):
        raise ValueError("엔드필드 서버명 확인 실패. 공식 도구에서 서버 검증 후 asia_server_verified를 켜세요")
    data = service.detail(role_id, server_id)
    key=(role_id,server_id)
    detail=data.get('data',{});detail=detail.get('detail',detail) if isinstance(detail,dict) else {}
    if isinstance(detail,dict) and not detail.get('indieHard') and time.time()>=_INDIE_RETRY.get(key,0):
        try:
            extra=service.indie_hard(role_id,server_id)
            from .endfield_longterm import body
            value=(body(extra) or {}).get('indieHard')
            if isinstance(value,dict):detail['indieHard']=value
            else:_INDIE_RETRY[key]=time.time()+3600
        except Exception:_INDIE_RETRY[key]=time.time()+3600
    saved=_CRISIS_CACHE.get(key,{})
    crisis=saved.get('window')
    if time.time()>=saved.get('retry_after',0):
        try:
            crisis=service.crisis_contract(role_id,server_id)
            from .endfield_longterm import crisis_progress
            parsed=crisis_progress(crisis)
            if parsed:_CRISIS_CACHE[key]={'window':parsed[2],'retry_after':0}
            else:
                _CRISIS_CACHE[key]={**saved,'retry_after':time.time()+3600};crisis=saved.get('window')
        except Exception:
            _CRISIS_CACHE[key]={**saved,'retry_after':time.time()+3600}
    war=None
    if time.time()>=_WAR_RETRY.get(key,0):
        try:
            war=service.war_echoes(role_id,server_id)
            if not isinstance((war.get('data') or {}).get('warEchoes'),dict):_WAR_RETRY[key]=time.time()+3600
        except Exception:_WAR_RETRY[key]=time.time()+3600
    return role_id, endfield_status(data, role_id, server_id,crisis,war=war)


def read_arknights(config):
    """명일방주 한국 서버 계정 상태. 상세 코드는 arknights.py 참조."""
    from .arknights import read_arknights as read
    return read(config)
