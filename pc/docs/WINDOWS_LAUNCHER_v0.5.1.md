# Windows 실행 파일 수정 (v0.5.1)

- `run_windows.bat`을 한국어 CMD용 **CP949(Windows-949), CRLF, BOM 없음**으로 저장했습니다.
- 코드 페이지 변경을 `chcp 949 >nul`로 바꿨습니다.
- Python 런처 `py -3`를 사용하지 않고 `python`으로 실행합니다.
- Python 3.10 이상인지 확인하고, 발견하지 못하면 안내 메시지를 출력합니다.
- `README.md` 및 과거 문서의 Windows 명령어도 `python -m ...`으로 통일했습니다.
- 프로그램 내부 Python 코드/완료 판정/설정/SQLite는 변경하지 않았습니다.

## 실행

```bat
python --version
python -m gametodo schedule-status
run_windows.bat
```

토큰 최초 설정은 프로젝트 폴더의 CMD에서 아래를 실행하세요.

```bat
python -m gametodo auth todoist
```

**주의:** CP949는 `.bat` 실행 파일에만 적용합니다. `.py`와 `.json` 파일은 UTF-8을 유지해야 합니다.
