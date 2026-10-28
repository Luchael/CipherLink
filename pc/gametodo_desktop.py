"""PyInstaller용 데스크톱 실행 엔트리. 콘솔 창 없이 GUI 실행."""
from gametodo.gui import start_gui

if __name__ == "__main__":
    start_gui()
