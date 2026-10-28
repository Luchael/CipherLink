import copy
import json
from pathlib import Path
from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock
from gametodo.banners import KST, fetch_banners

FIXTURE = Path(__file__).resolve().parents[2] / 'tests/fixtures/stella_kr_20261028.json'
NOW = datetime(2026, 10, 28, 12, tzinfo=KST)

class StellaBannersTests(TestCase):
    def fetch(self, payload, now=NOW):
        api = Mock()
        api.request.return_value = payload
        return fetch_banners(api, 'stella', {'enabled': True, 'source': 'ennead'}, now=now), api

    def test_actual_public_kr_response_character_only_and_kst(self):
        rows, api = self.fetch(json.loads(FIXTURE.read_text()))
        self.assertEqual({r.character for r in rows}, {'세이나(기원)', '호타루'})
        self.assertTrue(all(r.start.hour == 13 and r.end.hour == 11 for r in rows))
        self.assertTrue(all(r.start.utcoffset().total_seconds() == 32400 for r in rows))
        api.request.assert_called_once_with('https://api.ennead.cc/stella/banners?lang=KR', cache=True)

    def test_invalid_dates_and_unsupported_names_never_import(self):
        original = json.loads(FIXTURE.read_text())['current'][1]
        for patch in ({'startTime': None}, {'endTime': '2026-11-10'},
                      {'endTime': original['startTime']}, {'rateUp': None},
                      {'bannerType': '레코드 기간 한정 모집'}):
            row = copy.deepcopy(original); row.update(patch)
            self.assertEqual(self.fetch({'current': [row]})[0], [])
        row = copy.deepcopy(original)
        row['rateUp']['fiveStar']['entries'][0]['name'] = 'Unlocalized name'
        self.assertEqual(self.fetch({'current': [row]})[0], [])

    def test_source_current_label_does_not_override_end_time(self):
        payload = json.loads(FIXTURE.read_text())
        rows, _ = self.fetch(payload, datetime(2026, 12, 1, tzinfo=KST))
        self.assertEqual(rows, [])
