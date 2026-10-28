"""게임 식별자 -> Todoist 제목 접두사·라벨. 모든 화면/동기화 기능의 단일 기준."""
from dataclasses import dataclass


@dataclass(frozen=True)
class GameProfile:
    name: str
    prefix: str
    label: str


GAMES = {
    "genshin": GameProfile("원신", "원신", "원신"),
    "hsr": GameProfile("붕괴: 스타레일", "열차", "스타레일"),
    "zzz": GameProfile("젠레스 존 제로", "젠존제", "젠레스존제로"),
    "wuthering": GameProfile("명조: 워더링 웨이브", "명조", "명조:워더링웨이브"),
    "limbus": GameProfile("림버스 컴퍼니", "림컴", "림버스컴퍼니"),
    "stella": GameProfile("스텔라 소라", "스소", "스텔라소라"),
    "reverse1999": GameProfile("리버스: 1999", "립9", "리버스1999"),
    # 수동 할 일/플로팅 식별용. 개인 진행도/가챠 자동 수집은 활성화하지 않는다.
    "colorsweeper": GameProfile("컬러스위퍼", "색지뢰", "컬러스위퍼"),
    "arknights": GameProfile("명일방주", "명방", "명일방주"),
    "endfield": GameProfile("명일방주: 엔드필드", "엔필", "명일방주:엔드필드"),
}


def title_for(game: str, name: str) -> str:
    """이미 접두사가 있거나 과거 버전에서 넘어온 경우 중복 부착하지 않음."""
    import re
    profile = GAMES[game]
    stripped = name.strip()
    existing = re.match(r"^\s*\[([^\]]+)\]\s*", stripped)
    if existing and existing.group(1) in {g.prefix for g in GAMES.values()} | {"이벤트"}:
        stripped = stripped[existing.end():].strip()
    return f"[{profile.prefix}] {stripped}"


def task_game(task: dict) -> str | None:
    """이름, 라벨, 설명에 명시된 게임이 하나로 확정될 때만 반환."""
    import re
    title = task.get("content") or ""
    labels = set(task.get("labels") or [])
    desc = task.get("description") or ""
    found = set()
    # 명시적 GameTodo 표식이 최우선, 기존 수동 Todo는 접두사/라벨 판별
    marker = re.search(r"(?m)^게임:\s*(\w+)\s*/\s*서버:", desc)
    if marker and marker.group(1) in GAMES:
        return marker.group(1)
    for key, profile in GAMES.items():
        if title.startswith(f"[{profile.prefix}]") or profile.label in labels:
            found.add(key)
    return next(iter(found)) if len(found) == 1 else None
