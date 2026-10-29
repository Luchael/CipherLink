"""Current-user Windows autorun registration with observable status."""
from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import shlex
import ntpath
import re
import sys

RUN=r'Software\Microsoft\Windows\CurrentVersion\Run'
APPROVED=r'Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run'
NAME='CipherLink'

@dataclass(frozen=True)
class StartupState:
    registered: bool | None
    current: bool
    blocked: bool
    message: str


def command(executable=None,frozen=None):
    exe=Path(executable or sys.executable)
    frozen=getattr(sys,'frozen',False) if frozen is None else frozen
    args=[str(exe)] if frozen else [str(exe.with_name('pythonw.exe')),str(Path(__file__).resolve().parents[1]/'gametodo_desktop.py')]
    return subprocess.list2cmdline(args)


def _registry(registry=None):
    if registry is not None:return registry
    if os.name!='nt':return None
    import winreg
    return winreg


def _parts(value):
    try:return [item.strip('"') for item in shlex.split(str(value),posix=False)]
    except ValueError:return []


def _owned(value):
    parts=_parts(value)
    if not parts:return False
    first=ntpath.basename(parts[0]).casefold()
    return bool(re.fullmatch(r'(?:cipherlink(?:-\d+\.\d+\.\d+)?|questlink)\.exe',first)) or (first in ('python.exe','pythonw.exe') and len(parts)>1 and ntpath.basename(parts[1]).casefold()=='gametodo_desktop.py')


def _same(one,two):
    return [ntpath.normcase(ntpath.normpath(x)) for x in _parts(one)]==[ntpath.normcase(ntpath.normpath(x)) for x in _parts(two)]


def state(registry=None,expected=None):
    reg=_registry(registry)
    if reg is None:return StartupState(None,False,False,'Windows에서 확인할 수 있습니다')
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER,RUN) as key:
            value_name=NAME
            try:value,_=reg.QueryValueEx(key,NAME)
            except FileNotFoundError:
                try:
                    value,_=reg.QueryValueEx(key,'GameTodo');value_name='GameTodo'
                except FileNotFoundError:return StartupState(False,False,False,'등록 안 됨')
                if not _owned(value):return StartupState(False,False,False,'등록 안 됨')
    except FileNotFoundError:return StartupState(False,False,False,'등록 안 됨')
    except OSError:return StartupState(None,False,False,'시작 프로그램 상태를 확인하지 못했어요')
    current=_same(value,expected or command())
    blocked=False
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER,APPROVED) as key:
            approved,_=reg.QueryValueEx(key,value_name)
            blocked=isinstance(approved,bytes) and len(approved)>=4 and int.from_bytes(approved[:4],'little') in (3,7)
    except OSError:pass
    label='등록됨 · Windows에서 사용 안 함' if blocked else '등록됨 · 현재 앱 자동 실행' if current else '다른 버전의 실행 경로가 등록됨'
    return StartupState(True,current,blocked,label)


def enable(registry=None,expected=None):
    reg=_registry(registry)
    if reg is None:return state()
    with reg.CreateKeyEx(reg.HKEY_CURRENT_USER,RUN,0,reg.KEY_SET_VALUE|reg.KEY_QUERY_VALUE) as key:
        try:old,_=reg.QueryValueEx(key,NAME)
        except FileNotFoundError:old=None
        if old is not None and not _owned(old):raise OSError('같은 이름의 다른 시작 항목이 있습니다')
        reg.SetValueEx(key,NAME,0,reg.REG_SZ,expected or command())
        try:
            legacy,_=reg.QueryValueEx(key,'GameTodo')
            if _owned(legacy):reg.DeleteValue(key,'GameTodo')
        except FileNotFoundError:pass
    return state(reg,expected)


def disable(registry=None):
    reg=_registry(registry)
    if reg is None:return state()
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER,RUN,0,reg.KEY_SET_VALUE|reg.KEY_QUERY_VALUE) as key:
            for name in (NAME,'GameTodo'):
                try:value,_=reg.QueryValueEx(key,name)
                except FileNotFoundError:continue
                if _owned(value):reg.DeleteValue(key,name)
    except FileNotFoundError:pass
    return state(reg)
