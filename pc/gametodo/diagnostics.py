"""사용자에게 보여 줄 안전한 오류 진단.

HTTP 요청의 원문(URL의 query, 응답 본문, 쿠키 등)에는 세션 비밀값이
들어 있을 수 있으므로 그 내용을 그대로 로그에 남기지 않는다.
"""
from urllib.error import HTTPError, URLError


def user_error(exc: Exception, stage: str = "") -> str:
    """오류 *종류와 해결 방향*만 전달한다. 원문 URL/헤더/토큰은 노출 금지."""
    prefix = (stage + ": ") if stage else ""
    from .embedded_login import LoginStepError
    if isinstance(exc, LoginStepError):
        # 이 오류는 고정된 안내 문구만 갖고 있어 인증 값이 출력되지 않는다.
        return f"{prefix}[{exc.stage}] {exc.reason}"
    if isinstance(exc, HTTPError):
        code = exc.code
        if code in (401, 403):
            return f"{prefix}HTTP {code} 인증 또는 접근 권한 오류. 연결 상태를 다시 확인하세요."
        if code == 404:
            return f"{prefix}HTTP 404 요청 API가 바뀌었거나 주소를 찾을 수 없습니다."
        if code == 429:
            return f"{prefix}HTTP 429 요청 제한. 잠시 후 다시 확인하세요."
        return f"{prefix}HTTP {code} 서버 응답 오류."
    if isinstance(exc, (URLError, TimeoutError, ConnectionError)):
        return f"{prefix}네트워크 연결·DNS·시간 초과 오류 ({type(exc).__name__})."
    if isinstance(exc, ImportError):
        return f"{prefix}필수 Python 라이브러리가 설치되지 않았습니다 ({type(exc).__name__})."
    if isinstance(exc, ValueError):
        # Todoist 섹션 없음/중복은 매우 흔한 초깃값 문제. 작업 제목을 로그로 노출하지 않는다.
        if "섹션" in str(exc):
            return f"{prefix}Todoist 대상 섹션이 없거나 중복되었습니다. 'Todoist 대상 위치 선택'을 실행하세요."
        return f"{prefix}입력 설정 또는 응답 형식 오류 ({type(exc).__name__})."
    if isinstance(exc, RuntimeError):
        return f"{prefix}프로그램/외부 API 처리 오류 ({type(exc).__name__}). 상세 정보는 설정과 연결 상태를 확인하세요."
    return f"{prefix}{type(exc).__name__} 오류. 연결 상태 및 설치 환경을 확인하세요."
