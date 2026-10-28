"""휴대폰 자체(Termux ↔ Android 앱)의 127.0.0.1 API.

/tasks: 해당 게임의 현재 할 일, 사용자가 펼쳤을 때만 조회.
/complete: 플로팅 완료 버튼 수동 누름에만 호출; 서버에서 ID/게임 검증.
/observation: OCR을 별도 활성화한 경우에만 처리.
"""
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import logging
from urllib.parse import parse_qs, urlsplit

from .games import GAMES, task_game

LOG = logging.getLogger(__name__)
KST = timezone(timedelta(hours=9))


def tasks_for_game(tasks, game):
    if game not in GAMES:
        raise ValueError("지원하지 않는 게임")
    active = [t for t in tasks if task_game(t) == game
              and not t.get("checked") and not t.get("is_completed")]
    active.sort(key=lambda t: (
        ((t.get("due") or {}).get("date") or "9999-12-31"),
        (t.get("content") or "")))
    return [{"id": str(t["id"]), "content": t.get("content", ""),
             "due": (t.get("due") or {}).get("date", "")} for t in active[:100]]


def run_bridge(observer, secret: str, port=8765):
    if len(secret) < 20:
        raise ValueError("LOCAL_BRIDGE_SECRET은 최소 20자 이상으로 설정하세요")

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # 유저의 게임 작업명, OCR 값 등 기록하지 않음

        def _authorized(self):
            if not hmac.compare_digest(self.headers.get("X-Local-Secret", ""), secret):
                self.send_error(403)
                return False
            return True

        def _json(self, value):
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self._authorized():
                return
            route = urlsplit(self.path)
            if route.path != "/tasks":
                self.send_error(404); return
            key = parse_qs(route.query).get("game", [""])[0]
            try:
                tasks = tasks_for_game(observer.todoist.all_tasks(), key)
                self._json({"game": key, "tasks": tasks})
            except Exception as exc:
                LOG.warning("게임 작업 조회 실패: %s", type(exc).__name__)
                self.send_error(400)

        def do_POST(self):
            if not self._authorized():
                return
            if self.path not in ("/observation", "/complete"):
                self.send_error(404); return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size <= 0 or size > 48000:
                    self.send_error(413); return
                obj = json.loads(self.rfile.read(size))
                if self.path == "/observation":
                    game, text = obj["game"], obj["text"]
                    if not isinstance(text, str) or not isinstance(game, str):
                        raise ValueError("타입 오류")
                    changed = observer.evaluate(game, text)
                    self._json({"completed": changed})
                else:
                    game, tid = obj["game"], str(obj["id"])
                    # 모바일 앱 요청만 믿지 않고 Todoist에서 다시 실제 게임 소속 확인
                    if game not in GAMES or not tid or len(tid) > 64:
                        raise ValueError("잘못된 작업")
                    items = observer.todoist.all_tasks()
                    matches = [t for t in items if str(t["id"]) == tid and task_game(t) == game]
                    if len(matches) != 1:
                        raise ValueError("해당 게임의 작업을 찾지 못함")
                    due = ((matches[0].get("due") or {}).get("date") or "")[:10]
                    occurrence = due or datetime.now(KST).date().isoformat()
                    changed = observer.todoist.complete_task(matches[0], occurrence)
                    observer._cached_tasks = None
                    self._json({"completed": bool(changed)})
            except Exception as exc:
                LOG.warning("Android 요청 실패: %s", type(exc).__name__)
                self.send_error(400)

    server = ThreadingHTTPServer(("127.0.0.1", int(port)), Handler)
    LOG.info("Android 로컬 브리지: 127.0.0.1:%s", port)
    server.serve_forever()
