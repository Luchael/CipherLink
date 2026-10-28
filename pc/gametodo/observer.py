"""OCR 증거 기반 완료 판정.

부분 진행/보상 수령 버튼 존재만으로 완료하지 않음.
게임별 명시적 '모든 보상 수령 완료' 문구를 2번 연속 관측해야 한다.
"""
import re
import time
from datetime import datetime, timedelta

from .cycles import KST, before_today_reset, current_period, due_is_eligible
from .task_rules import configured_bindings
from .models import canonical


def safe_regex(pattern: str, text: str):
    if len(pattern) > 200 or len(text) > 10000:
        return False
    return re.search(pattern, text, flags=re.I | re.M) is not None


class Observer:
    def __init__(self, config, todoist, store):
        self.rules = config.get("screen_rules", [])
        self.todoist = todoist
        self.store = store
        self.config = config
        self._cached_tasks = None
        self._cached_at = 0.0

    def active_tasks(self):
        # 충분히 명확한 완료 신호가 잡힌 때에만 인터넷을 사용한다.
        if self._cached_tasks is None or time.monotonic() - self._cached_at > 600:
            self._cached_tasks = self.todoist.all_tasks()
            self._cached_at = time.monotonic()
        return self._cached_tasks

    def evaluate(self, game: str, text: str, dry_run=False):
        """입력: OCR 화면 텍스트. 출력: 확실한 완료로 처리된 작업 제목 목록."""
        if len(text) > 10000:
            return []
        output = []
        active_tasks = None
        for rule in self.rules:
            if not rule.get("enabled", False) or rule.get("game") != game:
                continue
            positives = rule.get("all_claimed_patterns") or []
            # 포괄적인 "수령" 한 단어만 들어가면 절대 완료 처리하지 않는다.
            if not positives or not any(safe_regex(p, text) for p in positives):
                continue
            if any(safe_regex(p, text) for p in rule.get("pending_patterns", [])):
                continue
            if rule.get("kind") == "event":
                if active_tasks is None:
                    active_tasks = self.active_tasks()
                # 이벤트 이름과 '모든 보상 수령' 확증이 동일 화면에 함께 있어야 함.
                for task in active_tasks:
                    desc = task.get("description", "")
                    if "GameTodo-ID: " not in desc or f"게임: {game} " not in desc:
                        continue
                    title = canonical(task["content"])
                    # 단문을 다른 UI 일부 텍스트로 오인하지 않음.
                    if len(title) < 5 or title not in canonical(text):
                        continue
                    due = (task.get("due") or {}).get("date", "")[:10]
                    evidence_key = f"event:{task['id']}:{due}"
                    if self.store.evidence_seen(evidence_key, time.time()):
                        if self.todoist.complete_task(task, due, dry_run):
                            output.append(task["content"])
                            self._cached_tasks = None
            else:
                # 반복 작업의 OCR 경로에도 계정 API와 동일한 날짜 안전장치를 적용.
                # 감지할 '주간/일간' 유형이 확인되지 않으면 임의로 완료하지 않는다.
                now = datetime.now(KST)
                account = self.config.get("account_data") or {}
                hours = account.get("reset_hours_kst") or {}
                times = account.get("reset_times_kst") or {}
                if before_today_reset(game, now, hours, times):
                    continue
                daily = current_period(game, "daily", now, hours, times)
                grace = max(0, min(120, int(account.get("reset_grace_minutes", 20))))
                if daily is None or now < daily.starts_at + timedelta(minutes=grace):
                    continue
                want = rule.get("task_name", "")
                binding = next((b for b in configured_bindings(self.config)
                                if b.game == game and b.title == want), None)
                kind = rule.get("period") or (binding.kind if binding else "")
                # 화면 인식에는 갱신 시각을 확인할 근거가 없어 rotation은 자동 제외.
                if kind not in ("daily", "weekly"):
                    continue
                period = current_period(game, kind, now, hours, times,
                                        weekdays=account.get("weekly_reset_weekdays"))
                if period is None:
                    continue
                if not rule.get("context_patterns") or not all(
                        safe_regex(p, text) for p in rule["context_patterns"]):
                    continue
                if active_tasks is None:
                    active_tasks = self.active_tasks()
                for task in active_tasks:
                    if task.get("content") != want or task.get("checked") or task.get("is_completed"):
                        continue
                    if not due_is_eligible(task, now):
                        continue
                    evidence_key = f"ocr:task:{task['id']}:{game}:{period.key}"
                    if not self.store.evidence_seen(evidence_key, time.time()):
                        continue
                    occurrence = period.starts_at.date().isoformat() if kind == "daily" else period.key
                    if self.todoist.complete_task(task, occurrence, dry_run):
                        output.append(task["content"])
                        self._cached_tasks = None
        return output
