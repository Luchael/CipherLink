"""Unofficial public KR feed, with observed schema and independent period checks."""
from datetime import datetime
import re

SOURCE = 'https://api.ennead.cc/stella/banners?lang=KR'

def parse(payload, now):
    from .banners import Banner, KST
    if not isinstance(payload, dict) or not isinstance(payload.get('current'), list):
        raise ValueError('스텔라 KR 배너 응답 구조 변경')
    found = {}
    for row in payload['current']:
        if not isinstance(row, dict) or row.get('bannerType') != '여행가 기간 한정 모집':
            continue
        try:
            start, end = (datetime.fromisoformat(row[key]) for key in ('startTime', 'endTime'))
            if start.utcoffset() is None or end.utcoffset() is None:
                continue
            start, end = start.astimezone(KST), end.astimezone(KST)
            if not start <= now < end:
                continue
            entries = row['rateUp']['fiveStar']['entries']
            if not isinstance(entries, list):
                continue
            for entry in entries:
                name = entry.get('name') if isinstance(entry, dict) else None
                if (not isinstance(name, str) or not 1 <= len(name) <= 40 or
                    not re.search('[가-힣]', name) or any(ord(c) < 32 for c in name) or
                    any(c in name for c in ('/', ':', '[', ']'))):
                    continue
                b = Banner('stella', name.strip(), start, end, SOURCE)
                found[b.key] = b
        except (KeyError, TypeError, ValueError):
            continue
    return list(found.values())
