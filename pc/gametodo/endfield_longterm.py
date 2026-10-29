"""Strict parsing of optional Endfield global response candidates.

Only verified response fields are used. These models do not establish live Asia API support.
"""
import time
from .live_data import Gauge,field_at,number
from .endgame_records import date_value


def body(payload):
    if not isinstance(payload,dict):return None
    for key in ('code','status'):
        if key in payload and not ((type(payload[key]) is int and payload[key]==0) or payload[key]=='0'):return None
    return payload.get('data',payload)


def umbral_goal(detail,now_seconds=None):
    now=time.time() if now_seconds is None else now_seconds
    groups=field_at(detail,'indieHard.indieHardGroups')
    if not isinstance(groups,list):return None
    candidates=[]
    for group in groups:
        if not isinstance(group,dict):continue
        begin=date_value(group.get('activityStartTs'))
        if begin is not None and begin<=now:candidates.append((begin,group))
    if not candidates:return None
    latest=max(begin for begin,_ in candidates);flags=[]
    for begin,group in candidates:
        if begin!=latest:continue
        rows=group.get('dungeonGroups')
        if not isinstance(rows,list) or not rows:return None
        for row in rows:
            for name in ('normalDungeon','hardDungeon'):
                value=field_at(row,name+'.isPass')
                if type(value) is not bool:return None
                flags.append(value)
    if not flags:return None
    # activityEndTs is the limited bonus window, not the permanent challenge's end.
    return Gauge(sum(flags),len(flags)),(latest,None)


def crisis_progress(payload,now_seconds=None):
    now=time.time() if now_seconds is None else now_seconds
    root=body(payload)
    contract=root.get('crisisContract') if isinstance(root,dict) else None
    if not isinstance(contract,dict):return None
    status=contract.get('status')
    if not isinstance(status,dict) or str(status.get('id') or '').strip() in ('','0','null'):return None
    begin=date_value(status.get('startAtTs'));end=date_value(status.get('endAtTs'))
    if begin is None or end is None or begin>=end:return None
    gameplay_end=date_value(status.get('gameplayEndAtTs'))
    if gameplay_end is not None:
        if not begin<gameplay_end<=end:return None
        end=gameplay_end
    metrics={};checks=[]
    for key in ('weeklyMission','indicatorMission','stageMission'):
        cur=number(status,key+'.count');total=number(status,key+'.total')
        valid=cur is not None and total is not None and total>0
        checks.append(valid and cur>=total)
        if valid:metrics['crisis_'+key]=Gauge(cur,total)
    plated=field_at(status,'achieve.isPlated')
    # All three counters AND explicit plated medal; missing reward evidence never implies completion.
    goals=all(checks) and plated is True
    ready=now>=end or (now>=begin and goals)
    metrics['crisis_complete']=Gauge(int(ready),1)
    minimal={'crisisContract':{'status':{'id':str(status['id']),'startAtTs':begin,'endAtTs':end}}}
    return metrics,(begin,end),minimal,goals


def war_progress(payload,now_seconds=None):
    now=time.time() if now_seconds is None else now_seconds
    root=body(payload)
    seasons=field_at(root,'warEchoes.seasons')
    if not isinstance(seasons,list):return None
    active=[]
    for season in seasons:
        weeks=season.get('weeks') if isinstance(season,dict) else None
        if not isinstance(weeks,list):continue
        for week in weeks:
            if not isinstance(week,dict):continue
            begin=date_value(week.get('startTs'));end=date_value(week.get('endTs'))
            if begin is not None and end is not None and begin<=now<end:active.append((week,begin,end))
    if len(active)!=1:return None
    week,begin,end=active[0];rows=week.get('dungeonGroups')
    if not isinstance(rows,list) or not rows:return None
    metrics={};flags=[]
    for field in ('normalDungeon','hardDungeon','cruelDungeon'):
        values=[field_at(row,field+'.isPass') for row in rows]
        if all(type(value) is bool for value in values):metrics['war_'+field]=Gauge(sum(values),len(values));flags+=values
        else:flags.append(False)
    plus=week.get('allPlusTasks')
    flags.append(plus is True)
    metrics['war_complete']=Gauge(sum(flags),len(flags))
    return metrics,(begin,end),number(week,'stars'),plus
