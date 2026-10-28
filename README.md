# CipherLink (사이퍼링크) — Codex 인수인계 패키지

> 기준일: 2026-10-28 · 실제 소스 포함 · 개발 PC: **v0.11.0** / Android: **v0.11.1**

**Codex는 먼저 [`CODEX_START_HERE.md`](CODEX_START_HERE.md) → [`AGENTS.md`](AGENTS.md) → [`docs/OPEN_ISSUES.md`](docs/OPEN_ISSUES.md)를 읽을 것.**

## 포함된 파일

- `pc/`: Python/Tkinter Windows 앱 **v0.11.0** 전체 소스, 자동 테스트, EXE 빌드 배치 파일, 앱 아이콘.
- `android/`: Kotlin Android 네이티브 앱 **v0.11.1** 전체 소스(동기화, API, 플로팅, 계정, 게임별 조회).
- `tests/`: Android 측 순수 Kotlin 검증 코드.
- `reference_ui/`: 현재 PC GUI 캡처 2장(인수인계 참고용, 실제 UI 아님).
- `docs/`: 기능 요구사항, 최근 오류, 보안 규칙, 점수·회차 처리, 실행·배포 및 버전 이력.
- `CODEX_TASK_PROMPT.md`: Codex 새 대화에 붙여넣을 시작 지시문.

## 중요

- 이 ZIP에는 **사용자의 비밀번호, 쿠키, OAuth 토큰, 기존 `config.json`, DB, 개인 API 응답 원본이 포함되지 않습니다.** 민감 정보는 Codex에도 업로드하지 마세요.
- 이는 **소스 인수인계**입니다. 로그인 성공/Windows EXE 배포/Android APK 빌드가 실계정과 실기기에서 검증됐다는 뜻이 아닙니다.
- 과거 README/CHANGELOG의 오래된 제품 이름 또는 목표가 남아 있을 수 있습니다. 현재 기준은 본 인수인계 문서와 최신 소스 코드입니다.

## 즉시 실행 (개발자 PC)

```powershell
cd pc
python -m unittest discover -s tests -q
python -m gametodo gui
```

선택적 계정 로그인 기능을 개발자 환경에서 설치하려면 `python -m pip install -r requirements-login.txt`. 일반 사용자 배포판에는 Python/pip 설치를 요구하지 않는 것이 목표입니다.

Android: Android Studio에서 `android/` 열기, JDK17 / SDK35, 또는 기존 Termux `studio build android :app:assembleDebug` 환경. 전체 APK 빌드는 인수인계 시점에 검증되지 않았습니다.

## 개발 재개 결과

원본 인수 버전과 변경·검증 내역은 [2026-10-28 조사 기록](docs/INVESTIGATION_2026-10-28.md)을 참고하세요. [Windows EXE 수동 빌드](docs/WINDOWS_DISTRIBUTION.md)와 [명조 출처 상태](docs/WUTHERING_SOURCE_STATUS.md)는 실환경 검증 상태를 구분합니다. 로그인 실계정 성공 및 Windows EXE·Android 실기기 동작은 아직 미검증입니다.

최신 추가: [스텔라 KR 가챠 연결](docs/STELLA_KR_BANNERS.md), [즉시 완료·성공 알림·별도 설치 테스트판](docs/ANDROID_TEMP_0105.md).

[0.11.0 연결·설정·진행도 화면 개선](docs/UI_0110.md): 설치된 앱의 패키지와 서명을 유지하며 표시 이름을 사이퍼링크로 정리했습니다.
