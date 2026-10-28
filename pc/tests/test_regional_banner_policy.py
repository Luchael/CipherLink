"""Synthetic public-page fixtures; live PickupCal access is a separate check."""
from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock

from gametodo.banners import KST, UnsupportedBannerSource, fetch_banners


NOW = datetime(2026, 10, 28, 12, 0, tzinfo=KST)
NAME = "명조: 워더링 웨이브"
CONFIG = {"enabled": True, "name": NAME, "source": "pickupcal", "slug": "wuthering"}


def card(label=None, start="2026-10-20 11:00", end="2026-11-10 10:59", region="한국 서버"):
    label = label or f"[픽업] {NAME} - 「소집 이름」 - 금희"
    return (f'<li><a href="/banners/fixture">{label}</a>'
            f'{region} 시작 {start} · 종료 {end}</li>')


def fetch_fixture(body, *, header="한국 서버 일정 KST", cfg=None):
    http = Mock()
    http.request.return_value = f"<h1>{header}</h1>{body}"
    return fetch_banners(http, "wuthering", cfg or CONFIG, now=NOW), http


class RegionalBannerPolicyTests(TestCase):
    def test_wuthering_uses_fixed_public_korean_calendar(self):
        found, http = fetch_fixture(card())
        http.request.assert_called_once_with(
            "https://www.pickupcal.com/games/wuthering/", cache=True)
        self.assertEqual([b.title for b in found], ["[명조] 금희"])
        self.assertEqual(found[0].start.isoformat(), "2026-10-20T11:00:00+09:00")
        self.assertEqual(found[0].end.isoformat(), "2026-11-10T10:59:00+09:00")
        self.assertEqual(found[0].source_url, "https://www.pickupcal.com/banners/fixture")
        # Same fixture and key are checked by the actual Android fetch/parser test.
        self.assertEqual(found[0].key, "0928a4a1d4e56d0a09d7a2382ae3f6cf")

    def test_default_source_uses_same_validated_path(self):
        cfg = {k: v for k, v in CONFIG.items() if k != "source"}
        found, _ = fetch_fixture(card(), cfg=cfg)
        self.assertEqual(len(found), 1)

    def test_unverified_source_is_rejected_before_network(self):
        http = Mock()
        with self.assertRaises(UnsupportedBannerSource):
            fetch_banners(http, "wuthering", {**CONFIG, "source": "unverified"}, now=NOW)
        http.request.assert_not_called()

    def test_weapon_event_expired_future_and_wrong_game_do_not_create_banners(self):
        body = "".join([
            card(),
            card(f"[픽업] {NAME} - 무기 픽업 - 무기"),
            card(f"[이벤트] {NAME} - 「이벤트」 - 캐릭터"),
            card(end="2026-10-28 12:00"),
            card(start="2026-11-01 11:00"),
            card("[픽업] 붕괴: 스타레일 - 「다른 게임」 - 캐릭터"),
        ])
        found, _ = fetch_fixture(body)
        self.assertEqual([b.character for b in found], ["금희"])

    def test_missing_korean_or_kst_evidence_is_rejected(self):
        for header in ("한국 서버 CST", "Global Asia UTC+8", "中国服务器 CST"):
            with self.subTest(header=header), self.assertRaises(ValueError):
                fetch_fixture(card(region="서버 미상"), header=header)

    def test_item_requires_region_and_exact_valid_period(self):
        for body in (card(region="서버 미상"), card(start="2026-10-20", end="2026-11-10"),
                     card(start="2026-11-10 10:59", end="2026-10-20 11:00")):
            with self.subTest(body=body):
                found, _ = fetch_fixture(body)
                self.assertEqual(found, [])

    def test_empty_or_changed_page_does_not_create_banners(self):
        for body in ("", "<div>날짜를 찾을 수 없는 새 구조</div>"):
            found, _ = fetch_fixture(body)
            self.assertEqual(found, [])

    def test_non_html_response_is_rejected(self):
        http = Mock()
        http.request.return_value = {"error": "fixture"}
        with self.assertRaises(ValueError):
            fetch_banners(http, "wuthering", CONFIG, now=NOW)
