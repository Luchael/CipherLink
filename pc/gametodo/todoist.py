"""Todoist Sync API: 중복 차단·라벨·기존 이벤트 v0.1 업그레이드."""
import json
from urllib.parse import urlencode

from .games import GAMES, task_game, title_for
from .models import canonical, command_uuid

BASE = "https://api.todoist.com/api/v1"
MARKER = "GameTodo-ID: "


class Todoist:
    def __init__(self, http, section_name: str, project_id: str = "", section_id: str = ""):
        self.http = http
        self.section_name = section_name
        self.project_id = project_id
        self.section_id = section_id

    def locate(self):
        if self.section_id:
            info = self.http.request(f"{BASE}/sections/{self.section_id}")
            if canonical(info["name"]) != canonical(self.section_name):
                raise ValueError("지정된 섹션 ID의 이름이 설정과 다릅니다")
            self.project_id = str(info["project_id"])
            return
        sections = [s for s in self.http.paginated(f"{BASE}/sections")
                    if canonical(s.get("name", "")) == canonical(self.section_name)
                    and (not self.project_id or str(s.get("project_id")) == self.project_id)]
        if len(sections) != 1:
            raise ValueError(f"'{self.section_name}' 섹션 {len(sections)}개 발견. section_id를 명시해 주세요.")
        self.section_id = str(sections[0]["id"])
        self.project_id = str(sections[0]["project_id"])

    def all_tasks(self):
        return list(self.http.paginated(f"{BASE}/tasks"))

    def command(self, operation: str, args: dict, unique_key: str, temp_id=None):
        uid = command_uuid(operation, unique_key)
        one = {"type": operation, "uuid": uid, "args": args}
        if temp_id:
            one["temp_id"] = temp_id
        encoded = urlencode({"commands": json.dumps([one], ensure_ascii=False)}).encode("utf-8")
        result = self.http.request(f"{BASE}/sync", "POST", encoded,
                                   headers={"Content-Type": "application/x-www-form-urlencoded"})
        status = result.get("sync_status", {}).get(uid)
        if status != "ok":
            raise RuntimeError(f"Todoist sync {operation} 오류: {status!r}")
        return result.get("temp_id_mapping", {}).get(temp_id) if temp_id else None

    @staticmethod
    def indexed(tasks):
        """같은 제목인 다른 게임은 충돌시키지 않음. 기존 이름만 있는 수동 일정은 보수적으로 보존."""
        names = set()  # (game, normalized_name), (None, normalized_name)
        markers = {}
        for task in tasks:
            if task.get("checked") or task.get("is_completed"):
                continue
            name = canonical(task.get("content", ""))
            game = task_game(task)
            if name:
                names.add((game, name))
            for line in (task.get("description") or "").splitlines():
                if line.startswith(MARKER):
                    markers[line[len(MARKER):].strip()] = task
        return names, markers

    def import_event(self, event, existing_names: set, markers: dict, store, dry_run=False):
        """기존 v0.1 자동등록도 제목/라벨 보정. 사용자 수동 작업은 절대 변경하지 않음."""
        profile = GAMES[event.game]
        title = title_for(event.game, event.name)
        labels = [profile.label]
        prior = markers.get(event.key)
        cached = store.event_task(event.key)
        if prior:
            new_labels = sorted(set(prior.get("labels") or []) | {profile.label})
            delta = {}
            if prior.get("content") != title:
                delta["content"] = title
            if new_labels != sorted(set(prior.get("labels") or [])):
                delta["labels"] = new_labels
            if ((prior.get("due") or {}).get("date") or "")[:10] != event.due_date:
                delta["due"] = {"date": event.due_date}
            if not delta:
                store.record_event(event.key, prior["id"], event.due_date)
                return None
            if dry_run:
                return f"[기존 작업 수정 예정] {title} {delta}"
            delta["id"] = str(prior["id"])
            # 다른 날짜/라벨로 업데이트되어도 다시 적용 가능하도록 상태를 UUID에 반영
            state_key = json.dumps(delta, ensure_ascii=False, sort_keys=True)
            self.command("item_update", delta, f"{event.key}:{state_key}")
            store.record_event(event.key, prior["id"], event.due_date)
            prior.update({"content": title, "labels": new_labels, "due": {"date": event.due_date}})
            existing_names.add((event.game, canonical(title)))
            return f"[기존 작업 보정] {title}"
        # 수동 추가한 해당 게임의 제목도 보호. 접두사 없는 이름 수동 작업도 보호.
        norm = canonical(event.name)
        if (event.game, norm) in existing_names or (None, norm) in existing_names:
            return None
        if cached:
            # 검색 반영 지연/다른 기기의 직전 생성 중 중복 명령 차단
            return None
        if dry_run:
            return f"[추가 예정] {title} ({event.due_date}) 라벨={profile.label}"
        desc = (f"{MARKER}{event.key}\n"
                f"게임: {event.game} / 서버: {event.server}\n"
                f"시작(KST): {event.starts_at:%Y-%m-%d %H:%M}\n"
                f"종료(KST): {event.ends_at:%Y-%m-%d %H:%M}\n"
                f"출처: {event.url}\n"
                "완료 조건: 게임 내 해당 이벤트의 모든 획득 가능 보상 수령 확인")
        temp = command_uuid("temp", f"{self.project_id}:{event.key}")
        args = {"content": title, "labels": labels, "description": desc,
                "project_id": self.project_id, "section_id": self.section_id,
                "due": {"date": event.due_date}}
        task_id = self.command("item_add", args, f"{self.project_id}:{event.key}", temp_id=temp)
        if task_id:
            store.record_event(event.key, task_id, event.due_date)
            markers[event.key] = {"id": task_id, "content": title, "labels": labels,
                                  "description": desc, "due": {"date": event.due_date}}
        existing_names.add((event.game, norm))
        return f"[등록] {title} ({event.due_date})"

    def complete_task(self, task: dict, occurrence: str, dry_run=False):
        if task.get("checked") or task.get("is_completed"):
            return False
        if dry_run:
            return True
        # 'item_close' : Todoist가 반복 작업인 경우 다음 회차로 전환함.
        self.command("item_close", {"id": str(task["id"])}, f"{task['id']}:{occurrence}")
        return True
