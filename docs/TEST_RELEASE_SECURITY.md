# 실행·테스트·배포·보안 체크리스트

## 개발자용 Windows 실행

```powershell
cd pc
python -m unittest discover -s tests -q
python -m gametodo gui
```

- Python 3.10 이상을 사용하는 **소스판**. 계정 API 기능은 개발 환경에서 `python -m pip install -r requirements-login.txt`, 일부 엔드 전적은 `requirements-endgame.txt`. `requirements-pc.txt`는 OCR/캡처용 선택 의존성.
- `pc/run_windows.bat`: CMD CP949 인코딩 유지. `python -m gametodo gui` 시작.
- `pc/build_windows.bat`: PyInstaller `--onefile`로 `CipherLink.exe` 생성 시도. **Windows에서 빌드/설치 검증한 적 없음**. PyInstaller의 `--collect-all`로 실제 필요한 패키지/브라우저 드라이버 포함되는지 확인해야 함.
- 실행 전 현재 사용자 데이터 `~/.gametodo`, `pc/config.json`, `pc/data/` 백업. 인수인계 ZIP에는 이 자료가 없음.

## Android 개발자 빌드

- Android Studio `android/` Gradle Kotlin 프로젝트. `compileSdk/targetSdk=35`, `minSdk=30`, JDK 17, Android `applicationId=com.gametodo.nativeapp` 보존.
- 기존 사용자 Termux 환경에서 `studio build ~/projects/gametodo/android :app:assembleDebug` 사용. **일반 사용자가 Termux/Android Studio를 설치해야 한다는 의미는 아님**: 최종 배포 시 APK 직접 설치 목표.
- 기존 앱을 삭제하지 않고 동일 서명으로 업데이트해야 로그인 및 Keystore 보존 가능. 이번 ZIP에 서명 키나 완성 APK는 넣지 않음.

## 확인한 테스트 범위

- 2026-10-28 Linux/Python 환경에서 `pc/tests/` unittest **168개 통과**. `sqlite3.Connection` 미종료 `ResourceWarning` 2건은 향후 정리 권장. 의존성 없는 모의 테스트이지 실제 인증 API 성공을 증명하지 않음.
- Android 기존 Kotlin 단위/회귀 테스트 기록은 존재하지만 **이 패키징 세션에서 Gradle APK 전체 빌드/실기기 테스트는 수행하지 않음**.
- EXE 릴리스의 Windows 수동 검증(시작, 로그인, 계정 UID/캐릭터 선택, 설치/업데이트, 스마트스크린, 비관리자 권한, 네트워크 오류)은 **필수 후속 작업**.

## 최종 배포 목표

- 일반 사용자는 `CipherLink Setup.exe` 또는 `CipherLink.exe` 설치/실행 → 앱 안에서 Todoist/게임사 최초 로그인 → 사용. Python/pip/CMD 입력/라이브러리 수동 설치 요구 금지.
- 로컬 저장소 데이터 호환/업데이트 보존, 예외 로그에서 비밀정보 마스킹, 앱 기본 설정에서 자동 확인 ON/OFF와 개별 게임 조회 ON/OFF.
- 게임사 API/개인 계정 전적은 **읽기 전용**. 게임 콘텐츠 직접 조작, 자동 전투, 게임 세션 파괴 방지. 명일방주 PC 23:59 1회 opt-in은 접속 종료 가능성이 있고 모바일 구현 전.

## Git/아티팩트 배포에서 제외해야 하는 항목

- `config.json`, `.env`, `data/`, `~/.gametodo`, 데이터베이스, 로그, 쿠키/토큰, `ACCOUNT_TOKEN`, 사용자 지정 UID/계정 ID, API 인증 URL.
- Android `local.properties`, `*.jks`, `*.keystore`, 앱 패키지 서명 키.
- 실제 계정 API 진단 JSON은 **요청 시 별도 비식별 검토 후** 공유. 사용자에게 쿠키나 패스워드를 받아서 직접 재현하지 말 것.
