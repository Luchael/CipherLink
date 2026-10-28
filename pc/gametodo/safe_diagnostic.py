# -*- coding: utf-8 -*-
"""Explicit opt-in, *read-only* game API schema diagnostic. No secrets on disk.

Run locally: python -m gametodo.safe_diagnostic --config config.json
This writes numeric progress + tree shape ONLY; always inspect before sharing.
"""
from __future__ import annotations
import argparse
import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from .credentials import read_secret
from .hoyo_client import close_hoyo_client

_ALLOWED_KEY = re.compile(r'[A-Za-z][A-Za-z0-9_]{0,55}\Z')
_SECRET_KEY = re.compile(r'(cookie|token|secret|auth|passwd|password|session|signature|email|phone|device|nickname|name|avatar|icon|image|url|link|user|player|account|uid|role|id$|_id$|character|weapon|member|lineup|description|desc|title|text|key|hash|ip_address)', re.I)
_NUMBER_KEY = re.compile(r'(star|score|stella|medal|count|num|rank|progress|rate|floor|layer|round|start|end|begin|time|duration|current|maximum|total|schedule_type|difficulty|pass|clear|done|award|reward|percent|level|grade|status|stage|settle|finish)', re.I)
_DATE_VALUE = re.compile(r'\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?\Z')
ENUMS = {'S','S+','SS','A','B','C','D','v1','v2','true','false'}


def sanitize(value: Any, key: str = '', depth: int = 0) -> Any:
    """Whitelist-based scrubber: no raw strings, identifiers or URLs.

    Do not replace this with a blacklist of tokens in free text.
    """
    if depth >= 7: return '<depth_limit>'
    if value is None or type(value) is bool: return value
    if isinstance(value, dict):
        result = {}
        for name in sorted(value):
            if len(result) >= 36: break
            if type(name) is not str or not _ALLOWED_KEY.fullmatch(name) or _SECRET_KEY.search(name): continue
            result[name] = sanitize(value[name], name, depth + 1)
        result['_schema_key_count'] = len(value)
        return result
    if isinstance(value, (list, tuple)):
        result = {'_array_length': len(value),
                  '_first_samples': [sanitize(v, key, depth+1) for v in value[:3]]}
        if ('star' in key.lower() or 'medal_round' in key.lower()) and value:
            if all(type(x) is bool for x in value):
                result['_true_count'] = sum(value)
            elif all(type(x) is int and x in (0, 1) for x in value):
                result['_ones_count'] = sum(value)
        return result
    if type(value) in (float, int):
        if _NUMBER_KEY.search(key):return value
        if key=='year' and 2020<=value<=2045:return value
        if key=='month' and 1<=value<=12:return value
        if key=='day' and 1<=value<=31:return value
        if key in ('hour','minute','second') and 0<=value<=59:return value
        return '<number>'
    if isinstance(value, str):
        if _NUMBER_KEY.search(key) and _DATE_VALUE.fullmatch(value): return value
        if value in ENUMS and re.search('rank|rating|grade|ver', key, re.I): return value
        return '<string_redacted>'
    # Pydantic datetime etc. must not serialize account-specific raw values.
    return '<unknown>'

# Fallback names across genshin.py versions, fetched only when the user runs this CLI.
METHODS = {
  'genshin': {
    'spiral': ('get_genshin_spiral_abyss','get_spiral_abyss'),
    'theater': ('get_imaginarium_theater',),
  },
  'hsr': {
    'moc': ('get_starrail_challenge',),
    'pure_fiction': ('get_starrail_pure_fiction',),
    'apocalyptic': ('get_starrail_apc_shadow',),
    'arbitration': ('get_anomaly_arbitration',),
  },
  'zzz': {
    'shiyu': ('get_shiyu_defense',),
    'deadly': ('get_deadly_assault',),
  }
}

async def collect_hoyo(client: Any, game: str, uid: str, index: int) -> list[dict]:
    rows = []
    for mode, methods in METHODS.get(game, {}).items():
        fn = next((getattr(client, n, None) for n in methods if callable(getattr(client, n, None))), None)
        if fn is None:
            rows.append({'game':game, 'local_account_index':index, 'mode':mode,
                         'status':'method_unavailable'})
            continue
        for previous in (False, True):
            args = {'raw':True}
            if mode == 'arbitration':
                # current schedule_type=3 is confirmed in public wrapper.
                if previous: continue
                args['schedule_type'] = 3
            elif previous:
                # Only diagnostic experiment. Some versions reject this flag.
                args['previous'] = True
            label = 'previous_probe_unverified' if previous else 'default'
            try:
                response = await fn(int(uid), **args)
                # Return only sanitized schema; no raw response sent to disk.
                rows.append({'game':game, 'local_account_index':index, 'mode':mode,
                             'requested_period':label, 'status':'ok', 'schema':sanitize(response)})
            except Exception as exc:
                # Never serialize exception message: may contain a signed URL, UID, cookie.
                rows.append({'game':game, 'local_account_index':index, 'mode':mode,
                             'requested_period':label, 'status':'request_failed',
                             'error_type':type(exc).__name__[:48]})
            await asyncio.sleep(0.25)
    return rows

async def collect(config: dict) -> dict:
    report = {
        'format':'cipherlink_safe_schema_v2',
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'warning':'구체적인 날짜/점수 포함; 공유 전 직접 파일 검토 필요',
        'requests':[],
        'unsupported':[
            {'game':'wuthering_global','state':'global 개인 임무 API 미검증; CN KuroBBS 금지'},
            {'game':'arknights_kr_en_jp','state':'게임 강제 로그아웃 위험: private login 자동 요청 금지'}
        ]
    }
    cookie = read_secret('hoyolab')
    if not cookie:
        report['hoyolab_connected'] = False
        return report
    report['hoyolab_connected'] = True
    uid_map = (config.get('hoyolab') or {}).get('uids') or {}
    try:
        import genshin
    except ImportError:
        report['dependency'] = 'genshin.py_missing'
        return report
    client = genshin.Client()
    client.set_cookies(cookie)
    try:
        for game in ('genshin','hsr','zzz'):
            chosen = uid_map.get(game) or ((config.get('hoyolab') or {}).get('genshin_uid') if game == 'genshin' else None)
            uid = str(chosen or '').strip()
            if not uid.isdigit(): continue
            report['requests'].extend(await collect_hoyo(client, game, uid, 1))
    finally:
        await close_hoyo_client(client)
    return report

def main():
    parser = argparse.ArgumentParser(description='CipherLink 비식별 API 진단: 유저가 수동 실행')
    parser.add_argument('--config', default='config.json')
    parser.add_argument('--output', default='CipherLink_api_diagnostic_safe.json')
    args = parser.parse_args()
    from .settings import load_settings
    result = asyncio.run(collect(load_settings(args.config)))
    path = Path(args.output)
    if path.exists():
        raise SystemExit('기존 진단 파일을 덮어쓰지 않습니다. --output 으로 새 이름을 지정하세요.')
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print('완료: 비식별 스키마 파일 저장:', path.resolve())
    print('반드시 JSON 내용을 직접 확인한 뒤 공유하세요. 로그인/게임 진입 동작은 없습니다.')

if __name__ == '__main__': main()
