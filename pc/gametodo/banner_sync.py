"""가챠 자동 등록 및 종료 시 자동 완료.

- 일반 이벤트 등록 기능은 호출하지 않습니다.
- Todoist 일반 날짜(due)는 가챠 시작일, 유료 기한(deadline)은 사용하지 않습니다.
- 종료 시각과 자동생성 여부는 로컬 SQLite 원장으로 관리합니다.
- PC/Android가 함께 동기화할 수 있으므로 명령 UUID는 결정적으로 생성합니다.
"""
from datetime import datetime, timezone, timedelta
import logging
import re

from .banners import KST, fetch_banners
from .games import GAMES
from .http_client import HttpClient
from .models import canonical
from .todoist import Todoist

LOG = logging.getLogger(__name__)
BANNER_MARKER = "GameTodo-Banner-ID: "
END_MARKER = "가챠 종료(KST): "


def parse_expiry(description: str):
    """반드시 우리 자동 작업에 포함된 식별자와 종료일에서만 만료 판정."""
    if BANNER_MARKER not in description:
        return None
    match = re.search(r"(?m)^가챠 종료\(KST\):\s*(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s*$", description)
    return datetime.strptime(match.group(1), "%Y-%m-%d %H:%M").replace(tzinfo=KST) if match else None


def marker_key(task):
    m = re.search(r"(?m)^GameTodo-Banner-ID: ([a-f\d]{32})\s*$", task.get("description") or "")
    return m.group(1) if m else None


def description_for(b):
    """사용자 요청: 설명에는 오직 출처 링크만. 종료시간은 SQLite에만 저장."""
    return f"출처: {b.source_url}"


def due_date_for(b):
    """픽업 시작의 KST 날짜 (Todoist 무료 플랜의 일반 일정)."""
    return b.start.date().isoformat()


def remote_signature(task):
    return (str(task.get("content", "")).strip().casefold(),
            ((task.get("due") or {}).get("date") or "")[:10],
            (task.get("description") or "").strip())


