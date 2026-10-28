"""사이퍼링크 PC 표시 이름 및 모바일 공통 앱 아이콘.

기존 계정/설정/작업 ID 저장 위치(`~/.gametodo`)는 변경하지 않는다.
Windows EXE 내에서도 PyInstaller의 assets/ 리소스를 우선 찾는다.
"""
import os
from pathlib import Path
import sys
import tkinter as tk

APP_NAME = "사이퍼링크"
EXE_NAME = "CipherLink"
WINDOW_TITLE = f"{APP_NAME} • 게임 체크리스트 자동화"


def icon_resource(name):
    """소스 실행과 PyInstaller --onefile 양쪽에서 아이콘 위치 검색."""
    roots = []
    frozen_root = getattr(sys, '_MEIPASS', None)
    if frozen_root:
        roots.append(Path(frozen_root))
    roots.append(Path(__file__).resolve().parents[1])
    for root in roots:
        path = root / 'assets' / name
        if path.is_file():
            return path
    return None


def apply_window_icon(root):
    """Tk 창/작업 표시줄에 모바일과 동일한 런처 그림을 설정한다.

    윈도우 아이콘을 읽지 못해도 게임 조회/로그인 기능은 계속 실행한다.
    """
    if os.name == 'nt':
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('CipherLink.Desktop')
        except (AttributeError, OSError):
            pass
        ico = icon_resource('cipherlink.ico')
        if ico:
            try:
                root.iconbitmap(default=str(ico))
            except (tk.TclError, OSError):
                pass
    png = icon_resource('cipherlink.png')
    if png:
        try:
            image = tk.PhotoImage(master=root, file=str(png))
            root.iconphoto(True, image)
            return image  # 참조를 유지해야 일부 Tk 버전에서 그림이 유지됨
        except (tk.TclError, OSError):
            pass
    return None
