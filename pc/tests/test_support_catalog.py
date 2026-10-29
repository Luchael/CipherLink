"""The support overview must describe every shared binding without enabling it."""
from collections import Counter
from copy import deepcopy
import unittest
from unittest.mock import Mock

from gametodo.support_catalog import (
    AUTO_DESCRIPTION, GROUPS, format_support_catalog, support_rows,
)
from gametodo.task_rules import load_todoist_catalog


class SupportCatalogTests(unittest.TestCase):
    def test_all_39_titles_and_statuses_come_from_shared_catalog(self):
        catalog = load_todoist_catalog()
        before = deepcopy(catalog)
        rows = support_rows(catalog)
        self.assertEqual(len(rows), 39)
        self.assertEqual([row.title for row in rows], [row['title'] for row in catalog['tasks']])
        self.assertEqual(Counter(row.status for row in rows),
                         {'auto': 19, 'conditional': 3, 'manual': 17})
        self.assertEqual(next(row for row in rows if row.title == '[색지뢰] 일퀘').status, 'manual')
        self.assertEqual(catalog, before)

    def test_four_display_groups_preserve_monthly_and_rotation_meanings(self):
        rows = {row.title: row for row in support_rows()}
        self.assertEqual(set(row.group for row in rows.values()), set(GROUPS))
        for title in ('[원신] 환상극', '[원신] 나선', '[립9] 심면구역', '[스소] 연합토벌'):
            self.assertEqual(rows[title].group, '월간')
        for title in ('[열차] 혼돈', '[명조] 탑', '[립9] 갈기의 게시판1'):
            self.assertEqual(rows[title].group, 'N일 주기')
        self.assertEqual(rows['[원신] 일퀘'].group, '일일')
        self.assertEqual(rows['[젠존제] 주간퀘'].group, '주간')

    def test_auto_is_conditional_on_connection_current_period_and_score(self):
        for row in support_rows():
            if row.status == 'auto':
                self.assertIn(AUTO_DESCRIPTION, row.detail)
            if row.status == 'manual':
                self.assertTrue(row.detail.startswith('수동 확인 · '))

    def test_mobile_conditional_games_remain_manual_and_pc_policy_is_explicit(self):
        mobile = {row.title: row for row in support_rows(platform='android')}
        for title in ('[명방] 일퀘', '[명조] 일퀘', '[명조] 탑'):
            self.assertTrue(mobile[title].detail.startswith('수동 확인'))
        self.assertIn('23:59 KST 하루 1회', mobile['[명방] 일퀘'].detail)
        self.assertIn('종료될 수', mobile['[명방] 일퀘'].detail)
        self.assertTrue({row.title: row for row in support_rows()}['[명방] 일퀘']
                        .detail.startswith('조건부 자동 감지'))

    def test_catalog_edits_are_reflected_without_hardcoding_task_titles(self):
        catalog = {'tasks': [{'game': 'stella', 'title': '새 수동 작업',
                              'cadence': 'weekly', 'metric': None, 'status': 'manual',
                              'note': '확인되지 않은 진행도'}]}
        rows = support_rows(catalog)
        self.assertEqual([row.title for row in rows], ['새 수동 작업'])
        self.assertIn('확인되지 않은 진행도', rows[0].detail)

    def test_overview_separates_banners_and_mobile_operation_limits(self):
        text = format_support_catalog()
        for phrase in ('PC를 계속 켜둘 필요는 없습니다', '정확한 시각을 보장하지 않습니다',
                       '한국 서버가 있으면 한국 서버', '없으면 글로벌 Asia',
                       '실제 일정 응답은 아직 미검증', '자동 등록은 보류'):
            self.assertIn(phrase, text)

    def test_pc_handler_displays_read_only_overview_in_log_page(self):
        from gametodo.gui import Desktop
        view = Mock()
        Desktop._show_support_status(view)
        view._show_page.assert_called_once_with('logs')
        message = view._print.call_args.args[0]
        self.assertIn('[원신] 일퀘', message)
        self.assertIn('[스소] 종언의 노래', message)


if __name__ == '__main__':
    unittest.main()
