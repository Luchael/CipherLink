"""KR/아시아 일정용 표준 iCalendar(.ics) 읽기 전용 어댑터.

대상: 공식 한국 서버 캘린더, 사용자가 서버 일치 여부를 검증한 Google Calendar
공개 ICS 구독 주소. Google 로그인이나 별도 서비스 구동은 요구하지 않는다.

중요: 캘린더는 게임 계정의 '보상 수령 완료' 상태를 담지 않는다.
캘린더 데이터를 자동 완료 증거로 사용하는 코드는 절대 추가하지 않는다.
"""
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit
from ipaddress import ip_address
import re

from .models import Event, should_import, extract_short_name

KST = timezone(timedelta(hours=9))
ICAL_LINE = re.compile(r"^([^:]+):(.*)$")


def validate_ics_url(url: str) -> str:
    """임의 입력 URL로 로컬 서비스/장비를 요청하지 않도록 기본 검증."""
    if not isinstance(url, str) or len(url) > 1400:
        raise ValueError("ICS 주소가 없거나 너무 긺")
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host or parsed.username or parsed.password:
        raise ValueError("ICS 출처는 인증정보 없는 공개 HTTPS URL이어야 합니다")
    if host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        raise ValueError("로컬망 ICS 주소는 차단")
    try:
        ip = ip_address(host.strip('[]'))
    except ValueError:
        ip = None
    if ip and not ip.is_global:
        raise ValueError("사설망/루프백 IP 접근은 허용하지 않음")
    return url


def _unfold(ics: str) -> list[str]:
    """RFC5545 줄 이어쓰기: 공백 또는 탭으로 시작하면 전 행 끝에 합친다."""
    lines = []
    for line in ics.replace('\r\n','\n').replace('\r','\n').split('\n'):
        if line.startswith((' ', '\t')) and lines:
            lines[-1] += line[1:]
        else:
            lines.append(line)
    return lines


def _datetime_ics(meta: str, text: str, *, end=False):
    """지원 시간 형식: Asia/Seoul 부착, YYYYMMDD / YYYYMMDDTHHMMSS / UTC Z.

    원본 시간대를 추정해야 하는 비표준 캘린더는 위험하므로 건너뛴다.
    """
    meta = meta.upper()
    val = text.strip()
    if 'VALUE=DATE' in meta or re.fullmatch(r'\d{8}', val):
        dt = datetime.strptime(val, '%Y%m%d').replace(tzinfo=KST)
        # RFC5545 종일 이벤트 DTEND는 exclusive: 10/30 종료 -> 실제 종료 10/29
        return dt - timedelta(seconds=1) if end else dt
    if 'TZID=' in meta and not any(z in meta for z in ('TZID=ASIA/SEOUL','TZID=ASIA/TOKYO')):
        raise ValueError("한국/일본 시간 이외의 캘린더는 이 어댑터에서 지원 안 함")
    utc = val.endswith('Z')
    if not utc and 'TZID=' not in meta:
        raise ValueError("TZID 미지정 ICS 이벤트의 시간을 추정하지 않음")
    raw = val[:-1] if utc else val
    fmt = '%Y%m%dT%H%M%S' if len(raw) == 15 else '%Y%m%dT%H%M'
    dt = datetime.strptime(raw, fmt)
    return dt.replace(tzinfo=timezone.utc if utc else KST).astimezone(KST)


def _unescape(v: str) -> str:
    # ICS 내 문자 이스케이프. \\n은 줄바꿈(제목에선 공백으로 축약).
    return v.replace('\\n',' ').replace('\\N',' ').replace('\\,',',').replace('\\;',';').replace('\\\\','\\').strip()


def parse_ics(ics: str, game: str, url: str, verified_server: str):
    """명시적으로 KR 검증된 캘린더만 이벤트로 변환. RRULE은 중복 방지 위해 건너뜀."""
    if verified_server != 'KR':
        raise ValueError('한국 서버 출처 검증 실패: verified_server는 KR이어야 합니다')
    if not isinstance(ics, str) or 'BEGIN:VCALENDAR' not in ics:
        raise ValueError('유효한 iCalendar 데이터가 아님')
    events=[]
    entry=None
    for line in _unfold(ics):
        if line == 'BEGIN:VEVENT':
            entry={}
        elif line == 'END:VEVENT':
            if entry is None:
                continue
            try:
                if entry.get('STATUS', ('',''))[1].upper() == 'CANCELLED' or 'RRULE' in entry:
                    continue
                raw = _unescape(entry['SUMMARY'][1])
                if not should_import(raw, _unescape(entry.get('DESCRIPTION', ('',''))[1])):
                    continue
                start = _datetime_ics(*entry['DTSTART'])
                end = _datetime_ics(*entry['DTEND'], end=True)
                if end <= start:
                    continue
                events.append(Event(game,extract_short_name(raw),start,end,
                      entry.get('URL', ('',url))[1] or url,
                      _unescape(entry.get('DESCRIPTION',('',''))[1]),server='KR'))
            except (KeyError, ValueError):
                # 잘못된 항목 한 건 때문에 전체 일정 수집이 멈추지 않도록 보류.
                pass
            finally:
                entry=None
        elif entry is not None:
            match = ICAL_LINE.match(line)
            if match:
                lhs, val = match.groups()
                key = lhs.split(';',1)[0].upper()
                entry.setdefault(key, (lhs,val))
    return events


def fetch_ics(http, game: str, cfg: dict):
    url=validate_ics_url(cfg.get('ics_url',''))
    ics=http.request(url,cache=True)
    # 구독용 주소의 경로/쿼리에는 비공개 접근 키가 들어 있을 수 있다.
    # Todoist 설명에 원본 구독 주소를 쓰지 않고 사이트 루트만 사용한다.
    source_host = urlsplit(url).hostname
    safe_source = "https://" + source_host + "/"
    return parse_ics(ics,game,safe_source,cfg.get('verified_server',''))
