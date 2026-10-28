"""v0.2: 게임별 제목/라벨, 기존 작업 보정, 외부행사 제외, 플로팅 API."""
import json
import unittest
from datetime import datetime
from urllib.parse import parse_qs
from unittest.mock import patch

from gametodo.games import GAMES, task_game, title_for
from gametodo.bridge import tasks_for_game
from gametodo.hoyolab import genshin_daily_claimed, reset_cycle_date, KST
from gametodo.models import Event, canonical, should_import
from gametodo.settings import load_settings
from gametodo.todoist import Todoist


class DummyStore:
    def __init__(self): self.events = {}
    def event_task(self, key): return self.events.get(key)
    def record_event(self, key, tid, due): self.events[key] = (tid, due)


class HTTP:
    def __init__(self): self.calls = []
    def request(self, url, method="GET", payload=None, **kwargs):
        if method == "POST" and url.endswith("/sync"):
            cmd = json.loads(parse_qs(payload.decode())["commands"][0])[0]
            self.calls.append(cmd)
            return {"sync_status": {cmd["uuid"]: "ok"},
                    "temp_id_mapping": {cmd.get("temp_id", ""): "id-new"}}
        return {}


class TestV02(unittest.TestCase):
    def make_event(self, game):
        return Event(game, "기간한정 선물", datetime(2026, 10, 26, tzinfo=KST),
                     datetime(2026, 11, 5, tzinfo=KST), "https://example.org/")

    def test_game_prefix_labels(self):
        expected = {
            "genshin": ("원신", "원신"), "hsr": ("열차", "스타레일"),
            "zzz": ("젠존제", "젠레스존제로"), "wuthering": ("명조", "명조:워더링웨이브"),
            "limbus": ("림컴", "림버스컴퍼니"), "stella": ("스소", "스텔라소라"),
            "reverse1999": ("립9", "리버스1999"), "colorsweeper": ("색지뢰", "컬러스위퍼"),
            "arknights": ("명방", "명일방주"), "endfield": ("엔필", "명일방주:엔드필드"),
        }
        for key, (prefix, label) in expected.items():
            with self.subTest(game=key):
                self.assertEqual((GAMES[key].prefix, GAMES[key].label), (prefix, label))
                self.assertEqual(title_for(key, "이벤트"), f"[{prefix}] 이벤트")
                http = HTTP()
                todo = Todoist(http, "이벤트 / 기간 한정", project_id="p", section_id="s")
                todo.import_event(self.make_event(key), set(), {}, DummyStore())
                args = http.calls[0]["args"]
                self.assertEqual(args["content"], f"[{prefix}] 기간한정 선물")
                self.assertEqual(args["labels"], [label])
                self.assertEqual(args["due"], {"date": "2026-11-05"})

    def test_offline_omitted_and_ingame_retained(self):
        external = ["엔드필드 1주년 페스티벌", "오프라인 행사 현장 참여",
                    "네이버 팬아트 공모전", "경품 댓글 이벤트",
                    "일산 KINTEX 행사", "갤럭시 스토어 할인 쿠폰"]
        for title in external:
            self.assertFalse(should_import(title), title)
        self.assertTrue(should_import("칼리의 꽃과 풀 동화"))
        self.assertTrue(should_import("기간 한정 도전 이벤트"))

    def test_same_title_different_game_is_allowed(self):
        names = {("genshin", canonical("[원신] 기간한정 선물"))}
        http = HTTP()
        todo = Todoist(http, "이벤트 / 기간 한정", project_id="p", section_id="s")
        self.assertIn("[등록]", todo.import_event(self.make_event("hsr"), names, {}, DummyStore()))

    def test_existing_marker_migrates_name_label_without_duplicate(self):
        ev = self.make_event("hsr")
        original = {"id": "old-id", "content": "기간한정 선물", "labels": ["업무"],
                    "due": {"date": "2026-11-05"}, "description": f"GameTodo-ID: {ev.key}\n게임: hsr / 서버: KR"}
        http, db = HTTP(), DummyStore()
        todo = Todoist(http, "이벤트 / 기간 한정", project_id="p", section_id="s")
        existing, markers = todo.indexed([original])
        msg = todo.import_event(ev, existing, markers, db)
        self.assertIn("보정", msg)
        self.assertEqual(len(http.calls), 1)
        self.assertEqual(http.calls[0]["type"], "item_update")
        self.assertEqual(http.calls[0]["args"]["labels"], ["스타레일", "업무"])
        self.assertEqual(http.calls[0]["args"]["content"], "[열차] 기간한정 선물")
        self.assertIsNone(todo.import_event(ev, existing, markers, db))

    def test_floating_filter_by_game_labels(self):
        tasks = [
            {"id": "1", "content": "[원신] 일퀘", "labels": ["원신"]},
            {"id": "2", "content": "[열차] 주간퀘", "labels": ["스타레일"]},
            {"id": "3", "content": "[엔필] 이벤트", "labels": ["명일방주:엔드필드"]},
            {"id": "4", "content": "[원신] 지난 완료", "labels": ["원신"], "checked": True},
        ]
        self.assertEqual([x["id"] for x in tasks_for_game(tasks, "genshin")], ["1"])
        self.assertEqual([x["id"] for x in tasks_for_game(tasks, "endfield")], ["3"])
        self.assertEqual(task_game(tasks[1]), "hsr")

    def test_hoyolab_daily_goal_even_without_reward_claim(self):
        class Note: pass
        n = Note(); n.completed_commissions = 4; n.max_commissions = 4
        n.claimed_commission_reward = False
        self.assertTrue(genshin_daily_claimed(n))
        n.claimed_commission_reward = True
        self.assertTrue(genshin_daily_claimed(n))
        del n.claimed_commission_reward
        self.assertTrue(genshin_daily_claimed(n))
        self.assertEqual(reset_cycle_date(datetime(2026, 10, 27, 4, 59, tzinfo=KST)), "2026-10-26")
        self.assertEqual(reset_cycle_date(datetime(2026, 10, 27, 5, 1, tzinfo=KST)), "2026-10-27")

    def test_legacy_config_enables_endfield(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.json"
            path.write_text(json.dumps({"game_settings": {"endfield": {"enabled": False}}}))
            self.assertTrue(load_settings(str(path))["game_settings"]["endfield"]["enabled"])
            path.write_text(json.dumps({"schema_version": 2, "game_settings": {"endfield": {"enabled": False}}}))
            self.assertFalse(load_settings(str(path))["game_settings"]["endfield"]["enabled"])


if __name__ == "__main__":
    unittest.main()
