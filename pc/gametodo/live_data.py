"""화면 캡처 없이 계정 목표 달성 여부를 읽는 자료형.

사용자 규칙(v0.4.1): 일일 목표 점수가 최대치면 Todoist에서 완료로 취급한다.
이는 실제 게임 보상 수령과는 다른 기준이다. 실제 수령 플래그는 참고용으로
별도로 보존하되, 목표 점수 자체가 없는 데이터(None/0)는 완료하지 않는다.
"""
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Gauge:
    current: int | None
    maximum: int | None

    @property
    def filled(self) -> bool:
        return (type(self.current) is int and type(self.maximum) is int
                and self.maximum > 0 and self.current >= self.maximum)

    def text(self):
        return f"{self.current}/{self.maximum}" if self.current is not None and self.maximum is not None else "정보 없음"


@dataclass(frozen=True)
class Status:
    game: str
    source: str
    daily: Gauge = field(default_factory=lambda: Gauge(None, None))
    # 실제 수령 정보는 참고용. True=수령, False=미수령, None=정보 없음.
    # 목표 달성 여부와 뒤섞지 않는다(진단 화면에서도 구분).
    all_rewards_claimed: bool | None = None
    details: dict = field(default_factory=dict)
    note: str = ""
    # 일일 점수와 주간/엔드콘텐츠 점수를 섞지 않고 별도로 유지한다.
    metrics: dict = field(default_factory=dict)
    # 다음 주기 시작 시각(Unix seconds)이 확인된 콘텐츠만 rotation 판정 허용.
    metric_expiries: dict = field(default_factory=dict)
    # 실제 서버가 응답한 상태 수집 시각(Unix seconds); 없는 API는 None.
    observed_at: int | None = None

    def meets_completion(self, score_goal_counts_as_complete: bool = True) -> bool:
        """Todoist 완료 판정: 기본은 목표 점수 충족, 설정으로 엄격 판정 복구 가능.

        숫자 0/0, 현재값만 있고 최대치가 없는 응답, 잘못된 응답은 미완료.
        보상 실제 수령 여부와 관계없이 점수 충족이면 True(사용자 요청).
        """
        if not self.daily.filled:
            return False
        return score_goal_counts_as_complete or self.all_rewards_claimed is True

    @property
    def safe_to_close(self) -> bool:
        return self.meets_completion()

    def report(self, score_goal_counts_as_complete: bool = True):
        return {"game": self.game, "source": self.source,
                "daily_progress": self.daily.text(),
                "reward_claimed": self.all_rewards_claimed,  # 실제 보상 플래그(있을 때만)
                "completion_basis": ("goal_score" if score_goal_counts_as_complete else "reward_claim"),
                "auto_complete_allowed": self.meets_completion(score_goal_counts_as_complete),
                "details": self.details,
                "metrics": {key: g.text() for key, g in self.metrics.items()},
                "note": self.note}


def field_at(obj: Any, path: str, default=None):
    """dict/Pydantic/일반 객체에 같은 방법으로 접근, 실패시 None."""
    current = obj
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part, default)
        else:
            current = getattr(current, part, default)
        if current is default or current is None:
            return default
    return current


def number(obj, *paths) -> int | None:
    for path in paths:
        v = field_at(obj, path)
        if type(v) is int and v >= 0:
            return v
    return None


def gauge(obj, current_paths, max_paths) -> Gauge:
    return Gauge(number(obj, *current_paths), number(obj, *max_paths))


def all_claimed_from_reward_list(obj, path, total_path=None):
    """최종 보상마다 claimed=True인 경우만 안전하게 참으로 반환.

    스코어 또는 루틴 완료 여부만으로 추측하지 않음. 최소 1개의 보상 필요.
    """
    rows = field_at(obj, path)
    # 리스트가 '수령 완료한 보상만' 반환할 수 있어 전체 개수 검증이 필수.
    expected = field_at(obj, total_path) if total_path else None
    if not isinstance(rows, (tuple, list)) or not rows or type(expected) is not int or expected <= 0:
        return None
    if len(rows) != expected:
        return None
    vals = [field_at(r, 'claimed') for r in rows]
    if not all(type(v) is bool for v in vals):
        return None
    return all(vals)


def genshin_status(note):
    daily = gauge(note, ("daily_task.completed_tasks", "completed_commissions"),
                  ("daily_task.max_tasks", "max_commissions"))
    flag = field_at(note, "daily_task.claimed_commission_reward")
    if type(flag) is not bool:
        flag = field_at(note, "claimed_commission_reward")
    flag = flag if type(flag) is bool else None
    # 할인 사용 횟수(전투 승리 횟수와 구별). API 필드가 없으면 완료 여부는 미확인.
    remaining = number(note, "remain_resin_discount_num")
    limit = number(note, "resin_discount_num_limit")
    weekly = (Gauge(limit - remaining, limit) if limit is not None and limit >= 3
              and remaining is not None and 0 <= remaining <= limit else Gauge(None, None))
    return Status("genshin", "HoYoLAB", daily, flag,
                  note="일퀘 4/4이면 완료(추가 보상 수령 플래그는 참고 정보)",
                  metrics={"weekly": weekly})


