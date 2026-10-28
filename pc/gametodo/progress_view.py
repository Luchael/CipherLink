"""Read-only presentation; never changes task bindings or completion policy."""
from dataclasses import dataclass

LABELS = {'daily':'일일 목표', 'weekly':'주간 목표', 'spiral':'나선', 'theater':'환상극',
          'moc':'혼돈의 기억', 'pure_fiction':'허구 이야기', 'apocalyptic':'종말의 환영',
          'arbitration':'이상 중재', 'shiyu':'시유 방어전', 'deadly':'위험한 강습전',
          'rogue_weekly':'시뮬레이션 우주 · 화폐 전쟁', 'weekly_task':'주간 일정'}

@dataclass(frozen=True)
class ProgressRow:
    title: str
    value: str
    percent: int
    state: str

def present(metric, current, maximum):
    known = type(current) is int and current >= 0 and type(maximum) is int and maximum > 0
    return ProgressRow(LABELS.get(metric, '추가 진행도'), f'{current} / {maximum}' if known else '정보 없음',
                       min(100,max(0,current*100//maximum)) if known else 0,
                       ('목표 달성' if current >= maximum else '진행 전' if current == 0 else '진행 중') if known else '확인 필요')

def status_rows(status):
    return [present('daily',status.daily.current,status.daily.maximum),
            *(present(key,g.current,g.maximum) for key,g in status.metrics.items())]
