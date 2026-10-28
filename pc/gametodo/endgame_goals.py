"""엔드콘텐츠 완료 조건. Android의 EndgameGoals.kt와 동일하게 관리합니다.

경고: 이 상수는 '완료 조건'일 뿐입니다. 실제 게임에서 데이터를 수집했다고
가정할 수 없으며, 같은 시즌의 별/스텔라 수를 얻기 전에는 Todoist를 닫지 않습니다.
"""
from __future__ import annotations

import json
from pathlib import Path

GOALS = json.loads((Path(__file__).parent.parent / 'endgame_goals.json').read_text(encoding='utf-8'))


def target(mode: str) -> int | None:
    """점수 기반 콘텐츠의 최대 보상 목표; 지맥제압전은 난이도로 따로 판단한다."""
    goal = GOALS.get(mode, {}).get('target')
    return goal if type(goal) is int and goal > 0 else None


def achieved(mode: str, value: int | None) -> bool:
    """같은 단위(별 또는 스텔라)의 수치임을 파서가 입증한 경우에만 호출한다."""
    required = target(mode)
    return required is not None and type(value) is int and value >= required
