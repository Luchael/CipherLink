"""한국/아시아 서버의 '게임 회차'와 Todoist의 날짜를 분리한다.

배경: Todoist는 반복 작업을 완료하면 다음 날짜로 옮긴다. 따라서 한국 시간
00:00~04:59에 *전날*의 게임 데이터를 보고 체크하면 오늘 새로 시작할 작업을
건너뛸 수 있다. 이 모듈은 해당 시간에 자동 완료를 **전면 금지**한다.

초기화 시간은 KST이며, 지원이 확인되지 않은 게임은 안전하게 감지를 멈춘다.
계정 데이터를 조회하는 시각과 완료를 허용하는 시각은 별개의 문제다.
"""
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

KST = timezone(timedelta(hours=9))

# HoYoverse 아시아 및 명조 아시아: 게임 서버 UTC+8 04:00 -> KST 05:00.
# 다른 서버의 시간을 추측하지 않는다. 설정 파일로 확인된 시간만 추가한다.
RESET_WEEKDAY_KST = {"limbus": 3}  # 림버스 컴퍼니: 목요일 06:00 주간 갱신

RESET_HOURS_KST = {"genshin": 5, "hsr": 5, "zzz": 5, "wuthering": 5,
                   "endfield": 5, "limbus": 6, "arknights": 4}


@dataclass(frozen=True)
class Period:
    kind: str
    key: str
    starts_at: datetime


def reset_time(game: str, hours=None, times=None) -> time | None:
    """레거시 정수 설정(reset_hours_kst)과 새 HH:MM 설정을 함께 지원한다."""
    hours, times = hours or {}, times or {}
    if game in times:
        value = times[game]
        if not isinstance(value, str):
            return None
        try:
            parts = value.split(":")
            if len(parts) != 2 or any(not x.isdigit() for x in parts):
                return None
            hh, mm = [int(x) for x in parts]
            return time(hh, mm)
        except ValueError:
            return None
    value = hours.get(game, RESET_HOURS_KST.get(game))
    return time(value) if type(value) is int and 0 <= value <= 23 else None


def daily_boundary(game: str, now: datetime, hours=None, times=None) -> datetime | None:
    """오늘(KST)의 게임 초기화 시각. 이전 회차 시작 시각과는 다르다."""
    t = reset_time(game, hours, times)
    local = now.astimezone(KST)
    return datetime.combine(local.date(), t, tzinfo=KST) if t is not None else None


def before_today_reset(game: str, now: datetime, hours=None, times=None) -> bool:
    """오늘의 초기화가 아직 오지 않았거나 시각을 알 수 없으면 True."""
    bound = daily_boundary(game, now, hours, times)
    return bound is None or now.astimezone(KST) < bound


def cycle_start(game: str, now: datetime, overrides=None) -> datetime | None:
    """v0.4.x에서 사용하던 '가장 최근의 일일 회차 시작' 함수도 유지."""
    bound = daily_boundary(game, now, hours=overrides)
    if bound is None:
        return None
    return bound if now.astimezone(KST) >= bound else bound - timedelta(days=1)


def cycle_label(game: str, now: datetime, overrides=None) -> str | None:
    start = cycle_start(game, now, overrides)
    return start.date().isoformat() if start else None


def reset_buffer(game: str, now: datetime, overrides=None, minutes=20) -> bool:
    """게임 초기화 직후 캐시 지연을 고려해 완료를 잠시 막는다."""
    start = cycle_start(game, now, overrides)
    if start is None:
        return True
    return start <= now.astimezone(KST) < start + timedelta(minutes=minutes)


def current_period(game: str, kind: str, now: datetime, hours=None, times=None,
                   until_timestamp: int | None = None, weekdays=None) -> Period | None:
    """일일/주간/서버가 종료 시각을 알리는 콘텐츠의 회차를 구분한다.

    - daily: 오늘 게임 초기화 ~ 다음 날 초기화
    - weekly: 월요일 게임 초기화 ~ 다음 주 월요일 초기화
    - rotation: 서버가 제공한 다음 갱신 시각을 고유 회차 ID로 사용.
      주기를 임의로 2주라고 추측하지 않는다.
    """
    local = now.astimezone(KST)
    bound = daily_boundary(game, local, hours, times)
    if bound is None or local < bound:
        return None  # 당일 초기화 전에는 전날 데이터라도 체크 불가
    if kind == "daily":
        return Period(kind, f"daily:{bound.date().isoformat()}", bound)
    if kind == "weekly":
        weekly_day = (weekdays or {}).get(game, RESET_WEEKDAY_KST.get(game, 0))
        if type(weekly_day) is not int or weekly_day not in range(7):
            return None
        start = bound - timedelta(days=(bound.weekday() - weekly_day) % 7)
        return Period(kind, f"weekly:{start.date().isoformat()}", start)
    if kind == "rotation":
        # 필드가 실제 다음 갱신 시간인 경우에만 사용하며 값이 없으면 무시.
        if type(until_timestamp) is not int or until_timestamp <= 0:
            return None
        expiry = datetime.fromtimestamp(until_timestamp, tz=KST)
        if not local < expiry < local + timedelta(days=90):
            return None
        return Period(kind, f"rotation:until:{until_timestamp}", bound)
    return None


def due_date_kst(task: dict) -> date | None:
    """Todoist due.date(날짜 또는 timezone 포함 ISO 문자열)를 KST 날짜로 읽기.

    일정이 *없는* 할 일은 자동 완료하지 않는다. '오늘 또는 과거'라는 사용자 규칙을
    판정할 수 없기 때문이다.
    """
    due = task.get("due") or {}
    raw = due.get("datetime") or due.get("date")
    if not isinstance(raw, str) or not raw:
        return None
    try:
        if "T" in raw or " " in raw:
            value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if value.tzinfo is None:
                # 무시간대 문자열은 명시적인 사용자 설정 없이는 보수적으로 사용 금지.
                return None
            return value.astimezone(KST).date()
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def due_is_eligible(task: dict, now: datetime) -> bool:
    due = due_date_kst(task)
    return due is not None and due <= now.astimezone(KST).date()
