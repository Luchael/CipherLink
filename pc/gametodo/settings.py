"""사용자 설정. 인증 토큰은 별도 로컬 인증 저장소 또는 환경 변수에서 읽기."""
import json
import os
from pathlib import Path

DEFAULT_GAMES = {
    "genshin": {"enabled": True, "name": "원신", "source": "pickupcal", "slug": "genshin"},
    "hsr": {"enabled": True, "name": "붕괴: 스타레일", "source": "pickupcal", "slug": "hsr"},
    "zzz": {"enabled": True, "name": "젠레스 존 제로", "source": "pickupcal", "slug": "zzz"},
    "wuthering": {"enabled": True, "name": "명조: 워더링 웨이브", "source": "pickupcal", "slug": "wuthering"},
    "limbus": {"enabled": True, "name": "림버스 컴퍼니", "source": "pickupcal", "slug": "limbus"},
    "endfield": {"enabled": True, "name": "명일방주: 엔드필드", "source": "pickupcal", "slug": "endfield"},
    "reverse1999": {"enabled": False, "name": "리버스: 1999", "source": "unverified", "slug": ""},
    "arknights": {"enabled": False, "name": "명일방주", "source": "unverified", "slug": ""},
    "stella": {"enabled": False, "name": "스텔라 소라", "source": "unverified", "slug": ""},
}


def load_settings(path: str) -> dict:
    settings = json.loads(Path(path).read_text(encoding="utf-8"))
    settings.setdefault("section_name", "이벤트 / 기간 한정")
    # 0.1 설정의 endfield.enabled=false는 '추후 추가 예정'이었던 값.
    # 업그레이드 시 자동으로 켜고, 0.2 형식에서는 사용자 선택을 존중.
    if int(settings.get("schema_version", 1)) < 2:
        settings.setdefault("game_settings", {}).setdefault("endfield", {})["enabled"] = True
    settings.setdefault("account_data", {})
    settings["account_data"].setdefault("enabled", False)
    # v0.4.1: 목표 점수만 채워도 Todoist를 완료하도록 기본 활성화.
    # 실제 게임 보상 수령과 다를 수 있으며 false로 되돌릴 수 있다.
    settings["account_data"].setdefault("score_goal_counts_as_complete", True)
    settings["account_data"].setdefault("interval_minutes", 20)
    settings["account_data"].setdefault("wuthering", {"enabled": False})
    # 글로벌 명조는 중국 KuroBBS 조회 불가. 이전 버전에서 enabled=true였어도
    # 새 데이터 출처가 검증되기 전까지 자동 조회를 허용하지 않는다.
    # 구 중국 KuroBBS 토큰을 글로벌 계정과 오인하지 않도록 기존 강제 차단 유지.
    settings["account_data"]["wuthering"]["enabled"] = False
    settings["account_data"].setdefault("endfield", {"enabled": False})
    settings["account_data"].setdefault("arknights", {"enabled": False})
    settings["account_data"].setdefault("game_lookup", {})
    settings.setdefault("poll_hours", 6)
    # 일반 이벤트 수집 기능은 제거. 기존 game_settings는 픽업 출처로만 사용.
    settings.setdefault("banner_sync", {"enabled": True})
    settings.setdefault("min_event_duration_minutes", 15)
    settings.setdefault("game_settings", {})
    merged = {k: dict(v) for k, v in DEFAULT_GAMES.items()}
    for key, value in settings["game_settings"].items():
        if key == "colorsweeper":
            # 수동 할 일/플로팅은 지원하되 구설정의 자동 수집은 활성화하지 않는다.
            continue
        if key not in merged:
            raise ValueError(f"알 수 없는 게임 키: {key}")
        merged[key].update(value)
    settings["game_settings"] = merged
    if not 0.25 <= float(settings["poll_hours"]) <= 72:
        raise ValueError("poll_hours는 0.25~72 범위 (15분 이상)")
    return settings


def get_token() -> str:
    from .credentials import read_secret
    # 공식 OAuth 로그인 우선: 만료되면 refresh_token으로 자동 갱신.
    # 기존 0.5.x 토큰도 호환되도록 로컬에 저장된 개인 토큰을 보조 지원.
    from .oauth_login import get_oauth_token
    token = os.environ.get("TODOIST_API_TOKEN", "").strip() or get_oauth_token() or (read_secret("todoist") or "")
    if not token:
        raise RuntimeError("Todoist 로그인이 필요합니다. python -m gametodo login-todoist 를 실행하세요.")
    return token
