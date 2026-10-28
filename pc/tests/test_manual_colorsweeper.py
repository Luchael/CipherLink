"""User-restored Colorsweeper is a Korean manual task, never an API completion target."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from gametodo.banners import fetch_banners
from gametodo.games import task_game
from gametodo.settings import load_settings
from gametodo.task_rules import AUTO_BINDINGS, configured_bindings

ROOT = Path(__file__).resolve().parents[2]


class ManualColorsweeperTests(unittest.TestCase):
    def test_shared_manual_catalog_contains_exact_screenshot_title(self):
        for path in (ROOT / 'pc/todoist_bindings.json',
                     ROOT / 'android/app/src/main/assets/todoist_bindings.json'):
            with self.subTest(path=path.name):
                catalog = json.loads(path.read_text(encoding='utf-8'))
                self.assertNotIn('colorsweeper', catalog['excluded_games'])
                rows = [item for item in catalog['tasks'] if item['game'] == 'colorsweeper']
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]['title'], '[색지뢰] 일퀘')
                self.assertEqual(rows[0]['status'], 'manual')
                self.assertEqual(rows[0]['cadence'], 'daily')
                self.assertIsNone(rows[0]['metric'])

    def test_shared_game_metadata_allows_user_selected_installed_app(self):
        for path in (ROOT / 'pc/game_rules.json',
                     ROOT / 'android/app/src/main/assets/game_rules.json'):
            rules = json.loads(path.read_text(encoding='utf-8'))
            self.assertNotIn('colorsweeper', rules['exclude_games'])
            self.assertEqual(rules['games']['colorsweeper'], {
                'name': '컬러스위퍼', 'prefix': '색지뢰', 'label': '컬러스위퍼',
                'daily_reset_hour_kst': None, 'android_packages': []})
        self.assertEqual(task_game({'content': '[색지뢰] 일퀘'}), 'colorsweeper')
        self.assertEqual(task_game({'content': '일퀘', 'labels': ['컬러스위퍼']}), 'colorsweeper')

    def test_manual_restoration_cannot_enable_auto_completion_or_collection(self):
        self.assertFalse(any(item.game == 'colorsweeper' for item in AUTO_BINDINGS))
        bindings = configured_bindings({'account_data': {'custom_bindings': [{
            'game': 'colorsweeper', 'title': '[색지뢰] 일퀘', 'kind': 'daily', 'metric': 'daily'}]}})
        self.assertFalse(any(item.game == 'colorsweeper' for item in bindings))
        self.assertEqual(fetch_banners(None, 'colorsweeper', {'enabled': True}), [])
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'config.json'
            path.write_text(json.dumps({'game_settings': {'colorsweeper': {'enabled': True}}}))
            self.assertNotIn('colorsweeper', load_settings(path)['game_settings'])


if __name__ == '__main__':
    unittest.main()
