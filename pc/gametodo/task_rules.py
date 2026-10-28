"""기존 Todoist 제목과 외부 API 점수의 *명시적* 연결표.

일일, 주간, 엔드 콘텐츠는 서로 다른 초기화 주기를 사용한다.
비슷한 이름이라는 이유로 엉뚱한 게이지를 연결하지 않는다.

현재 안전하게 연결 가능한 기본 작업만 AUTO_BINDINGS에 넣었다.
예: 명조 weeklyData는 '주간퀘스트' 점수가 아니므로 여기에 추가하지 않는다.
     명조 towerData는 탑 점수이므로 [명조] 탑에만 연결한다.

새 게임의 데이터를 확인하면 아래 표에 한 줄 추가하되, 반드시 단위 테스트를 같이 만든다.
"""
from dataclasses import dataclass
from .live_data import Gauge, Status


@dataclass(frozen=True)
class Binding:
    game: str
    title: str
    kind: str     # daily / weekly / rotation
    metric: str   # daily 또는 Status.metrics에 있는 게이지의 키


def load_todoist_catalog() -> dict:
    """동일한 연결표를 Android assets와 함께 유지한다.

    manual 항목은 실계정 API의 완료 증거가 없어 자동완료 규칙에 넣지 않는다.
    """
    import json
    from pathlib import Path
    return json.loads((Path(__file__).resolve().parent.parent / "todoist_bindings.json").read_text(encoding="utf-8"))


def _default_bindings() -> tuple[Binding, ...]:
    result = []
    for item in load_todoist_catalog()["tasks"]:
        if item["status"] not in ("auto", "conditional"):
            continue
        if not item.get("metric"):
            continue
        # 조건부 명일방주 인증은 account_watch의 allow_arknights 및 23:59 정책이 별도 통제한다.
        # 명조 글로벌은 read_wuthering이 사용 불가를 명시적으로 거부한다.
        for title in (item["title"], *(item.get("aliases") or [])):
            result.append(Binding(item["game"], title, item["cadence"], item["metric"]))
    return tuple(dict.fromkeys(result))


AUTO_BINDINGS = _default_bindings()

def configured_bindings(settings: dict) -> tuple[Binding, ...]:
    """사용자 구설정의 일퀘 제목은 보존하고, 추가 매핑도 지원한다.

    custom_bindings 예시:
       {"game":"hsr", "title":"[열차] 모의우주 주간 포인트",
        "kind":"weekly", "metric":"rogue_weekly"}
    이름이 같더라도 센서가 직접 점수를 제공하지 않으면 완료되지 않는다.
    """
    cfg = settings.get("account_data") or {}
    names = cfg.get("task_names") or {}
    bindings = []
    for item in AUTO_BINDINGS:
        title = names.get(item.game, item.title) if item.kind == "daily" else item.title
        bindings.append(Binding(item.game, title, item.kind, item.metric))
    for raw in cfg.get("custom_bindings") or []:
        if not isinstance(raw, dict):
            continue
        game, title, kind, metric = (raw.get(key) for key in ("game", "title", "kind", "metric"))
        if (isinstance(game, str) and isinstance(title, str) and title.startswith("[")
                and kind in ("daily", "weekly", "rotation", "endgame") and isinstance(metric, str)
                and metric.isidentifier() and game != "colorsweeper"):
            # 명시적으로 설정된 사용자 추가 연동, 설정만으로 감지 항목을 창조하지는 못함.
            bindings.append(Binding(game, title, kind, metric))
    return tuple(dict.fromkeys(bindings))


def gauge_for(status: Status, metric: str) -> Gauge:
    if metric == "daily":
        return status.daily
    value = status.metrics.get(metric)
    return value if isinstance(value, Gauge) else Gauge(None, None)
