# 사이퍼링크(CipherLink) PC v0.10.4 — 이름·아이콘 통일

기존 CipherLink PC v0.10.3 소스를 바탕으로 **브랜딩만 변경**한 업데이트입니다.

## 적용

- 데스크톱 메인 창과 계정 선택·Todoist 섹션 선택 대화상자 제목을 **사이퍼링크**로 통일했습니다.
- Windows EXE 생성 이름을 `CipherLink.exe`로 변경했습니다.
- 모바일 Android v0.10.3의 실제 `@mipmap/ic_launcher` 이미지를 PNG로 복사하고, 같은 그림으로 Windows 다중 해상도 ICO를 생성했습니다.
- 일반 실행 창·작업 표시줄·EXE 파일 모두 같은 그림을 사용하도록 코드/빌드 설정을 변경했습니다.
- Windows 로그인 시 자동 시작 레지스트리 값은 `CipherLink`로 등록합니다. 이전 버전의 `GameTodo` 값은 실제 이 프로그램으로 확인되는 경우에만 정리하므로 중복 실행을 줄입니다.
- 앞으로 처음 연결하는 Todoist OAuth 클라이언트의 표시 이름은 `CipherLink`입니다. 기존 연결의 토큰은 보존하며 자동으로 다시 로그인하지 않습니다.

## 기존 데이터·호환성 유지

`gametodo` Python 모듈 이름, `~/.gametodo` 자격 증명과 설정 경로, 기존 `GameTodo-ID`/`GameTodo-Banner-ID` 표식, Todoist 작업 연결 규칙 및 고유 UUID 등은 **변경하지 않았습니다**. 이 값들을 바꾸면 기존 동기화가 중복되거나 로그인 정보가 사라질 수 있습니다.

## Windows 소스 실행

기존 PC 폴더에 소스 ZIP을 덮어쓰고 `run_windows.bat`를 실행합니다. 소스 실행 시에도 창 제목·아이콘이 반영됩니다.

## 배포 EXE 제작 (빌드하는 사람의 Windows PC에서 1회)

`pc/build_windows.bat`를 실행하면 `pc/dist/CipherLink.exe` 생성이 시도됩니다. `--onefile --windowed --icon` 및 앱 PNG 파일 포함으로, 사용자에게 별도 아이콘 파일 복사를 요구하지 않습니다.

> 현재 이 환경에서는 **Windows EXE를 실제로 빌드·실행 검증하지 못했습니다.** 배포 PC에서 PyInstaller 의존성까지 설치해 빌드해야 합니다. 이번 ZIP은 소스이며 EXE는 아닙니다.

최종 배포에서는 Python 및 pip 의존성을 제작자가 EXE에 포함하고, 사용자는 `CipherLink.exe`를 실행한 다음 최초 계정 로그인만 수행하도록 구성할 수 있습니다.
