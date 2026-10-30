"""Read-only SDK-to-parser regression; fixtures contain no account data."""
import asyncio
from copy import deepcopy
import unittest
from unittest.mock import AsyncMock, patch

import genshin

from gametodo.endgame_records import fetch, parse

START, END = 1791000000, 1801000000


class ShiyuResponseContractTests(unittest.TestCase):
    def envelope(self, record, version='v2'):
        return {'hadal_ver': version, 'nick_name': '', 'icon': '',
                'hadal_info_' + version: {'hadal_begin_time': START,
                                          'hadal_end_time': END, **record}}

    def via_sdk(self, envelope):
        async def run():
            client = genshin.Client()
            with patch.object(client, '_request_zzz_record', AsyncMock(return_value=deepcopy(envelope))), \
                 patch.object(client, 'get_deadly_assault', AsyncMock(return_value={'total_star': 9})):
                return await fetch(client, 1300000000, 'zzz')
        return asyncio.run(run())

    def test_sdk_v1_raw_floor_alias_is_read(self):
        result, errors = self.via_sdk(self.envelope({
            'has_data': True,
            'all_floor_detail': [{'layer_index': i, 'layer_id': i, 'rating': 'S'} for i in range(1, 8)],
            'rating_list': [{'rating': 'S', 'times': 7}],
        }, 'v1'))
        self.assertNotIn('shiyu', errors, errors.get('shiyu'))
        self.assertEqual((result['shiyu'].value, result['shiyu'].goal), (7, 7))
        self.assertEqual(result['deadly'].value, 9)

    def test_sdk_partial_v2_keeps_known_fourth_s(self):
        result, errors = self.via_sdk(self.envelope({
            'zone_id': 1, 'pass_fifth_floor': False,
            'fourth_layer_detail': {'rating': 'S'}, 'fitfh_layer_detail': None,
        }))
        self.assertNotIn('shiyu', errors, errors.get('shiyu'))
        self.assertEqual((result['shiyu'].value, result['shiyu'].goal), (1, 4))
        self.assertFalse(result['shiyu'].filled)

    def test_stars_never_substitute_for_s_grades(self):
        self.assertIsNone(parse('shiyu', self.envelope({
            'brief_info': {'total_star': 5, 'max_star': 5}})))

    def test_summary_s_plus_and_high_scores_do_not_prove_room_s(self):
        self.assertIsNone(parse('shiyu', self.envelope({
            'brief': {'rating': 'S+', 'score': 150000, 'max_score': 150000},
            'fitfh_layer_detail': {'layer_challenge_info_list': [{'score': 50000}] * 3},
            'pass_fifth_floor': True})))

    def complete(self, passed=True):
        return self.envelope({'fourth_layer_detail': {'rating': 'S'},
            'fitfh_layer_detail': {'layer_challenge_info_list': [
                {'layer_id': i, 'rating': 'S', 'score': 100} for i in range(3)]},
            'pass_fifth_floor': passed})

    def test_s_ratings_count_without_a_point_threshold(self):
        results, errors = self.via_sdk(self.complete())
        self.assertEqual(errors, {})
        self.assertEqual((results['shiyu'].value, results['shiyu'].goal), (4, 4))
        self.assertTrue(results['shiyu'].filled)

    def test_pass_flag_never_changes_the_observed_s_count(self):
        record = parse('shiyu', self.complete(False))
        self.assertEqual(record.value, 4)
        self.assertFalse(record.filled)
        self.assertIn('자동 완료 보류', record.display_detail)

    def test_missing_fourth_keeps_three_fifth_s_without_inventing_fourth(self):
        payload = self.complete()
        del payload['hadal_info_v2']['fourth_layer_detail']
        record = parse('shiyu', payload)
        self.assertEqual((record.value, record.goal), (3, 4))
        self.assertFalse(record.filled)

    def test_duplicate_room_ids_cannot_complete(self):
        payload = self.complete()
        payload['hadal_info_v2']['fitfh_layer_detail']['layer_challenge_info_list'][1]['layer_id'] = 0
        self.assertIsNone(parse('shiyu', payload))

    def test_v1_explicit_grade_counts(self):
        record = parse('shiyu', self.envelope({'rating_list': [
            {'rating': 'S', 'times': 6}, {'rating': 'A', 'times': 1}]}, 'v1'))
        self.assertEqual((record.value, record.goal), (6, 7))
        self.assertFalse(record.filled)

    def test_diagnostic_never_echoes_unrecognized_values(self):
        results, errors = self.via_sdk(self.envelope({'fourth_layer_detail': {
            'rating': 'DO_NOT_ECHO'}, 'zone_id': 1, 'nick_name': 'DO_NOT_ECHO'}))
        self.assertNotIn('shiyu', results)
        self.assertIn('S 등급', errors['shiyu'])
        self.assertNotIn('DO_NOT_ECHO', str(errors))

    def test_account_reader_preserves_completion_hold_and_s_display(self):
        from gametodo.account_sources import read_hoyolab
        from gametodo.progress_view import status_rows
        record = parse('shiyu', self.complete(False))
        with patch('gametodo.account_sources.read_secret', return_value='test-cookie'), \
             patch('gametodo.account_sources._read_hoyolab_async', AsyncMock(return_value=({}, {'shiyu': record}, {}))):
            _, status = read_hoyolab('zzz', {'hoyolab': {'uids': {'zzz': '1300000000'}}})
        self.assertFalse(status.metrics['shiyu'].filled)
        row = next(row for row in status_rows(status) if row.title == '시유 방어전')
        self.assertEqual(row.value, '4 / 4 S')
        self.assertEqual(row.state, '확인 필요')

    def test_current_v2_unattempted_displays_no_record(self):
        from datetime import datetime, timezone
        now = int(datetime.now(timezone.utc).timestamp())
        payload = self.envelope({'zone_id': 1, 'pass_fifth_floor': False,
            'hadal_begin_time': now - 3600, 'hadal_end_time': now + 3600,
            'fourth_layer_detail': None, 'fitfh_layer_detail': None, 'brief': None})
        results, errors = self.via_sdk(payload)
        self.assertNotIn('shiyu', errors)
        record = results['shiyu']
        self.assertEqual((record.value, record.goal), (0, 4))
        self.assertTrue(record.current())
        self.assertFalse(record.filled)
        self.assertFalse(record.has_record)
        self.assertIn('미도전', record.display_detail)
        from gametodo.account_sources import read_hoyolab
        from gametodo.progress_view import status_rows
        with patch('gametodo.account_sources.read_secret', return_value='test-cookie'), \
             patch('gametodo.account_sources._read_hoyolab_async', AsyncMock(return_value=({}, {'shiyu': record}, {}))):
            _, status = read_hoyolab('zzz', {'hoyolab': {'uids': {'zzz': '1300000000'}}})
        row = next(row for row in status_rows(status) if row.title == '시유 방어전')
        self.assertEqual(row.value, '기록 없음')
        self.assertEqual(row.state, '미도전')
        self.assertFalse(row.show_bar)

    def test_missing_period_and_unexplained_positive_points_are_not_zero(self):
        raw = {'zone_id': 1, 'pass_fifth_floor': False,
               'fourth_layer_detail': None, 'fitfh_layer_detail': None}
        self.assertIsNone(parse('shiyu', raw))
        self.assertIsNone(parse('shiyu', self.envelope({**raw, 'brief': {'score': 30000}})))

    def test_unattempted_with_explicit_no_data_flag_can_display_zero(self):
        record = parse('shiyu', self.envelope({'zone_id': 1, 'has_data': False,
            'pass_fifth_floor': False, 'fourth_layer_detail': None, 'fitfh_layer_detail': None}))
        self.assertEqual((record.value, record.goal), (0, 4))
        self.assertFalse(record.filled)
