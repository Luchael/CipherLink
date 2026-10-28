"""KR 서버 일정이 명시된 PickupCal HTML을 읽는 어댑터.

공식 게임 API가 아닌 팬 사이트입니다. 화면 구조 변경 시 빈 수집 결과를 오류로
기록하며, 검증되지 않은 CN/글로벌 일정으로 자동 대체하지 않습니다.
"""
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
import re

from .models import Event, extract_short_name, should_import

KST = timezone(timedelta(hours=9))
DATE_RX = r"\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2})?"
PERIOD_RX = re.compile(r"기간\s*[·ㆍ]\s*한국\s*시간\s*:\s*(" + DATE_RX + r")\s*~\s*(" + DATE_RX + r")")


class ListItemHTML(HTMLParser):
    """검색봇용 목록(li)의 앵커 및 날짜만 파싱해 전체 DOM/JS 의존을 피함."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.parts = []
        self.links = []
        self.anchor_href = None
        self.anchor_parts = []
        self.items = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "li":
            if self.depth == 0:
                self.parts, self.links = [], []
            self.depth += 1
        if tag == "a" and self.depth:
            self.anchor_href = attrs.get("href", "")
            self.anchor_parts = []

    def handle_data(self, data):
        if self.depth:
            self.parts.append(data)
            if self.anchor_href is not None:
                self.anchor_parts.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.anchor_href is not None:
            label = " ".join(" ".join(self.anchor_parts).split())
            self.links.append((label, self.anchor_href))
            self.anchor_href = None
        if tag == "li" and self.depth:
            self.depth -= 1
            if self.depth == 0:
                self.items.append((" ".join(" ".join(self.parts).split()), self.links[:]))


def parse_datetime(value, end=False):
    fmt = "%Y-%m-%d %H:%M" if len(value.strip()) > 10 else "%Y-%m-%d"
    d = datetime.strptime(value.strip(), fmt).replace(tzinfo=KST)
    if end and fmt == "%Y-%m-%d":
        d = d.replace(hour=23, minute=59, second=59)
    return d


def parse_pickupcal(html: str, game_key: str, game_name: str, page_url: str):
    if "한국" not in html or "KST" not in html:
        raise ValueError("KR/KST 출처인지 확인할 수 없습니다")
    parser = ListItemHTML()
    parser.feed(html)
    events = []
    candidates = 0
    for text, links in parser.items:
        # 이벤트 목록 외 링크, 버전/픽업/공식방송은 제외.
        event_link = next(((title, href) for title, href in links
                           if title.startswith("[이벤트]") and (game_name in title)), None)
        if not event_link:
            continue
        candidates += 1
        match = PERIOD_RX.search(text)
        if not match:
            continue
        long_name, url = event_link
        raw = re.sub(r"^\[이벤트\]\s*" + re.escape(game_name) + r"\s*-\s*", "", long_name).strip()
        short = extract_short_name(raw)
        # 제목에 괄호 속 날짜/부연 설명이 들어있을 때만 짧게 줄이고 설명은 유지.
        description = text.split("(기간", 1)[0]
        if not should_import(raw, description):
            continue
        starts, ends = parse_datetime(match[1]), parse_datetime(match[2], end=True)
        if ends <= starts:
            continue
        official = next((href for title, href in links if "공식 출처" in title), "")
        events.append(Event(game_key, short, starts, ends, official or page_url, description, server="KR"))
    if not candidates:
        raise ValueError(f"{game_name}: 페이지에서 이벤트 목록을 못 찾음 (HTML 구조 변경 또는 수집 없음)")
    return events


def fetch_game(http, game_key: str, cfg: dict):
    if cfg.get("source") == "ics":
        from .ics_source import fetch_ics
        return fetch_ics(http, game_key, cfg)
    if cfg.get("source") != "pickupcal":
        raise ValueError("검증되지 않은 서버 출처의 자동 수집은 차단됩니다")
    slug = cfg["slug"]
    if slug not in {"genshin", "hsr", "zzz", "wuthering", "limbus", "endfield"}:
        raise ValueError("허용되지 않은 PickupCal 게임 식별자")
    url = f"https://www.pickupcal.com/games/{slug}/"
    html = http.request(url, cache=True)
    if not isinstance(html, str):
        raise ValueError("예상치 못한 응답 형식")
    return parse_pickupcal(html, game_key, cfg["name"], url)