def sync_banners(settings, store, *, dry_run=False, now=None, api=None):
    """1회 동기화. 네트워크 장애 시 기존 작업은 임의로 삭제하지 않는다.

    dry_run=True: 읽기만 하며 Todoist 인증 없어도 수집 목록을 보여준다.
    """
    now = now or datetime.now(KST)
    http = HttpClient(store)
    collected = {}
    failures = {}
    unsupported = {}
    for game, cfg in settings["game_settings"].items():
        if game not in ("genshin", "hsr", "zzz", "wuthering", "limbus", "endfield", "stella"):
            continue
        if not cfg.get("enabled", False):
            continue
        try:
            for b in fetch_banners(http, game, cfg, now=now):
                collected[b.key] = b
        except Exception as exc:
            from .diagnostics import user_error
            from .banners import UnsupportedBannerSource
            if isinstance(exc, UnsupportedBannerSource):
                unsupported[game] = str(exc)
                continue
            failures[game] = user_error(exc)
            LOG.warning("%s 픽업 조회 실패: %s", game, failures[game])
    report = {"active": [b.title for b in collected.values()], "created": [],
              "updated": [], "closed": [], "skipped": [], "errors": failures}
    report["unsupported"] = unsupported
    if dry_run:
        return report
    if api is None:
        from .settings import get_token
        http.token = get_token()
        api = Todoist(http, settings["section_name"],
                      settings.get("project_id", ""), settings.get("section_id", ""))
    api.locate()
    tasks = api.all_tasks()
    # 대상 섹션에 속한 *자동 생성* 가챠 작업만 수정/완료한다.
    target = [t for t in tasks if str(t.get("section_id")) == str(api.section_id)
              and not t.get("is_completed") and not t.get("checked")]
    by_marker = {marker_key(t): t for t in target if marker_key(t)}
    # PC/Android가 같은 계정을 쓸 때 설명에 내부 ID가 없어도 제목+시작일+출처로 식별.
    by_signature = {remote_signature(t): t for t in target}
    # 수동 작업이 라벨 없이 존재해도 동일 제목으로 중복 등록하지 않는다.
    # 접두사가 다른 게임은 서로 다른 작업이므로 접두사도 비교한다.
    by_title = {str(t.get("content", "")).strip().casefold()
                for t in target if not marker_key(t)}

    for b in collected.values():
        prior = by_marker.get(b.key) or by_signature.get((
            b.title.strip().casefold(), due_date_for(b), description_for(b)))
        profile = GAMES[b.game]
        if prior is None:
            # 사용자 수동 작업은 건드리지 않음. 제목+라벨이 같으면 중복 생성 보류.
            if b.title.strip().casefold() in by_title:
                report["skipped"].append(b.title + " (기존 수동 작업)")
                continue
            desc = description_for(b)
            temp_key = f"banner:{api.project_id}:{api.section_id}:{b.key}"
            from .models import command_uuid
            temp_id = command_uuid("banner-temp", temp_key)
            args = {"content": b.title, "description": desc,
                    "labels": sorted({profile.label, "가챠"}), "project_id": api.project_id,
                    "section_id": api.section_id,
                    "due": {"date": due_date_for(b)}}  # deadline_date는 사용하지 않음.
            new_id = api.command("item_add", args, temp_key, temp_id=temp_id)
            # 안정적인 Sync UUID로 PC+Android 동시 생성에도 중복 명령 방지.
            store.record_banner(b.key, new_id or "", b.end.isoformat(), b.title,
                                due_date_for(b), b.source_url)
            report["created"].append(b.title)
            continue
        change = {}
        if prior.get("content") != b.title:
            change["content"] = b.title
        labels = sorted(set(prior.get("labels") or []) | {profile.label, "가챠"})
        if labels != sorted(set(prior.get("labels") or [])):
            change["labels"] = labels
        desc = description_for(b)
        if prior.get("description") != desc:
            change["description"] = desc
        if ((prior.get("due") or {}).get("date") or "")[:10] != due_date_for(b):
            change["due"] = {"date": due_date_for(b)}
        if change:
            import json
            change["id"] = str(prior["id"])
            api.command("item_update", change, b.key + ":" + json.dumps(change, ensure_ascii=False, sort_keys=True))
            report["updated"].append(b.title)
        store.record_banner(b.key, prior["id"], b.end.isoformat(), b.title,
                            due_date_for(b), b.source_url)

    # 가챠 종료시간은 작업 설명에 기록하지 않고 PC 로컬 DB에 보존한다.
    # 출처 서버가 응답하지 않아도 마지막으로 검증한 종료시간으로 처리할 수 있다.
    by_id = {str(t["id"]): t for t in target}
    for key, task_id, end_at, saved_title, saved_start, saved_source in store.open_banners():
        task = by_id.get(str(task_id))
        if task is None:
            continue
        try:
            expiry = datetime.fromisoformat(end_at)
            if expiry.tzinfo is None:
                continue
        except (TypeError, ValueError):
            continue
        if now < expiry + timedelta(minutes=1):
            continue
        current = collected.get(key)
        if current and now < current.end + timedelta(minutes=1):
            continue  # 종료 시간 변경이 발견되었다면 최신 데이터를 우선함
        # 현재 설명이 출처만 포함된지, 구버전에서 GameTodo가 생성한 작업인지 검증.
        from_source = any(description_for(b) == (task.get("description") or "").strip()
                          and b.title == task.get("content")
                          and due_date_for(b) == ((task.get("due") or {}).get("date") or "")[:10]
                          for b in collected.values() if b.key == key)
        old_generated = marker_key(task) == key
        # 출처/제목/시작일을 DB 기록과 비교해 수동 수정 작업의 자동 완료를 차단한다.
        new_generated = bool(saved_title and saved_start and saved_source
            and str(task.get("content")) == saved_title
            and ((task.get("due") or {}).get("date") or "")[:10] == saved_start
            and (task.get("description") or "").strip() == f"출처: {saved_source}")
        if not (from_source or old_generated or new_generated):
            continue
        end_utc = expiry.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        api.complete_task(task, occurrence=f"banner:{key}:{end_utc}")
        store.record_closed_banner(key, str(task["id"]))
        report["closed"].append(task.get("content", ""))
    return report
