"""Read-only Korean support overview built from the shared Todoist bindings."""
from dataclasses import dataclass

from .task_rules import load_todoist_catalog

GROUPS = ('일일', '주간', '월간', 'N일 주기')
AUTO_DESCRIPTION = '연결·현재 회차·점수 확인 후 자동 감지'
SERVER_GUIDANCE = '한국 서버가 있으면 한국 서버, 없으면 글로벌 Asia를 사용합니다. 출처 확인 없이 서버를 바꾸지 않습니다.'
MOBILE_GUIDANCE = (
    '휴대폰에서 독립적으로 동기화·플로팅을 사용하며 PC를 계속 켜둘 필요는 없습니다.\n'
    'Android 자동 확인은 절전·네트워크 상태에 따라 늦어질 수 있어 정확한 시각을 보장하지 않습니다.\n'
    '모바일 설정의 「설치된 게임 앱 선택해서 연결」에서 실제 설치된 한국판/글로벌판 앱을 연결하세요.'
)
BANNER_GUIDANCE = (
    '가챠 일정은 위 할 일과 별도로 관리합니다.\n'
    '원신·스타레일·젠레스 존 제로·엔드필드·림버스·명조: 한국어 PickupCal 경로 연결 대상이며 실제 일정 응답은 아직 미검증입니다.\n'
    '리버스: 1999·스텔라 소라: 한국 서비스 일정 출처 조사 중이며 자동 등록은 보류합니다.\n'
    '출처·서버·시작·종료 시각을 확인한 현재 캐릭터 픽업만 등록합니다.'
)


@dataclass(frozen=True)
class SupportRow:
    title: str
    group: str
    status: str
    detail: str


def task_group(row):
    cadence = row.get('cadence')
    if cadence == 'daily':
        return '일일'
    if cadence == 'weekly':
        return '주간'
    if cadence == 'monthly' or row.get('metric') in ('theater', 'spiral'):
        return '월간'
    if cadence in ('endgame', 'rotation'):
        return 'N일 주기'
    raise ValueError('지원 현황에 표시할 작업 주기를 확인할 수 없습니다')


def support_rows(catalog=None, platform='pc'):
    """Display metadata only. Never enable a provider or mutate a Todoist task."""
    if platform not in ('pc', 'android'):
        raise ValueError('지원 현황 표시 플랫폼 오류')
    source = load_todoist_catalog() if catalog is None else catalog
    result = []
    for row in source['tasks']:
        status = row.get('status')
        if status == 'auto':
            detail = AUTO_DESCRIPTION
            if row.get('note'):
                detail += ' · ' + row['note']
        elif status == 'conditional' and row['game'] == 'arknights':
            detail = ('조건부 자동 감지' if platform == 'pc' else '수동 확인 · Android 계정 조회 미지원')
            detail += ' · PC에서 사용자가 허용한 23:59 KST 하루 1회 조회만 가능. 게임 접속이 종료될 수 있습니다.'
        else:
            detail = '수동 확인 · ' + (row.get('note') or '개인 진행도 완료 증거 미확인')
        result.append(SupportRow(row['title'], task_group(row), status, detail))
    return tuple(result)


def format_support_catalog(catalog=None, platform='pc'):
    rows = support_rows(catalog, platform)
    lines = ['할 일 지원 현황', SERVER_GUIDANCE, MOBILE_GUIDANCE,
             '이 분류는 안내용입니다. 기존 Todoist 제목·날짜·반복·하위 작업을 변경하지 않습니다.']
    for group in GROUPS:
        lines.append('\n' + group)
        lines.extend(f'• {row.title}\n  {row.detail}' for row in rows if row.group == group)
    lines.append('\n' + BANNER_GUIDANCE)
    return '\n'.join(lines)
