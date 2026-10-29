"""Read-only presentation; never changes task bindings or completion policy."""
from dataclasses import dataclass

LABELS = {'daily':'일일 목표', 'weekly':'주간 목표', 'spiral':'나선', 'theater':'환상극',
          'moc':'혼돈의 기억', 'pure_fiction':'허구 이야기', 'apocalyptic':'종말의 환영',
          'arbitration':'이상 중재', 'shiyu':'시유 방어전', 'deadly':'위험한 강습전',
          'weekly_boss_used':'주간 보스', 'rogue_weekly':'시뮬레이션 우주 · 화폐 전쟁', 'weekly_mission':'주간 임무', 'weekly_task':'리두 주간 일정', 'bounty_tasks':'현상금 의뢰 횟수', 'bounty_points':'현상금 의뢰 포인트'}

@dataclass(frozen=True)
class ProgressRow:
    title: str
    value: str
    percent: int
    state: str
    detail: str = ""

def present(metric, current, maximum):
    known = type(current) is int and current >= 0 and type(maximum) is int and maximum > 0
    value = f'{current} / {maximum}' if known else '정보 없음'
    return ProgressRow(LABELS.get(metric, '추가 진행도'), value,
                       min(100,max(0,current*100//maximum)) if known else 0,
                       ('목표 달성' if current >= maximum else '진행 전' if current == 0 else '진행 중') if known else '확인 필요')

def status_rows(status):
    from dataclasses import replace
    from .live_data import Gauge
    rows=[present('daily',status.daily.current,status.daily.maximum)]
    metrics=dict(status.metrics)
    if status.game=='zzz':
        for mode in ('shiyu','deadly'):metrics.setdefault(mode,Gauge(None,None))
    for key,gauge in metrics.items():
        if key=='weekly' and status.game in ('hsr','zzz'):continue
        if key=='bounty_tasks' and gauge.current is None:continue
        row=present(key,gauge.current,gauge.maximum)
        if key=='weekly' and status.game=='genshin':row=replace(row,title='주간 보스')
        detail=(status.details.get('endgame_display') or {}).get(key,'')
        if key in ('shiyu','deadly'):
            if gauge.current is None:
                detail=(status.details.get('endgame_diagnostics') or {}).get(key,'API 기록을 확인하지 못했어요')
            else:
                row=replace(row,value=row.value+(' S' if key=='shiyu' else '별'))
                if key not in status.metric_expiries:detail='회차 확인 필요'+(' · '+detail if detail else '')
        if key=='weekly_boss_used' or (key=='weekly' and status.game=='genshin'):
            detail='주간 보상 사용 횟수'+(f' · 남은 보상 {gauge.maximum-gauge.current}회' if gauge.current is not None and gauge.maximum is not None else '')
        if key=='weekly_task':detail='주간 보상 기준 800점'+(f' · 전체 상한 {gauge.maximum:,}점' if gauge.maximum is not None else '')
        if key=='weekly_mission':detail='매주 월요일 · [엔필] 주간퀘스트 연동'
        title=(status.details.get('metric_titles') or {}).get(key,row.title)
        detail=(status.details.get('metric_notes') or {}).get(key,detail)
        rows.append(replace(row,title=title,detail=detail))
    return rows
