"""실계정의 API 구조를 비밀정보 노출 없이 분석한다.

외부 공개 라이브러리는 API 필드가 바뀌기도 한다. 계정의 전체 JSON을 개발자나
채팅에 보내는 대신 각 경로의 '키 이름과 타입'만 보고서로 만든다.
절대로 쿠키·UID·닉네임·개인 기록의 값 자체를 저장하지 않는다.
"""
from collections.abc import Mapping

# 비밀정보가 포함될 수 있는 키는 값뿐 아니라 키 아래 구조도 출력을 막는다.
PRIVATE = ("token", "cookie", "secret", "email", "password", "phone", "auth", "name", "uid", "roleid", "account", "device")


def to_structure(obj, depth=0, limit=4):
    """객체를 키/형식/몇 개의 값이 있는지 정보로만 변환한다."""
    if depth >= limit:
        return type(obj).__name__
    if not isinstance(obj, (Mapping, list, tuple)):
        convert = getattr(obj, 'model_dump', None) or getattr(obj, 'dict', None)
        if callable(convert):
            try:
                obj = convert()
            except Exception:
                return type(obj).__name__
    if isinstance(obj, Mapping):
        result = {}
        for k, value in list(obj.items())[:120]:
            key = str(k)
            if key.isdigit() or any(p in key.casefold() for p in PRIVATE):
                continue
            result[key] = to_structure(value, depth+1, limit)
        return result
    if isinstance(obj, (list, tuple)):
        return {'type': 'list', 'item_count': len(obj),
                'sample_schema': to_structure(obj[0], depth+1, limit) if obj else None}
    return type(obj).__name__
