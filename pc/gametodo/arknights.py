"""명일방주 한국 서버 계정 조회 (ArkPRTS 활용, 완전 읽기 전용).

- 공식 제공 API가 아닌 커뮤니티 라이브러리를 사용한다.
- account/syncData 한 번만 요청하며 보상 수령/게임 조작 요청을 보내지 않는다.
- 로그인 토큰은 `auth arknights`로 기기에 1회 저장하고 출력하지 않는다.
- 사용자 요청에 따라 일일 목표 점수 current/max가 모두 조회될 때만 완료 판정.
- 이성(AP) 수치는 임무 점수가 아니므로 절대 완료 근거로 사용하지 않는다.

참고: https://github.com/ashleney/ArkPRTS
"""
import asyncio

from .credentials import read_secret
from .live_data import Status, Gauge


async def _fetch_kr(channel_uid: str, token: str):
    try:
        import arkprts
    except ImportError as exc:
        raise RuntimeError("명일방주 조회 의존성 필요: python -m pip install arkprts") from exc
    # kr을 명시하여 영어/일본/중국 서버 계정 혼입을 방지한다.
    # ArkPRTS README에 명시된 사용자 인증 절차.
    auth = arkprts.YostarAuth("kr")
    await auth.login_with_token(channel_uid, token)
    client = arkprts.Client(auth=auth, assets=False)
    try:
        return await client.get_raw_data()
    finally:
        # 버전별 close 지원 방식 차이 대응
        close = getattr(client, "close", None)
        if callable(close):
            result = close()
            if asyncio.iscoroutine(result):
                await result
        else:
            network = getattr(client, "network", None)
            close_network = getattr(network, "close", None)
            if callable(close_network):
                result = close_network()
                if asyncio.iscoroutine(result):
                    await result


def parse_arknights(payload):
    """민감한 계정 원문은 반환/저장하지 않고 요약만 만든다."""
    if not isinstance(payload, dict) or not isinstance(payload.get("user"), dict):
        raise ValueError("ArkPRTS 사용자 데이터가 올바르지 않음")
    user = payload["user"]
    status = user.get("status", {})
    if not isinstance(status, dict):
        raise ValueError("ArkPRTS status 형식 변경")
    # 상태값은 한국어로 표시할 수 있으나, 'AP 가득 참'을 일퀘 완료로 잘못 판단하면 안 된다.
    sanity = status.get("ap")
    max_sanity = status.get("maxAp")
    level = status.get("level")
    info = {"sanity": f"{sanity}/{max_sanity}" if type(sanity) is int and type(max_sanity) is int else "정보 없음"}
    if type(level) is int:
        info["level"] = level
    # 임무 점수는 라이브러리/버전에 따라 위치가 다를 수 있다. 현재값과 최대값이
    # 모두 있는 명시적인 일일 임무 점수만 사용한다. AP/레벨/임의의 100점 가정 금지.
    from .live_data import gauge
    daily = gauge(user, ("mission.daily.progress", "mission.daily.current"),
                       ("mission.daily.maxProgress", "mission.daily.max"))
    return Status("arknights", "ArkPRTS KR", daily, None, info,
                  "명시적 일일 임무 점수의 현재/최대치가 모두 있으면 Todoist 완료")


def read_arknights(config):
    cfg = (config.get("account_data") or {}).get("arknights") or {}
    channel_uid = str(cfg.get("channel_uid") or "").strip()
    if not channel_uid.isdigit():
        raise ValueError("arknights.channel_uid 미설정")
    token = read_secret("arknights")
    if not token:
        raise ValueError("명일방주 Yostar 인증 토큰 미설정: auth arknights")
    raw = asyncio.run(_fetch_kr(channel_uid, token))
    return channel_uid, parse_arknights(raw)

async def _login_kr_email(email: str, code_callback):
    """최초 1회 Yostar 한국 서버 로그인. 이후 저장된 토큰 재사용.

    ArkPRTS 문서의 get_token_from_email_code 흐름. 호출자가 이메일 인증 코드를
    현 기기에서 입력하며 계정 토큰은 함수 바깥에 기록하지 않는다.
    로그인 방식 자체가 게임 클라이언트 세션에 영향을 줄 수 있어 사용자가 명시적으로 실행해야 한다.
    """
    try:
        import arkprts
    except ImportError as exc:
        raise RuntimeError("python -m pip install arkprts 필요") from exc
    auth = arkprts.YostarAuth("kr")
    await auth.send_email_code(email)
    code = code_callback()  # 비밀 숫자는 로그로 출력하지 않는다.
    if not code or not str(code).strip():
        raise ValueError("이메일 인증 코드 미입력")
    uid, token = await auth.get_token_from_email_code(email, str(code).strip())
    if not uid or not token:
        raise ValueError("Yostar 로그인 응답에 UID/토큰 없음")
    return str(uid), str(token)


def login_arknights_kr(config_path: str):
    """사용자 명시적 실행에서만 호출. 기존 설정 다른 부분은 보존."""
    import getpass
    import json
    from pathlib import Path
    from .credentials import save_secret
    # 이 과정은 읽기 전용 API를 위한 로그인이라도 실제 게임 세션을 끊을 수 있다.
    # 사용자가 직접 실행하더라도 위험을 명확히 인지하고 동의해야 한다.
    print("주의: Yostar 개인 계정 인증은 현재 게임 연결을 강제 종료할 수 있습니다.")
    print("게임 진행 중에는 실행하지 마세요. 자동 조회 기능은 비활성화되어 있습니다.")
    consent = input("위험을 이해했다면 '동의' 입력 (그 외는 취소): ").strip()
    if consent != "동의":
        raise RuntimeError("명일방주 계정 연결을 취소했습니다. 게임에는 접근하지 않았습니다.")
    email = input("명일방주 한국 서버 Yostar 이메일 (기기 로컬 입력): ").strip()
    if not email or "@" not in email:
        raise ValueError("이메일 형식 오류")
    print("인증 메일을 전송합니다. 메일함에서 숫자 코드를 확인하세요.")
    uid, token = asyncio.run(_login_kr_email(email, lambda: getpass.getpass("메일 인증 코드: ")))
    # 인증 성공 후에만 설정 파일 갱신. 사용자 지정값은 유지한다.
    p = Path(config_path)
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg.setdefault("account_data", {}).setdefault("arknights", {})["channel_uid"] = uid
    cfg["account_data"]["arknights"]["enabled"] = True
    cfg["account_data"]["enabled"] = True
    save_secret("arknights", token)
    p.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("명일방주 한국 서버 로그인 정보 저장됨. 토큰/이메일은 출력하지 않습니다.")
