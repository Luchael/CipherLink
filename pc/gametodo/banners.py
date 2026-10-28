"""한국/아시아 서버 *가챠*만 조회. 이전의 일반 이벤트 수집과 완전히 독립.

데이터 출처: PickupCal 공개 HTML(한국 서버·KST 표시). 비공식 자료이므로
다른 지역 서버 페이지로 자동 대체하거나 종료일을 추측하지 않습니다.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import re
from urllib.parse import urljoin

from .games import title_for
from .models import canonical
from .pickupcal import ListItemHTML  # HTML <li> 구조 파서만 재사용 (이벤트 파서는 사용 안 함)

KST = timezone(timedelta(hours=9))
DATE = r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}"
# 픽업 페이지의 두 가지 한국 시간 표기를 모두 인식한다.
START_END = re.compile(r"시작\s*(" + DATE + r")\s*[·ㆍ]?\s*종료\s*(" + DATE + r")")
PERIOD = re.compile(r"기간\s*[·ㆍ]\s*한국\s*시간\s*:\s*(" + DATE + r")\s*~\s*(" + DATE + r")")
KINDS = ("[픽업]", "[복각]")
class UnsupportedBannerSource(ValueError):
    """An intentionally unsupported server source is a skip, not a broken API."""


SOURCE_KEYS = frozenset({"genshin", "hsr", "zzz", "wuthering", "limbus", "endfield"})


@dataclass(frozen=True)
class Banner:
    game: str
    character: str
    start: datetime  # 반드시 UTC 오프셋이 존재하는 KST 시간
    end: datetime
    source_url: str
    version: str = ""

    @property
    def key(self) -> str:
        """서버·캐릭터·시작 회차를 기준으로 ID 고정 (종료 시간 연장 시 동일 ID)."""
        plain = f"banner:v1:KR:{self.game}:{canonical(self.character)}:{self.start.isoformat()}"
        return hashlib.sha256(plain.encode("utf-8")).hexdigest()[:32]

    @property
    def title(self) -> str:
        # 버전을 실제로 확인한 경우에만 표시. 버전 모르면 지어내지 않는다.
        label = self.character + (f" ({self.version})" if self.version else "")
        return title_for(self.game, label)


def character_name(long_name: str, game_name: str) -> str | None:
    """캘린더 제목에서 캐릭터 명칭을 추출한다.

    예: [복각] 원신 - 「...」 기원: 「허계의 별·스커크(얼음)」 → 스커크
        [픽업] 젠레스 존 제로 - 「...」 - 피닉스 → 피닉스
        [픽업] 붕괴: 스타레일 - 「...」 펄 → 펄
    """
    raw = re.sub(r"^\s*\[(?:픽업|복각)\]\s*", "", long_name).strip()
    if raw.startswith(game_name):
        raw = raw[len(game_name):].lstrip(" -:")
    # 사용자가 원하는 것은 캐릭터 픽업이므로 무기/광추/음동기 전용 가챠는 제외.
    if any(term in raw for term in ("무기 기원", "무기 픽업", "무기 배너", "광추 이벤트", "광추 픽업",
                                    "음동기 픽업", "음동기 기원", "전용 무기", "전용 광추", "전용 음동기")):
        return None
    quoted = re.findall(r"[「『]([^」』]+)[」』]", raw)
    if quoted:
        # 마지막 「」 다음에 캐릭터 이름이 있는 게임
        tail = raw.split("」")[-1].split("』")[-1].strip(" -:·")
        if tail and len(tail) <= 35:
            candidate = tail
        else:
            candidate = quoted[-1].split("·")[-1]
    else:
        # 캐릭터 이름을 추출할 근거가 부족하면 설명 전체를 맹목적으로 등록하지 않음.
        candidate = raw.rsplit(" - ", 1)[-1] if " - " in raw else ""
    candidate = re.sub(r"\([^()]{1,14}\)$", "", candidate).strip(" -:·")
    if not candidate or len(candidate) > 40 or candidate in ("픽업", "복각"):
        return None
    return candidate


def parse_banners(html: str, game: str, game_name: str, base_url: str, *, version="", now=None):
    """현재 진행 중인 캐릭터 가챠만 반환; 이벤트/굿즈/무기 픽업은 제외.

    종료 시각은 날짜만이 아닌 초단위 시각 비교. 데이터가 없는 경우 건너뛰고
    실패로 기록해, 소스가 비어 있다는 이유만으로 Todoist를 닫지 않는다.
    """
    if not ("한국" in html and "KST" in html):
        raise ValueError("한국 서버/KST 근거가 없는 출처")
    if game not in SOURCE_KEYS:
        return []
    now = now or datetime.now(KST)
    parser = ListItemHTML()
    parser.feed(html)
    found = {}
    for text, links in parser.items:
        banner_link = next(((title, link) for title, link in links
                            if title.startswith(KINDS) and game_name in title), None)
        if not banner_link:
            continue
        if "한국 서버" not in text and "한국 시간" not in text:
            continue
        period = START_END.search(text) or PERIOD.search(text)
        if not period:
            continue
        start, end = (datetime.strptime(raw, "%Y-%m-%d %H:%M").replace(tzinfo=KST)
                      for raw in period.groups())
        if not start <= now < end or end <= start:
            continue
        character = character_name(banner_link[0], game_name)
        if not character:
            continue
        url = urljoin(base_url, banner_link[1])
        # 같은 일정 카드에 버전 번호가 명시된 경우에만 자동 표기한다.
        # CN/글로벌 서버의 별도 버전 데이터를 섞지 않아 KR 기준을 유지한다.
        version_match = re.search(r"(?:버전|Ver\.?|v)\s*(\d+(?:\.\d+){1,2})", text, re.I)
        reliable_version = version or (version_match.group(1) if version_match else "")
        banner = Banner(game, character, start, end, url, reliable_version)
        found[banner.key] = banner
    return list(found.values())


def fetch_banners(http, game: str, cfg: dict, *, now=None):
    """공개 페이지는 ETag/Last-Modified 캐시 이용. 인증/게임 로그인 불필요."""
    if game not in SOURCE_KEYS or not cfg.get("enabled", False):
        return []
    # 사용자가 명조의 글로벌/CN 공통 가챠 일정 사용을 허용했다.
    # 다른 게임과 같은 한국어/KST 공개 일정 파서만 사용하며, 개인 CN API는 호출하지 않는다.
    if cfg.get("source", "pickupcal") != "pickupcal":
        raise UnsupportedBannerSource("검증되지 않은 가챠 출처 · 자동 등록 건너뜀")
    slug = cfg.get("slug", game)
    if slug not in SOURCE_KEYS:
        raise ValueError("허용되지 않은 배너 출처")
    url = f"https://www.pickupcal.com/games/{slug}/"
    html = http.request(url, cache=True)
    if not isinstance(html, str):
        raise ValueError("배너 사이트가 HTML을 반환하지 않음")
    return parse_banners(html, game, cfg["name"], url,
                         version=cfg.get("version_label", ""), now=now)
