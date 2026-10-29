# 사이퍼링크 · CipherLink

게임 진행도와 할 일을 Todoist에 연결하는 Windows·Android 앱입니다. 한국어와 한국 시간(KST)을 사용하며, PC가 꺼져 있어도 Android에서 독립적으로 동기화합니다.

## 주요 기능

- 연결한 게임 계정의 일일·주간·회차별 진행도 조회
- 현재 회차의 목표를 충족하면 Todoist 작업 완료 및 모바일 알림
- 게임 화면의 사이퍼링크 플로팅 버튼으로 할 일 확인·수동 체크
- 설치 앱 검색과 Todoist 라벨을 이용한 게임 연결
- 출처와 기간을 확인한 캐릭터 가챠 일정 수집, 게임 라벨과 `가챠` 라벨 적용

자동 진행도 연동은 원신·스타레일·젠레스 존 제로·엔드필드를 중심으로 구현되어 있습니다. API가 확인되지 않은 게임은 수동 체크를 사용합니다. 명일방주 자동 조회는 사용자가 허용한 PC 23:59 1회 정책을 따릅니다.

## 설치와 업데이트

설치 파일은 이 대화에서 제공하는 EXE·APK를 사용하세요. 현재 GitHub 최신 릴리스 다운로드는 제공하지 않습니다.

- **Windows:** EXE를 실행합니다. 사용자 PC에 Python을 설치할 필요가 없습니다. 업데이트는 앱을 종료하고 EXE를 교체합니다.
- **Android:** 기존 앱을 삭제하지 않고 APK를 열어 업데이트합니다. 설치에 성공한 기존 앱과 같은 패키지·서명을 유지해야 합니다.
- 업데이트할 때 설정과 데이터 폴더를 삭제하지 마세요. 비밀번호·쿠키·토큰을 다른 사람에게 전달하지 마세요.

## 개발

현재 소스 버전: **PC·Android 0.11.6**.

```bash
cd pc
python -m pip install -r requirements-login.txt -r requirements-endgame.txt
python -m unittest discover -s tests -q
python -m gametodo gui
```

Android는 `android/`를 Android Studio에서 열어 빌드합니다. JDK 17과 Android SDK 35를 사용합니다. [프로젝트 시작 안내](CODEX_START_HERE.md)와 [개발 지침](AGENTS.md)을 참고하세요.

## 검증 범위

회귀 테스트와 빌드 성공은 실제 계정 로그인·게임 API·Windows 실행·Android 설치 검증을 대신하지 않습니다. 확인하지 못한 기록을 0점이나 완료로 간주하지 않습니다.

[진행도·가챠 수정 내역](docs/PROGRESS_0115.md) · [제품·Todoist 기준](docs/PRODUCT_AND_TODOIST.md)