def hsr_status(note):
    daily = gauge(note, ("current_train_score", "daily_training.current", "daily_training.current_score"),
                  ("max_train_score", "daily_training.max", "daily_training.max_score"))
    rogue = gauge(note, ("current_rogue_score",), ("max_rogue_score",))
    # 일일 훈련 점수가 현재/최대치에 도달하면 보상 수령 여부와 무관하게 완료.
    # 플래그가 있다면 실제 수령 여부 확인용으로만 남겨 둔다.
    claim = field_at(note, "daily_training.all_rewards_claimed")
    if type(claim) is not bool:
        claim = all_claimed_from_reward_list(note, "daily_training.rewards", "daily_training.total_rewards")
    # Android와 동일: 시뮬레이션 우주·화폐 전쟁 통합 포인트 AND 역전의 여운 주간 할인 3회.
    remain = number(note, "remaining_weekly_discounts", "weekly_cocoon_cnt")
    discount_limit = number(note, "max_weekly_discounts")
    if discount_limit is None:
        discount_limit = 3
    weekly = Gauge(None, None)
    if (rogue.current is not None and rogue.maximum is not None and rogue.maximum > 0
            and remain is not None and discount_limit == 3 and 0 <= remain <= 3):
        weekly = Gauge(int(rogue.filled) + int(remain == 0), 2)
    return Status("hsr", "HoYoLAB", daily, claim,
                  {"simulated_universe_points": rogue.text()},
                  "일일 훈련 점수가 최대치면 Todoist 완료",
                  metrics={"rogue_weekly": rogue, "weekly": weekly})


def zzz_status(note):
    daily = gauge(note, ("vitality.current", "engagement.current", "daily_engagement.current"),
                  ("vitality.max", "engagement.max", "daily_engagement.max"))
    weekly = gauge(note, ("weekly_task.current", "weekly_task.points"),
                   ("weekly_task.max", "weekly_task.max_points"))
    claim = field_at(note, "vitality.all_rewards_claimed")
    if type(claim) is not bool:
        claim = all_claimed_from_reward_list(note, "vitality.rewards", "vitality.total_rewards")
    # Todoist 주간퀘 부모 작업: Android와 동일하게 두 보상 조건을 모두 확인해야 한다.
    ridu = number(note, "weekly_task.cur_point", "weekly_task.current")
    bounty = number(note, "bounty_commission.total_score", "bounty_commission.current_score",
                    "bounty_commission.score", "bounty_commission.points", "hollow_zero.bounty_points")
    combined = (Gauge(int(ridu >= 800) + int(bounty >= 8000), 2)
                if ridu is not None and bounty is not None else Gauge(None, None))
    return Status("zzz", "HoYoLAB", daily, claim,
                  {"weekly_task_points": weekly.text()},
                  "일일 활약도가 최대치면 Todoist 완료",
                  metrics={"weekly_task": weekly, "weekly": combined})


def wuthering_status(payload, expected_server_id):
    data = field_at(payload, "data")
    if not isinstance(data, dict) or payload.get("code") != 200:
        raise ValueError("KuroBBS 상태 조회 실패/로그인 만료")
    actual = str(data.get("serverId") or "")
    role = str(data.get("roleId") or "")
    if not actual or actual != str(expected_server_id) or not role:
        raise ValueError("KuroBBS 게임 서버/계정 불일치. 다른 서버 데이터를 사용하지 않음")
    daily = gauge(data, ("livenessData.cur",), ("livenessData.total",))
    weekly = gauge(data, ("weeklyData.cur",), ("weeklyData.total",))
    # weeklyData는 일반 '주간 퀘스트'가 아니라 주간 콘텐츠(战歌重奏) 진행도다.
    # 기존 [명조] 주간퀘와 동일하다고 판단하면 잘못 체크할 수 있으므로 자동 매칭하지 않는다.
    weekly_rogue = gauge(data, ("weeklyRougeData.cur",), ("weeklyRougeData.total",))
    tower = gauge(data, ("towerData.cur",), ("towerData.total",))
    slash_tower = gauge(data, ("slashTowerData.cur",), ("slashTowerData.total",))
    tower_expiry = number(data, "towerData.refreshTimeStamp")
    slash_expiry = number(data, "slashTowerData.refreshTimeStamp")
    signed_in = data.get("hasSignIn")
    # KuroBBS 출석 완료(hasSignIn)는 게임 안의 일일 활약 보상 수령 증거가 아니다.
    return Status("wuthering", "KuroBBS", daily, None,
                  {"weekly": weekly.text(),
                   "community_checkin_claimed": signed_in if type(signed_in) is bool else None},
                  "일일 활약도가 최대치면 Todoist 완료(커뮤니티 출석은 무관)",
                  metrics={"weekly_boss": weekly, "weekly_rogue": weekly_rogue,
                           "tower": tower, "slash_tower": slash_tower},
                  metric_expiries={"tower": tower_expiry, "slash_tower": slash_expiry},
                  observed_at=number(data, "serverTime"))


def endfield_status(payload, role_id, server_id):
    data = field_at(payload, "data")
    if not isinstance(data, dict):
        raise ValueError("SKPORT API 응답 실패")
    detail = data.get("detail") or data
    if not isinstance(detail, dict):
        raise ValueError("SKPORT 캐릭터 데이터 없음")
    base = detail.get("base") or {}
    if str(base.get("roleId") or "") != str(role_id):
        raise ValueError("SKPORT 계정 불일치")
    # 서버 식별도 필수: 호출 시 서명된 serverId와 바인딩 정보를 비교.
    daily = gauge(detail, ("dailyMission.dailyActivation",),
                  ("dailyMission.maxDailyActivation",))
    # 일일 활약도 maxDailyActivation 달성을 Todoist 완료 조건으로 사용.
    # 실제 보상 수령을 수행하지는 않는다.
    return Status("endfield", "SKPORT", daily, None,
                  {"server_id": str(server_id)},
                  "일일 임무 활약도 최대치면 Todoist 완료")
