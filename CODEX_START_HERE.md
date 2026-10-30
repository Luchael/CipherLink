# Codex: 이 파일부터 읽으세요

> **현재 개발 상태:** PC·Android **0.11.9**, 새 Android 정식 설치 계열 `com.gametodo.cipherlink`. [자동 배포](docs/AUTOMATIC_RELEASES.md), [0.11.9 변경](docs/releases/v0.11.9.md)을 먼저 읽으세요. PC 296개·Kotlin 28개 통과, 기존 초기화·플로팅 개선 유지. 새 고정 서명키와 GitHub Secrets로 자동 서명·배포 CI가 성공했고 Windows·APK 모두 0.11.9 정식 게시 및 README 상단 링크 갱신을 확인했습니다. 기존 Android 앱/데이터를 지우지 않으며 첫 설치 후 계정·권한을 다시 연결해야 합니다. 한국 서버 우선, 없으면 글로벌 Asia, 한국어/KST, 모바일 주 실행 정책을 유지합니다. 아래 구 기준선은 원본 ZIP 인수 당시 기록입니다.

## 프로젝트 미션

**사이퍼링크(CipherLink)**: Windows PC와 Android 각각 독립 실행되며 동일한 Todoist 계정에 연결하는 다중 게임 할 일/계정 데이터 자동 완료 앱. 게임 계정의 **읽기 전용** 진행도를 확인하여 Todoist의 일간/주간/월간/N일 주기 작업을 정확한 회차에만 자동 완료한다. 가챠 일정은 신뢰 가능한 **해당 서버** 출처만 사용한다.

### 현재 기준선 (중요)

| 구성 요소 | 포함된 실제 버전 | 검증 상황 |
| --- | --- | --- |
| PC | `pc/` v0.10.5 (Python/Tkinter) | `python -m unittest discover -s tests -q` **168/168 통과**(2026-10-28 인수인계 환경에서 재검증) |
| Android | `android/` v0.10.3 (Kotlin) | 기존 단위 컴파일/회귀 테스트 기록은 있으나 전체 APK 빌드/실계정 검증 **미완료** |
| 연동 스키마 | `pc/todoist_bindings.json` 및 `android/app/src/main/assets/todoist_bindings.json` | 실사용 Todoist 작업 제목 34개(자동·조건부·수동 분류) |
| UI | PC 최신 사이드바 대시보드, 계정 연결/동기화/설정/진단 페이지 | `reference_ui/`에 현재 예시 화면 2장 |
| 브랜딩 | **사이퍼링크**, `CipherLink.exe`, Android 런처와 같은 아이콘 | 기존 내부 호환 키는 유지 |

## 소스가 들어 있는 위치

- Windows 시작: `pc/run_windows.bat` → `python -m gametodo gui`. 구현: `pc/gametodo/gui.py`, `pc/gametodo/cli.py`, `pc/gametodo/embedded_login.py`.
- HoYoLAB: `pc/gametodo/hoyolab.py`, `hoyolab_login.py`, `embedded_login.py`, `account_setup.py`.
- 엔드필드/GRYPHLINE: `pc/gametodo/skport.py`, `account_setup.py`, `embedded_login.py`.
- 게임 진행도: `pc/gametodo/live_data.py`, `endgame_records.py`, `endgame_goals.py`, `account_watch.py`.
- Todoist: `pc/gametodo/task_rules.py`, `todoist.py`, `todoist_bindings.json`, `cycles.py`.
- 가챠: `pc/gametodo/banners.py`, `pickupcal.py`, `banner_sync.py`.
- 모바일 로그인/계정: `android/app/src/main/java/com/gametodo/nativeapp/{GameAccountLoginActivity,AccountProviders,AccountSync,EndgameRecords,RealTimeMemo}.kt`.
- 모바일 예약/플로팅: `SyncWorker.kt`, `GameDetectionService.kt`, `FloatingOverlay.kt`, `OverlayTaskPolicy.kt`, `AutoCheckIntervals.kt`.
- 명일방주 PC 제한적 예약: `pc/gametodo/nightly_arknights.py`, `arknights.py`.
- 비식별 진단: `pc/gametodo/safe_diagnostic.py` / Android `SafeApiDiagnostics.kt`.

## 사용자가 가장 최근에 겪는 미해결 문제 — 우선순위

