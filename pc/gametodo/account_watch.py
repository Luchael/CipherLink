"""게임 계정 데이터 → Todoist '오늘/과거의 해당 회차 작업' 자동 완료.

오작동 방지 규칙:
1) 매일 KST 서버 초기화 전에는 *어떤* 회차도 완료하지 않는다.
2) 초기화 직후 유예 시간에는 전날 API 캐시를 사용하지 않는다.
3) 일일/주간/순환 콘텐츠는 각기 다른 회차 ID를 쓴다.
4) 정확히 같은 제목·게임인 작업 한 개만, due 날짜가 오늘 이하일 때만 닫는다.
5) 점수가 불확실하거나 해당 콘텐츠의 API가 없으면 변경하지 않는다.
6) 서로 다른 PC/안드로이드도 동일 완료 명령 UUID를 사용한다.
"""
from datetime import datetime, timedelta
import logging
import time

from .account_sources import read_hoyolab, read_wuthering, read_endfield, read_arknights
from .cycles import KST, before_today_reset, current_period, due_is_eligible, due_date_kst, season_matches_task
from .games import task_game
from .task_rules import configured_bindings, gauge_for
from .lookup_policy import enabled as lookup_enabled

LOG = logging.getLogger(__name__)

# 하위 호환: 구 코드가 이 상수를 참조할 수 있다.
DAILY_TITLES = {"genshin": "[원신] 일퀘", "hsr": "[열차] 일퀘",
                "zzz": "[젠존제] 일퀘", "wuthering": "[명조] 일퀘",
                "endfield": "[엔필] 일퀘", "arknights": "[명방] 일퀘"}


def active_games(settings, allow_arknights=False):
    hoyo = settings.get("hoyolab") or {}
    if hoyo.get("enabled"):
        uid_map = hoyo.get("uids") or {}
        if lookup_enabled(settings, "genshin") and (hoyo.get("genshin_uid") or uid_map.get("genshin")):
            yield "genshin", lambda: read_hoyolab("genshin", settings)
        for key in ("hsr", "zzz"):
            if lookup_enabled(settings,key) and uid_map.get(key):
                yield key, lambda k=key: read_hoyolab(k, settings)
    cfg = settings.get("account_data") or {}
    if cfg.get("enabled"):
        if lookup_enabled(settings,"wuthering") and (cfg.get("wuthering") or {}).get("enabled"):
            yield "wuthering", lambda: read_wuthering(settings)
        if lookup_enabled(settings,"endfield") and (cfg.get("endfield") or {}).get("enabled"):
            yield "endfield", lambda: read_endfield(settings)
        # 명일방주는 사용자가 로그인 충돌을 수용하고 매일 23:59 조회에
        # 명시적으로 동의한 경우에만, 별도 1회 호출 경로로 실행한다.
        ark = cfg.get("arknights") or {}
        if allow_arknights and lookup_enabled(settings,"arknights") and ark.get("enabled"):
            yield "arknights", lambda: read_arknights(settings)


def _done_before(store, key: str) -> bool:
    # 구 테스트용 메모리 Store에도 맞춰 동작하도록 duck typing 사용.
    fn = getattr(store, "has_completed", None)
    return bool(fn(key)) if callable(fn) else False


def _record_done(store, key: str, task_id: str) -> None:
    fn = getattr(store, "record_completion", None)
    if callable(fn):
        fn(key, str(task_id))


