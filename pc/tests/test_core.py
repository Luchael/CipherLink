import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from gametodo.models import Event, canonical, command_uuid, should_import, extract_short_name
from gametodo.pickupcal import KST, parse_datetime, parse_pickupcal
from gametodo.todoist import Todoist
from gametodo.observer import Observer


class DummyStore:
    def __init__(self):
        self.events = {}
        self.evidence = {}
    def event_task(self, key):
        return self.events.get(key)
    def record_event(self, key, taskid, due):
        self.events[key] = (taskid, due)
    def evidence_seen(self, key, now, min_interval=8):
        if key not in self.evidence:
            self.evidence[key] = now
            return False
        return now - self.evidence[key] >= min_interval


class DummyHTTP:
    def __init__(self): self.sent = []
    def request(self, url, method="GET", payload=None, **kw):
        self.sent.append((url, method, payload))
        if method == "POST" and url.endswith("/sync"):
            import json
            from urllib.parse import parse_qs
            cmd = json.loads(parse_qs(payload.decode())["commands"][0])[0]
            return {"sync_status": {cmd["uuid"]: "ok"}, "temp_id_mapping": {cmd.get("temp_id", ""): "task-987"}}
        return {}


class CoreTests(unittest.TestCase):
    def test_kst_day(self):
        self.assertEqual(parse_datetime("2026-11-03 04:59", end=True).date().isoformat(), "2026-11-03")
        self.assertEqual(parse_datetime("2026-11-03", end=True).strftime("%H:%M:%S"), "23:59:59")
        self.assertEqual(parse_datetime("2026-11-03").utcoffset(), timedelta(hours=9))

    def test_exclusion(self):
        for word in ["현실 속 환상극", "나선 비경", "연합 토벌", "갈기의 게시판", "종언의 노래"]:
            self.assertFalse(should_import(word), word)
        self.assertFalse(should_import("커뮤니티 댓글 이벤트", "게임 외 SNS"))
        self.assertTrue(should_import("근심 없는 눈싸움"))

    def test_short_names(self):
        self.assertEqual(extract_short_name("「근심 없는 눈싸움」"), "근심 없는 눈싸움")
        self.assertEqual(extract_short_name("원신 - 「근심 없는 눈싸움」 이벤트"), "근심 없는 눈싸움")
        self.assertEqual(canonical("[원신] 일퀘"), "일퀘")

    def test_pickupcal_kr_html(self):
        html = '''<html><p>한국 서버 이벤트 일정 KST</p><ul>
        <li>[원신] <a href="/e/1">[이벤트] 원신 - 「근심 없는 눈싸움」</a>
        (7.1 버전 기간 한정 이벤트) (기간 · 한국 시간: 2026-10-21 11:00 ~ 2026-11-02 04:59)
        <a href="https://hoyolab.com/notice">공식 출처</a></li>
        <li>[원신] <a>[이벤트] 원신 - 「지맥 제압전」</a>
        (기간 · 한국 시간: 2026-09-30 ~ 2026-11-02)</li>
        <li>[원신] <a>[픽업] 원신 - 신규 캐릭터</a>
        (기간 · 한국 시간: 2026-10-13 ~ 2026-11-03)</li>
        </ul></html>'''
        events = parse_pickupcal(html, "genshin", "원신", "https://www.pickupcal.com/games/genshin/")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].name, "근심 없는 눈싸움")
        self.assertEqual(events[0].due_date, "2026-11-02")
        self.assertEqual(events[0].url, "https://hoyolab.com/notice")

    def test_china_not_accepted(self):
        with self.assertRaises(ValueError):
            parse_pickupcal("<li>중국 서버 이벤트</li>", "arknights", "명일방주", "https://other/")

    def test_id_is_stable_when_event_extended(self):
        a = Event("genshin", "축제", datetime(2026, 10, 12, tzinfo=KST), datetime(2026, 10, 27,tzinfo=KST), "")
        b = Event("genshin", "축제", a.starts_at, datetime(2026, 11, 2,tzinfo=KST), "")
        self.assertEqual(a.key, b.key)
        self.assertEqual(command_uuid("item_add", a.key), command_uuid("item_add", b.key))

    def test_do_not_duplicate_manual_todo(self):
        e = Event("genshin", "눈싸움", datetime(2026,10,1,tzinfo=KST), datetime(2026,11,2,tzinfo=KST), "https://example.com/")
        http = DummyHTTP()
        todo = Todoist(http, "이벤트 / 기간 한정", project_id="p1", section_id="s1")
        self.assertIsNone(todo.import_event(e, {("genshin", canonical("[원신] 눈싸움"))}, {}, DummyStore()))
        self.assertFalse(http.sent)

    def test_create_once_and_sync_idempotency(self):
        e = Event("genshin", "눈싸움", datetime(2026,10,1,tzinfo=KST), datetime(2026,11,2,tzinfo=KST), "https://example.com/")
        http, store = DummyHTTP(), DummyStore()
        todo = Todoist(http, "이벤트 / 기간 한정", project_id="p1", section_id="s1")
        names = set()
        one = todo.import_event(e, names, {}, store)
        two = todo.import_event(e, names, {}, store)
        self.assertIn("[등록]", one)
        self.assertIsNone(two)
        self.assertEqual(len(http.sent), 1)

    def test_no_auto_completion_without_evidence(self):
        task = {"id": "123", "content":"[원신] 일퀘", "due":{"date":"2026-01-02"}}
        class MockTodo:
            def __init__(self): self.closed = []
            def all_tasks(self): return [task]
            def complete_task(self, task, occurrence, dry_run=False):
                self.closed.append((task, occurrence))
                return True
        todo = MockTodo()
        settings = {"screen_rules": [{"enabled":True, "game":"genshin", "kind":"task", "task_name":"[원신] 일퀘",
                                     "context_patterns":["일일 의뢰"], "all_claimed_patterns":["모든 보상을 수령했습니다"],
                                     "pending_patterns":["수령 가능"]}]}
        observer = Observer(settings, todo, DummyStore())
        self.assertEqual(observer.evaluate("genshin", "일일 의뢰: 4/4 완료"), [])
        self.assertEqual(observer.evaluate("genshin", "일일 의뢰 - 모든 보상을 수령했습니다 / 수령 가능"), [])
        with patch("gametodo.observer.time.time", side_effect=[100.0, 115.0]), \
                patch("gametodo.observer.datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 10, 28, 12, tzinfo=KST)
            self.assertEqual(observer.evaluate("genshin", "일일 의뢰 모든 보상을 수령했습니다"), [])
            self.assertEqual(observer.evaluate("genshin", "일일 의뢰 모든 보상을 수령했습니다"), ["[원신] 일퀘"])
        self.assertEqual(len(todo.closed), 1)

if __name__ == "__main__": unittest.main()
