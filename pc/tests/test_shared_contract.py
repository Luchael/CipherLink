"""양쪽 프로젝트가 동일한 접두사·라벨을 사용하는지 검사한다."""
import json
from pathlib import Path
import unittest
from gametodo.games import GAMES

class TestSharedContract(unittest.TestCase):
    def test_game_names_and_labels(self):
        rules = json.loads((Path(__file__).resolve().parents[1] / "game_rules.json").read_text(encoding="utf-8"))
        for game, data in rules["games"].items():
            with self.subTest(game=game):
                self.assertEqual(GAMES[game].prefix, data["prefix"])
                self.assertEqual(GAMES[game].label, data["label"])
        self.assertNotIn("colorsweeper", rules["games"])

if __name__ == "__main__":
    unittest.main()