1. **PC HoYoLAB 로그인 후 UID 조회 실패**: 공식 페이지 로그인 자체는 성공. 3/4 계정 검증에서 실패. v0.10.5에서 쿠키 준비 및 글로벌 UID 대체 경로를 수정했으나 **실계정 재검증 전**. 실제 오류의 정확한 예외·HTTP/retcode만 비식별 진단해 재현/수정할 것.
2. **PC 엔드필드 로그인 후 GRYPHLINE 단계 실패**: 공식 로그인 자체 성공, 3/5 토큰 검증 실패. v0.10.5가 기본정보 API 다양한 스키마 허용 및 OAuth/캐릭터 바인딩 재검증을 추가했지만 **실계정 재검증 전**.
3. **명조 글로벌 가챠 수집 미지원**: 기존 일반 `ValueError` 오류의 실질 원인은 검증된 글로벌 Asia 배너 일정 출처 부재로 인한 의도적 차단. v0.10.5에서는 오류를 분리 표시하지만 **수집 성공으로 수정된 것이 아님**. 서버 일치·시작/종료 날짜 검증 없이 한국 서버/중국 서버 일정 혼용 금지.
4. **최종 Windows 설치판**: 사용자에게 Python/pip/명령어/외부 장비/수동 라이브러리 설치를 요구하지 않는 EXE/설치 프로그램 제공. 현재 `pc/build_windows.bat`에 PyInstaller 설정은 있으나 **Windows 실제 빌드 및 설치 테스트는 미완료**.
5. UI/UX: PC GUI 가독성·일관성·계정 오류 재시도 경험 개선. 기존 사이드바 UI와 모바일 아이콘을 유지하면서 발전시킬 것.

자세한 재현/목표는 [`docs/OPEN_ISSUES.md`](docs/OPEN_ISSUES.md).

## 절대 보존해야 할 제약

- Windows·Android가 **같은 Todoist 계정**을 사용해도 중복 완료/중복 가챠 등록하면 안 됨.
- 원래 Todoist 작업 제목·날짜·반복·하위 작업을 멋대로 변경하거나 삭제하면 안 됨.
- 일/주/월/N일 회차, KST/게임별 서버 초기화 시간 준수. 이미 지난 **미완료 회차는 플로팅에서 보이되**, 새 회차 API로 이전 회차를 **잘못 자동 완료하지 않음**.
- 현재 회차 기록이 확인되지 않으면 자동 완료 보류. 일부 기록 0점/미도전은 **API 실패가 아님**.
- 실계정 비밀번호·세션 쿠키·토큰을 출력/전송/디버그 로그에 남기지 않음. DS 서명·쿠키 등 인증 보안 우회 금지.
- 게임 플레이 방해 최소화(읽기 전용 API). 명일방주만 예외적으로 **사용자가 명시적으로 허용한 PC 23:59 KST 하루 1회** 조회가 가능하지만 게임 강제 로그아웃 위험이 있음.
- 브랜드 이름은 **사이퍼링크**, 아이콘은 PC `pc/assets/cipherlink.ico`와 Android 런처를 일치시킴. 호환을 위해 Python 모듈명 `gametodo`, Android `applicationId=com.gametodo.nativeapp`, `~/.gametodo`, Todoist UUID/표식은 유지.

## Codex 첫 작업 권장 순서

1. 현재 프로젝트를 검사하고 테스트 재실행, 실제 실패하는 경로/예외 분류. 가설을 사실처럼 확정하지 않는다.
2. 토큰을 노출하지 않는 요청/응답 상태 진단 추가(HTTP status/retcode/필드 스키마만). 인증 재시도 안전성, 브라우저 쿠키 로딩 타이밍, OAuth 흐름에 대한 모의 테스트 작성.
3. PC HoYoLAB 및 엔드필드 로그인 문제의 가능한 원인을 코드·공개 API 구현과 대조한 뒤 최소 패치. 실제 계정 검증이 필요하면 사용자 로컬에서 실행할 **안전한 검증 절차** 제공.
4. 명조 글로벌 가챠의 신뢰 가능한 공개 일정 소스를 검증; 없으면 사용자 설정/오류 안내를 개선하되 무단 자동 등록은 계속 보류.
5. Windows 패키징/GUI 사용성 개선. 회귀 테스트와 변경 이력, 재현 방법을 남김.

**이 패키지를 받은 이유는 이미 개발된 앱을 이어서 완성하는 것이지 새 프로젝트를 처음부터 재작성하는 것이 아니다.**
