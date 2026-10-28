"""코어 자료형 및 이름 정규화. 네트워크 호출 없음."""
from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import re
import unicodedata
import uuid


@dataclass(frozen=True)
class Event:
    game: str
    name: str
    starts_at: datetime  # UTC offset이 포함된 datetime
    ends_at: datetime
    url: str
    description: str = ""
    server: str = "KR"

    @property
    def due_date(self) -> str:
        return self.ends_at.date().isoformat()  # 입력 자체가 KST임을 보장

    @property
    def key(self) -> str:
        # 종료 연장으로 인해 ID가 바뀌지 않도록 시작일만 사용.
        payload = f"v1|{self.game}|{canonical(self.name)}|{self.starts_at.date()}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def canonical(value: str) -> str:
    value = re.sub(r"^\s*\[[^\]]+\]\s*", "", value)
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(c for c in value if c.isalnum())


def command_uuid(action: str, target: str) -> str:
    """기기 간 결정적 UUID: Todoist Sync API에서 동일 명령 재전송 시 중복 방지."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://gametodo.local/v1/{action}/{target}"))


EXCLUDED = (
    "환상극", "나선", "가상몽유", "심면구역", "연합토벌", "연합 토벌",
    "지맥제압전", "지맥 제압전", "이상중재", "혼돈", "허구", "종말",
    "시유방어전", "강습전", "탑", "폐허", "매트릭스", "재앙의전선",
    "종언의노래", "갈기의게시판",
)
EXCLUDED_NORMALIZED = tuple(canonical(x) for x in EXCLUDED)

# 게임 외 커뮤니티 홍보, 추첨 이벤트를 게임 내 모든 보상 수령 대상으로 취급하지 않는다.
EXTERNAL_ONLY = (
    "댓글 이벤트", "공유 이벤트", "추첨 이벤트", "공모전", "팬아트",
    "공식방송", "생방송", "리딤코드", "sns", "트위터", "오프라인",
    "참여 인증", "사전예약", "해시태그", "방문 이벤트", "출시 기념",
    "경품", "댓글", "전시회", "페스티벌", "팝업 스토어", "팝업스토어",
    "콜라보 카페", "현장 방문", "현장 참여", "k in tex", "kintex",
    "갤럭시 스토어", "할인 쿠폰", "상품권", "굿즈 판매",
    "chzzk drops", "twitch drops", "디스코드 이벤트", "whatsapp",
)


def should_import(name: str, description: str = "") -> bool:
    if not name or len(name) > 90:
        return False
    normalized = canonical(name)
    if any(t in normalized for t in EXCLUDED_NORMALIZED):
        return False
    full = (name + " " + description).lower()
    # 제목/설명 둘 다 검사. 외부 캠페인에 '이벤트' 표기가 있어도 등록하지 않음.
    if any(t in full for t in EXTERNAL_ONLY):
        return False
    return True


def extract_short_name(raw: str) -> str:
    """작업 제목만 간결하게. 이벤트 상세 설명은 Todoist 설명 필드에 저장."""
    name = re.sub(r"^\s*[\[\(]이벤트[\]\)]\s*", "", raw).strip()
    name = re.sub(r"^[^\-]{1,24}\s+-\s+", "", name).strip()
    # 설명성 제목 중 따옴표 안 이벤트 이름을 우선 사용.
    m = re.search(r"[「『]([^」』]+)[」』]", name)
    if m and len(m.group(1)) <= 45:
        return m.group(1).strip()
    return name[:70].strip()