def run_account_check(settings, todoist=None, store=None, read_only=False, now=None, only_game=None, allow_arknights=False):
    """게임별 상태를 한 번만 조회하고, 가능한 일퀘·주간·순환 작업을 판정한다.

    read_only=True: 계정 상태 진단. Todoist 로그인·완료 명령은 실행하지 않는다.
    반환값의 action은 기존 CLI와 호환되는 일퀘 결과이고, other_tasks는 추가 결과.
    """
    now = now or datetime.now(KST)
    local = now.astimezone(KST)
    responses = []
    account = settings.get("account_data") or {}
    hours = account.get("reset_hours_kst") or {}
    times = account.get("reset_times_kst") or {}
    weekdays = account.get("weekly_reset_weekdays") or {}
    strict = not account.get("score_goal_counts_as_complete", True)
    grace = max(0, min(120, int(account.get("reset_grace_minutes", 20))))
    bindings = configured_bindings(settings)
    tasks = None

    for game, reader in active_games(settings, allow_arknights=allow_arknights):
        if only_game is not None and game != only_game: continue
        # 비용 절약: 초기화 전에는 계정 API도 조회하지 않는다(읽기 전용 제외).
        if not read_only and before_today_reset(game, local, hours, times):
            responses.append({"game": game, "source": "게임 초기화 시각",
                              "action": "오늘 게임 초기화 전 또는 시각 미확인: 체크 금지"})
            continue
        if not read_only:
            # 설정에 분(HH:MM)이 있어도 일관된 초기화 후 유예 시간 계산.
            boundary = current_period(game, "daily", local, hours, times)
            if boundary and local < boundary.starts_at + timedelta(minutes=grace):
                responses.append({"game": game, "source": "게임 초기화 시각",
                                  "action": "서버 초기화 직후: 감지 보류"})
                continue
        try:
            uid, status = reader()
            info = status.report(not strict)
            info["uid_last4"] = uid[-4:] if uid else ""
            info["other_tasks"] = []
            game_bindings = [b for b in bindings if b.game == game]
            for binding in game_bindings:
                progress = gauge_for(status, binding.metric)
                # 기존 엄격 모드는 일일 작업에서 실수령 플래그도 요구한다.
                meets = (status.meets_completion(False) if strict and binding.metric == "daily"
                         else progress.filled and not strict)
                is_daily = binding.kind == "daily"
                desc = {"title": binding.title, "kind": binding.kind,
                        "metric": binding.metric, "progress": progress.text()}
                if not meets:
                    desc["action"] = "목표 점수 미달 또는 증거 불충분: 변경 안 함"
                elif (type(status.observed_at) is int
                      and ((current_period(game, "daily", local, hours, times) is not None
                            and status.observed_at < current_period(game, "daily", local, hours, times).starts_at.timestamp())
                           or status.observed_at > local.timestamp() + 300)):
                    # API 서버 응답 자체가 오늘 회차 이전 데이터면 2회 관측해도 무효.
                    desc["action"] = "전날 서버 캐시 또는 기기 시간 불일치: 보류"
                elif read_only:
                    desc["action"] = "목표 점수 달성: 읽기 전용, Todoist 변경 없음"
                elif todoist is None or store is None:
                    desc["action"] = "Todoist/기록 저장소 미연결"
                else:
                    until = status.metric_expiries.get(binding.metric) if binding.kind in ("rotation", "endgame") else None
                    fixed=None
                    if binding.kind=="interval":
                        # The exact task date is required below; never fabricate a server period.
                        period=True if status.metric_windows.get(binding.metric) else None
                    else:
                        period = current_period(game, "rotation" if binding.kind == "endgame" else binding.kind,
                                            local, hours, times, until, weekdays)
                    # Unknown season / score-only / old season MUST NOT cause automatic check.
                    if binding.kind == "endgame" and not (type(until) is int and until > local.timestamp()):
                        period = None
                    if period is None:
                        desc["action"] = "회차 또는 서버 종료 시간 확인 불가: 보류"
                    else:
                        # 게임, 계정, 콘텐츠, 기간을 포함해 회차 간 교차완료를 방지.
                        period_key=("api:"+":".join(str(n) for n in status.metric_windows[binding.metric])) if binding.kind=="interval" else period.key
                        key = f"account:{game}:{uid}:{binding.kind}:{binding.metric}:{period_key}"
                        if _done_before(store, key):
                            desc["action"] = "이 회차는 이미 완료 처리함"
                        else:
                            if tasks is None:
                                tasks = todoist.all_tasks()
                            matching = [t for t in tasks if t.get("content") == binding.title
                                        and task_game(t) == game
                                        and not t.get("checked") and not t.get("is_completed")]
                            if binding.project_name and binding.section_name:
                                location=todoist.named_location(binding.project_name,binding.section_name)
                                matching=[t for t in matching if location and str(t.get('project_id'))==location[0] and str(t.get('section_id'))==location[1]]
                            if binding.kind=="interval" and len(matching)==1:
                                from .fixed_cycles import fixed_occurrence
                                fixed=fixed_occurrence(matching[0],binding.interval_days,status.metric_windows.get(binding.metric),local,binding.completion)
                            if len(matching) != 1:
                                desc["action"] = "정확히 일치하는 활성 작업이 하나가 아님: 보류"
                            elif not due_is_eligible(matching[0], local):
                                desc["action"] = "Todoist 다음 회차 또는 날짜 미설정: 보류"
                            elif binding.kind=="interval" and (fixed is None or _done_before(store,key)):
                                desc["action"]="현재 고정 주기·API 회차 확인 불가 또는 이미 완료: 보류"
                            elif binding.kind == "endgame" and not season_matches_task(
                                    game, matching[0], status.metric_windows.get(binding.metric), local, hours, times):
                                desc["action"] = "API 기록과 Todoist 현재 회차 불일치: 보류"
                            elif binding.kind == "weekly" and due_date_kst(matching[0]) < period.starts_at.date():
                                desc["action"] = "이전 주간 회차 예정일: 보류"
                            else:
                                # 모든 기기에서 동일 회차에 동일한 UUID가 생성되도록 고정한다.
                                occurrence = (fixed if binding.kind=="interval" else period.starts_at.date().isoformat() if is_daily
                                              else period.key)
                                if todoist.complete_task(matching[0], occurrence):
                                    _record_done(store, key, str(matching[0]["id"]))
                                    desc["action"] = "Todoist 완료 적용"
                                    # Todoist가 완료 후 due를 다음 회차로 옮기므로 재조회 필요.
                                    tasks = None
                                else:
                                    desc["action"] = "Todoist 이전에 완료됨"
                if is_daily:
                    # 기존 계정 상태 CLI와 테스트가 사용하던 결과 필드 유지.
                    info["action"] = desc["action"]
                else:
                    info["other_tasks"].append(desc)
            info.setdefault("action", "자동 연결된 일퀘 없음")
            responses.append(info)
        except Exception as exc:
            # 토큰·API 원문은 출력하지 않고 오류 클래스만 남긴다.
            LOG.warning("%s: 상태 조회 실패: %s", game, type(exc).__name__)
            responses.append({"game": game, "source": "계정 API", "action": "조회 실패: 완료 안 함",
                              "reason": type(exc).__name__ + " (설정/로그인/응답 점검 필요)"})
    return responses
