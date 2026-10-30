# -*- coding: utf-8 -*-
"""Read-only, per-season HoYoLAB endgame scoring; uncertain data never auto-completes.

Original endpoints/model names cross-checked against genshin.py v1.7.31 documentation.
Never emit raw JSON, cookies, or character identifiers in error reports.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

ASIA = timezone(timedelta(hours=8))
TARGETS = {'spiral':36, 'theater':12, 'moc':36, 'pure_fiction':12,
           'apocalyptic':12, 'deadly':9, 'arbitration':12}
METHODS = {'genshin': {'spiral':'get_genshin_spiral_abyss', 'theater':'get_imaginarium_theater'},
           'hsr': {'moc':'get_starrail_challenge', 'pure_fiction':'get_starrail_pure_fiction',
                   'apocalyptic':'get_starrail_apc_shadow','arbitration':'get_anomaly_arbitration'},
           'zzz': {'shiyu':'get_shiyu_defense','deadly':'get_deadly_assault'}}

@dataclass(frozen=True)
class EndgameProgress:
    mode: str
    value: int
    goal: int
    starts: int | None  # unix seconds
    ends: int | None
    basis: str
    display_detail: str = ""
    completion_verified: bool = True
    has_record: bool = True
    @property
    def filled(self): return self.completion_verified and self.goal > 0 and self.value >= self.goal
    def current(self, when: datetime | None=None):
        now = (when or datetime.now(timezone.utc)).timestamp()
        return self.starts is not None and self.ends is not None and self.starts+1200 <= now < self.ends

def field(obj: Any, *paths):
    for path in paths:
        at=obj
        for piece in path.split('.'):
            at=at.get(piece) if isinstance(at,dict) else None
        if at is not None: return at
    return None

def integer(obj,*paths):
    x=field(obj,*paths)
    if type(x) is int:return x
    if isinstance(x,str) and x.strip().isdigit(): return int(x.strip())
    return None

def date_value(value):
    if type(value) in (int,float) or (isinstance(value,str) and value.isdigit()):
        n=int(value)
        if n>10**12: n//=1000
        return n if 1_500_000_000<=n<=5_000_000_000 else None
    if isinstance(value,dict):
        # genshin.py adds {timestamp, tzinfo} to Unix timestamps even for raw=True.
        if 'timestamp' in value:return date_value(value['timestamp'])
        try:
            # HoYoLAB PartialTime sometimes uses year/month/day and nested time values.
            year=int(value['year']); month=int(value['month']); day=int(value['day'])
            hour=int(value.get('hour',0)); minute=int(value.get('minute',0)); second=int(value.get('second',0))
            return int(datetime(year,month,day,hour,minute,second,tzinfo=ASIA).timestamp())
        except (KeyError,TypeError,ValueError):return None
    if isinstance(value,str):
        try:
            dt=datetime.fromisoformat(value.replace('Z','+00:00'))
            if dt.tzinfo is None:dt=dt.replace(tzinfo=ASIA)
            return int(dt.timestamp())
        except ValueError: return None
    return None

def period(obj):
    return (date_value(field(obj,'start_time','begin_time','schedule_start_time','start_date_time','hadal_begin_time','schedule.start_time','schedule.start_datetime','schedule.begin_time','hadal_info_v2.begin_time','hadal_info_v1.begin_time','hadal_info_v2.hadal_begin_time','hadal_info_v1.hadal_begin_time')),
            date_value(field(obj,'end_time','finish_time','schedule_end_time','end_date_time','hadal_end_time','schedule.end_time','schedule.end_datetime','schedule.finish_time','hadal_info_v2.end_time','hadal_info_v1.end_time','hadal_info_v2.hadal_end_time','hadal_info_v1.hadal_end_time')))

def choose_record(raw, mode):
    if not isinstance(raw,dict):return {}
    root=raw
    for _ in range(3):
        inner=next((root[k] for k in ('data','detail','record') if isinstance(root.get(k),dict)),None)
        if inner is None: break
        root=inner
    # Deadly Assault has top-level total_star and a list of boss records.
    # Never discard the top-level total_star by selecting list[0].
    if mode == 'deadly' and integer(root, 'total_star', 'total_stars') is not None:
        return root
    # Actual Imaginarium Theater response: {data: [ {schedule, stat...}, ... ], is_unlock...}
    arrays=['data'] if mode=='theater' else []
    arrays+=['list','records','schedules','schedule_list']
    for key in arrays:
        seq=root.get(key)
        if not isinstance(seq,list):continue
        rows=[x for x in seq if isinstance(x,dict)]
        if not rows:return {}
        marked=[x for x in rows if integer(x,'schedule.schedule_type','schedule_type')==1]
        if len(marked)==1:return marked[0]
        if len(rows)==1:return rows[0]
        dates=[(period(x)[0],x) for x in rows]
        if all(s is not None for s,_ in dates):
            dates.sort(key=lambda x:x[0],reverse=True)
            if dates[0][0]>dates[1][0]:return dates[0][1]
        return {}
    return root

def _stella(record):
    rows=field(record,'stat.get_medal_round_list','get_medal_round_list',
               'stat.star_challenge_stellas','stats.star_challenge_stellas','star_challenge_stellas')
    if isinstance(rows,list) and rows and all(type(v) is bool for v in rows):
        return sum(rows),'act-level stella boolean list'
    if isinstance(rows,list) and rows and all(type(v) is int and v in (0,1) for v in rows):
        return sum(rows),'act-level stella 0/1 list'
    # Only explicitly named stella totals, never medal_num or number of acts.
    count=integer(record,'stella_num','stella_count','stat.stella_num','stats.stella_num',
                  'stat.total_stella','stats.total_stella')
    return count,'explicit stella count'

def _peak(record):
    rows=field(record,'challenge_peak_records')
    if not isinstance(rows,list):return record
    windows=[]
    for row in rows:
        if not isinstance(row,dict):return {}
        start,end=period(row.get('group',row))
        if start is None or end is None or end<=start:return {}
        windows.append((start,end,row))
    now=datetime.now(timezone.utc).timestamp()
    active=[row for start,end,row in windows if start<=now<end]
    if len(active)==1:return active[0]
    if len(active)>1:return {}
    return max(windows,key=lambda t:t[0])[2] if windows else {}

def _period_from_groups(record):
    windows=[]
    for row in field(record,'groups') or []:
        if not isinstance(row,dict):continue
        a,b=period(row)
        if a is not None and b is not None and b>a: windows.append((a,b))
    now=datetime.now(timezone.utc).timestamp()
    active=[(a,b) for a,b in windows if a<=now<b]
    return active[0] if len(active)==1 else (None,None)

def _deadly(record):
    stars=integer(record,'total_star','total_stars')
    if field(record,'has_data') is False:
        empty_normal=field(record,'list') == []
        empty_hard=field(record,'hard_list') == []
        if stars==0 and empty_normal and empty_hard:
            return 0,'current season not attempted (normal 0/9, adversity unavailable)'
        return None,'no data, not verified'
    if stars is not None and 0<=stars<=9:return stars,'API normal mode total_star (hard_list excluded)'
    rows=field(record,'list','challenges','challenge_list')
    if isinstance(rows,list) and len(rows)==3 and all(isinstance(x,dict) for x in rows):
        direct=[integer(x,'total_star','star') for x in rows]
        if all(x is not None and 0<=x<=3 for x in direct):return sum(direct),'sum of per-boss stars'
        points=[integer(x,'score') for x in rows]
        if all(x is not None and x>=0 for x in points):
            return sum(3 if p>=20000 else 2 if p>=14000 else 1 if p>=6000 else 0 for p in points),'per-boss score tiers 6000/14000/20000'
    return None,'missing per-boss records'

def _shiyu_record(record):
    version=field(record,'hadal_ver')
    # genshin.py removes both the version tag and the versioned envelope.
    if version in ('v1','v2'):
        record=field(record,'hadal_info_'+version) or record
    elif version is not None:
        return None,{}
    elif isinstance(field(record,'hadal_info_v2'),dict):
        version='v2';record=record['hadal_info_v2']
    elif isinstance(field(record,'hadal_info_v1'),dict):
        version='v1';record=record['hadal_info_v1']
    elif any(k in record for k in ('fourth_layer_detail','fitfh_layer_detail','fifth_layer_detail','pass_fifth_floor','zone_id')):
        version='v2'
    elif any(k in record for k in ('all_floor_detail','floors','rating_list')):
        version='v1'
    return version,record


def _shiyu(record):
    """Count API S ratings. Missing records/points/summary rank cannot prove S."""
    version,o=_shiyu_record(record)
    unknown=(None,None,False,'',False)
    if field(o,'has_data') is False and version!='v2':return unknown
    known={'S','A','B'}
    def grade(row):
        value=field(row,'rating')
        return value.strip().upper() if isinstance(value,str) else None
    def distinct(rows):
        ids=[field(row,'layer_id') for row in rows]
        return not any(v is not None for v in ids) or (all(type(v) is int for v in ids) and len(set(ids))==len(ids))
    if version=='v1':
        rows=field(o,'all_floor_detail','floors')
        if isinstance(rows,list) and 0<len(rows)<=7 and distinct(rows):
            grades=[grade(row) for row in rows]
            if all(v in known for v in grades):
                return grades.count('S'),7,True,'확인된 S · 구형 시유 7개 노드 기준',True
        # Public raw API also exposes explicit grade counts, not stars.
        ratings=field(o,'rating_list')
        if isinstance(ratings,list) and 0<len(ratings)<=3:
            grades=[grade(row) for row in ratings]
            counts=[integer(row,'times') for row in ratings]
            if (all(v in known for v in grades) and len(set(grades))==len(grades)
                    and all(v is not None and 0<=v<=7 for v in counts) and sum(counts)<=7):
                return sum(n for g,n in zip(grades,counts) if g=='S'),7,True,'확인된 S · 구형 시유 등급별 횟수',True
        return unknown
    if version!='v2':return unknown
    # The SDK declares both frontier details/brief optional. An explicit failure
    # to pass + no challenge evidence + an actual season window is a zero record,
    # not an API failure. Never turn missing authentication/schema/period into 0.
    fourth_detail=field(o,'fourth_layer_detail')
    fifth_detail=field(o,'fitfh_layer_detail','fifth_layer_detail')
    def empty_frontier(detail):
        return detail is None or (isinstance(detail,dict)
            and field(detail,'rating') in (None,'')
            and field(detail,'layer_challenge_info_list') in (None,[])
            and field(detail,'challenge_time') in (None,0,''))
    start,end=period(record)
    brief=field(o,'brief')
    if (field(o,'pass_fifth_floor') is False and (brief is None or isinstance(brief,dict))
            and empty_frontier(fourth_detail)
            and empty_frontier(fifth_detail) and field(o,'brief.rating') in (None,'')
            and field(o,'brief.score') in (None,0,'0')
            and start is not None and end is not None and end>start):
        return 0,4,True,'해당 회차 미도전',False
    if field(o,'has_data') is False:return unknown
    fourth=grade(field(o,'fourth_layer_detail'))
    if fourth not in known and fourth not in (None,''):return unknown
    rooms=field(o,'fitfh_layer_detail.layer_challenge_info_list','fifth_layer_detail.layer_challenge_info_list')
    if rooms is None:rooms=[]
    if not isinstance(rooms,list) or len(rooms)>3 or not distinct(rooms):return unknown
    grades=[grade(row) for row in rooms]
    if any(not isinstance(row,dict) for row in rooms):return unknown
    if any(v not in known and v not in (None,'') for v in grades):return unknown
    if fourth not in known and not any(v in known for v in grades):return unknown
    count=int(fourth=='S')+grades.count('S')
    verified=(fourth in known and len(grades)==3 and all(v in known for v in grades)
              and field(o,'pass_fifth_floor') is True)
    detail=f"확인된 S · 제4전선 {fourth or '미확인'} · 제5전선 S {grades.count('S')}/3"
    if not verified:detail+=' · 일부 기록/통과 미확인, 자동 완료 보류'
    return count,4,verified,detail,True


def shiyu_diagnostic(payload):
    """Only allowlisted schema states; never echo unknown field values/identifiers."""
    version,o=_shiyu_record(choose_record(payload,'shiyu'))
    version=version if version in ('v1','v2') else '미확인'
    fourth=field(o,'fourth_layer_detail.rating')
    rank=fourth if fourth in ('S','A','B') else '없음/미확인'
    rooms=field(o,'fitfh_layer_detail.layer_challenge_info_list','fifth_layer_detail.layer_challenge_info_list')
    n=str(len(rooms)) if isinstance(rooms,list) and len(rooms)<=3 else '없음/미확인'
    return f'응답 성공·S 등급 기록 확인 필요 ({version}, 제4전선 {rank}, 제5전선 방 {n})'


def parse(mode, payload):
    record=choose_record(payload,mode)
    if mode=='arbitration':record=_peak(record)
    if not record:return None
    if field(record,'has_data') is False and mode not in ('deadly','shiyu'):return None
    value=None;maximum=TARGETS.get(mode);basis='';verified=True;has_record=True
    if mode=='theater':value,basis=_stella(record)
    elif mode=='deadly':value,basis=_deadly(record)
    elif mode=='shiyu':
        value,maximum,verified,basis,has_record=_shiyu(record)
    elif mode=='spiral':
        value=integer(record,'total_star','total_stars')
        basis='API total stars'
        if value is None:
            rows=field(record,'floors')
            if isinstance(rows,list):
                totals={integer(x,'index','floor'):integer(x,'star','stars') for x in rows if isinstance(x,dict)}
                if all(type(totals.get(i)) is int for i in (9,10,11,12)):
                    value=sum(totals[i] for i in (9,10,11,12))
    elif mode=='arbitration':
        mobs=integer(record,'mob_stars','summary.mini_boss_stars')
        boss=integer(record,'boss_stars','summary.boss_stars')
        if mobs is not None and boss is not None and 0<=mobs<=9 and 0<=boss<=3:
            value=mobs+boss;maximum=12;basis='one arbitration season 9 mobs + 3 boss'
    else:
        value=integer(record,'total_star','total_stars','star_num','total_star_num','stat.total_star','basic.total_star')
        basis='API total stars'
    if type(value) is not int or type(maximum) is not int or value<0 or maximum<=0 or value>500:return None
    explicit_max=integer(record,'max_star_num','max_stars','max_star','total_max_stars','max_star_count')
    if mode != 'shiyu' and explicit_max is not None and explicit_max > maximum and explicit_max <= 500:
        maximum=explicit_max
    start,end=period(record)
    if mode=='arbitration' and (start is None or end is None):
        start,end=period(field(record,'group') or {})
    if start is None or end is None:
        start,end=period(payload)
    if (start is None or end is None) and mode in ('moc','pure_fiction','apocalyptic'):
        start,end=_period_from_groups(record)
    if (start is None or end is None) and isinstance(field(payload,'seasons'),list):
        # Seasons list can describe the current active window, but only if unambiguous.
        active=[x for x in payload['seasons'] if isinstance(x,dict) and integer(x,'status')==1]
        if len(active)==1:start,end=period(active[0])
    if start is None or end is None or end<=start:start,end=None,None
    detail=score_detail(mode,payload)
    if mode=='shiyu':detail=basis+(' · '+detail if detail else '')
    return EndgameProgress(mode,value,maximum,start,end,basis,detail,verified,has_record)

async def fetch(client, uid, game):
    """Reuse existing genshin.Client cookie and DS/auth refresh logic. No Todoist mutation."""
    results={};errors={}
    for mode,method in METHODS.get(game,{}).items():
        candidate=getattr(client,method,None)
        if not callable(candidate):
            errors[mode]='설치된 genshin.py에 해당 조회 기능 없음';continue
        try:
            args={'raw':True}
            if mode=='arbitration':args['schedule_type']=3
            payload=await candidate(int(uid),**args)
            parsed=parse(mode,payload)
            if parsed is None:
                errors[mode]=shiyu_diagnostic(payload) if mode=='shiyu' else '응답 성공·보상 점수/별 데이터 해석 불가'
            else:
                if mode=='deadly':
                    from dataclasses import replace
                    info=deadly_detail(payload)
                    b=info.get('normal_bosses',[])
                    h=info.get('adversity_bosses',[])
                    fmt=lambda vals: ', '.join(f"{v.get('score','?')}점/{v.get('stars','?')}별" for v in vals) or '기록 없음'
                    parsed=replace(parsed,basis=(parsed.basis + '; 일반 ' + fmt(b) +
                        '; 절망(추가 보상) ' + fmt(h)))
                results[mode]=parsed
        except Exception as exc:
            errors[mode]='조회 실패: '+type(exc).__name__
    return results,errors


def deadly_detail(payload):
    """Display-only normal/adversity summary, never used to close Todoist tasks."""
    obj=choose_record(payload,'deadly')
    if not isinstance(obj,dict):return {'state':'unverified'}
    start,end=period(obj)
    if start is None or end is None or end<=start:return {'state':'unverified'}
    def rows(name):
        a=obj.get(name)
        return ([{'score':integer(v,'score'),'stars':integer(v,'star','total_star')}
                 for v in a if isinstance(v,dict)] if isinstance(a,list) else [])
    n=rows('list');h=rows('hard_list')
    return {'state':'not_attempted' if obj.get('has_data') is False and not n and not h else 'recorded',
            'normal_stars':integer(obj,'total_star') or 0,
            'normal_score':integer(obj,'total_score') or 0,
            'normal_bosses':n, 'adversity_bosses':h,
            'adversity_optional':True, 'season_start':start,'season_end':end}


def score_detail(mode,payload):
    """Read-only point details; never used as evidence of S grades or completion."""
    record=choose_record(payload,mode)
    if mode=='shiyu':
        record=field(record,'hadal_info_v2','hadal_info_v1') or record
        rooms=field(record,'fitfh_layer_detail.layer_challenge_info_list','fifth_layer_detail.layer_challenge_info_list')
        if not isinstance(rooms,list):return ''
        return ' · '.join(f"{i+1}번 방 {integer(room,'score'):,}점" for i,room in enumerate(rooms)
                          if integer(room,'score') is not None and integer(room,'score')>=0)
    if mode=='deadly':
        pieces=[]
        for key,title in [('list','일반'),('hard_list','절망')]:
            rows=field(record,key)
            if not isinstance(rows,list):continue
            values=[f"{i+1}번 {integer(row,'score'):,}점" for i,row in enumerate(rows)
                    if integer(row,'score') is not None and integer(row,'score')>=0]
            if values:pieces.append(title+' '+', '.join(values))
        return ' · '.join(pieces)
    return ''
