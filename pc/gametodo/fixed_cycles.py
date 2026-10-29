"""User-fixed Todoist recurrence plus verified API windows; no recurrence mutation."""
from datetime import datetime,timedelta
import re
from .cycles import KST,due_date_kst


def fixed_occurrence(task,days,window,now,mode='goal'):
    if mode not in ('goal','goal_or_expiry','series_goal'):return None
    if type(days) is not int or not 1<=days<=366:return None
    due=task.get('due') or {}
    if due.get('is_recurring',due.get('recurring')) is not True:return None
    raw=str(due.get('string') or '').lower().strip().replace('every!','every')
    if re.match(r'^(?:weekly|every\s+(?:week|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|매주)',raw):
        actual=7
    else:actual=None
    raw=re.sub(r'^(?:every|매)\s*','',raw)
    rule=re.match(r'^(\d{1,3})\s*(weeks?|days?|주|일)(?:\b|(?=마다|간격|에)|$)',raw)
    if rule:actual=int(rule.group(1))*(7 if rule.group(2) in ('week','weeks','주') else 1)
    if actual!=days:return None
    start=due_date_kst(task)
    if start is None:return None
    today=now.astimezone(KST).date()
    if not start<=today<start+timedelta(days=days):return None
    if not isinstance(window,(tuple,list)) or len(window)!=2:return None
    begin,end=window
    if type(begin) is not int or not 1_500_000_000<=begin<=5_000_000_000:return None
    if mode!='series_goal' and (type(end) is not int or not begin<end<=5_000_000_000):return None
    a=datetime.combine(start,datetime.min.time(),KST).timestamp()
    b=datetime.combine(start+timedelta(days=days),datetime.min.time(),KST).timestamp()
    if not a<=begin<b or (mode!="series_goal" and not end>a):return None
    stamp=now.timestamp()
    if mode=='series_goal':return f'interval:{days}:series:{begin}' if stamp>=begin+1200 else None
    if mode=='goal' and not begin+1200<=stamp<end:return None
    if mode=='goal_or_expiry' and stamp<begin+1200:return None
    return f'interval:{days}:{begin}:{end}'
