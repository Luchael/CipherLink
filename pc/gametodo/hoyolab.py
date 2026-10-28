"""이전 버전의 원신 전용 수동 점검 명령과 호환되는 HoYoLAB 연결부.

최신 계정 감시와 동일하게 '일퀘 목표 달성' 기준을 적용한다.
HoYoLAB 웹 출석체크와 실제 게임 일퀘는 서로 다르다.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import logging
import time

from .credentials import read_secret

LOG = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))


def genshin_daily_claimed(note) -> bool:
    """구 명령에서도 원신 의뢰 4/4이면 보상 수령 플래그 없이 완료로 판단."""
    from .live_data import genshin_status
    return genshin_status(note).safe_to_close


def reset_cycle_date(now=None) -> str:
    """원신 아시아 서버 일일 초기화는 KST 05:00 기준."""
    now = now or datetime.now(KST)
    return (now - timedelta(hours=5)).date().isoformat()


async def request_genshin(uid: int, cookie: str):
    try:
        import genshin  # optional dependency
    except ImportError as exc:
        raise RuntimeError("HoYoLAB 조회에는 pip install genshin 이 필요합니다") from exc
    client = genshin.Client()
    client.set_cookies(cookie)
    # 라이브러리 버전 별 별칭을 지원하되 필드가 확인되지 않으면 자동완료하지 않음.
    get_notes = getattr(client, "get_genshin_notes", None) or client.get_notes
    try:
        return await get_notes(uid)
    finally:
        await client.close()


def check_once(settings, todoist, store, dry_run=False):
    """구버전 명령도 새 공통 회차/예정일 검증을 **반드시** 거친다.

    예전 구현은 오전 03:00에 전날 진행도로 Todoist를 닫는 우회 경로가 있었다.
    버전 0.5부터는 중복 로직을 삭제하고 공통 감시기로 위임한다.
    """
    from .account_watch import run_account_check
    if not (settings.get("hoyolab") or {}).get("enabled"):
        return "HoYoLAB 연동 꺼짐"
    results = run_account_check(settings, todoist, store, read_only=dry_run)
    for item in results:
        if item.get("game") == "genshin":
            return item.get("action", "원신 상태 조회 불가")
    return "원신 계정 UID 미설정 또는 감지 대상 아님"
