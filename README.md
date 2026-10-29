# 사이퍼링크 · CipherLink

게임 할 일을 Todoist와 연결하는 Windows·Android 앱입니다. 한국어와 한국 시간을 기준으로 동작합니다.

| 다운로드 | 버튼을 눌러 받으세요 |
| --- | --- |
| **Windows PC** | [**⬇ CipherLink-Windows.exe 다운로드**](https://github.com/Luchael/CipherLink/releases/latest/download/CipherLink-Windows.exe) |
| **Android 휴대폰** | [**⬇ CipherLink-Android.apk 다운로드**](https://github.com/Luchael/CipherLink/releases/latest/download/CipherLink-Android.apk) |
| **버전·변경 내용** | [**최신 버전 안내**](https://github.com/Luchael/CipherLink/releases/latest) · [이전 버전 전체 보기](https://github.com/Luchael/CipherLink/releases) |

> **비공개 배포:** GitHub에서 저장소 소유자 계정으로 로그인해야 다운로드할 수 있습니다. 링크가 열리지 않으면 먼저 [최신 버전 안내](https://github.com/Luchael/CipherLink/releases/latest)를 열고 아래 **Assets(파일)**에서 받으세요.

Windows는 EXE를 실행하면 됩니다. Python을 설치할 필요가 없습니다. Android는 APK를 열고 **업데이트**를 선택하세요. 설치에 성공한 별도 테스트 앱과 패키지·서명을 유지합니다. 원래 0.10.2 앱과는 별개입니다.

앱의 **설정 → 최신 버전 다운로드**에서도 이 페이지를 열 수 있습니다. 비공개 배포는 브라우저에서 GitHub 로그인이 필요하므로 무인 자동 설치는 제공하지 않습니다. 휴대폰 설치 승인은 Android가 직접 받습니다. 알림을 원하면 GitHub **Watch → Custom → Releases**를 선택하세요.

최신 배포에는 진행도 조회 충돌 수정, 스타레일 **18000점 + 역전의 여운 잔여 0/3** 조건, 사이퍼링크 플로팅 아이콘, 앱 검색과 Todoist 라벨로 새 게임 추가 기능이 포함됩니다. 실제 계정/API와 기기에서의 동작은 별도 검증이 필요합니다.

[배포·업데이트 방법](docs/DOWNLOAD_AND_UPDATES.md) · [버전별 변경 내용](https://github.com/Luchael/CipherLink/releases) · [Windows 실행 안내](docs/WINDOWS_DISTRIBUTION.md)

---

PC·Android 소스: **v0.11.3** · 2026-10-29 KST

개발을 이어갈 때는 [`CODEX_START_HERE.md`](CODEX_START_HERE.md) → [`AGENTS.md`](AGENTS.md) → [`docs/OPEN_ISSUES.md`](docs/OPEN_ISSUES.md)를 읽으세요.

## 포함된 파일

- `pc/`: Python/Tkinter Windows 앱 **v0.11.3** 전체 소스, 자동 테스트, EXE 빌드 배치 파일, 앱 아이콘.
- `android/`: Kotlin Android 네이티브 앱 **v0.11.3** 전체 소스(동기화, API, 플로팅, 계정, 게임별 조회).
- `tests/`: Android 측 순수 Kotlin 검증 코드.
- `reference_ui/`: 현재 PC GUI 캡처 2장(인수인계 참고용, 실제 UI 아님).
- `docs/`: 기능 요구사항, 최근 오류, 보안 규칙, 점수·회차 처리, 실행·배포 및 버전 이력.
- `CODEX_TASK_PROMPT.md`: Codex 새 대화에 붙여넣을 시작 지시문.

## 중요

- 이 ZIP에는 **사용자의 비밀번호, 쿠키, OAuth 토큰, 기존 `config.json`, DB, 개인 API 응답 원본이 포함되지 않습니다.** 민감 정보는 Codex에도 업로드하지 마세요.
- 이는 **개발·배포 소스**입니다. Windows·Android 빌드와 회귀 테스트 통과가 실계정과 실기기의 로그인·동작 검증을 대신하지 않습니다.
- 과거 README/CHANGELOG의 오래된 제품 이름 또는 목표가 남아 있을 수 있습니다. 현재 기준은 본 인수인계 문서와 최신 소스 코드입니다.

## 즉시 실행 (개발자 PC)

```powershell
cd pc
python -m unittest discover -s tests -q
python -m gametodo gui
```

선택적 계정 로그인 기능을 개발자 환경에서 설치하려면 `python -m pip install -r requirements-login.txt`. 일반 사용자 배포판에는 Python/pip 설치를 요구하지 않는 것이 목표입니다.

Android: Android Studio에서 `android/` 열기, JDK17 / SDK35, 또는 기존 Termux `studio build android :app:assembleDebug` 환경. APK 빌드와 서명·업데이트 메타데이터 검사는 통과했습니다. 실제 기기 동작은 별도 확인이 필요합니다.

## 개발 재개 결과

원본 인수 버전과 변경·검증 내역은 [2026-10-28 조사 기록](docs/INVESTIGATION_2026-10-28.md)을 참고하세요. [Windows EXE 수동 빌드](docs/WINDOWS_DISTRIBUTION.md)와 [명조 출처 상태](docs/WUTHERING_SOURCE_STATUS.md)는 실환경 검증 상태를 구분합니다. 로그인 실계정 성공 및 Windows EXE·Android 실기기 동작은 아직 미검증입니다.

최신 추가: [스텔라 KR 가챠 연결](docs/STELLA_KR_BANNERS.md), [즉시 완료·성공 알림·별도 설치 테스트판](docs/ANDROID_TEMP_0105.md).

[0.11.2 진행도 조회·스타레일 목표·새 게임 연결](docs/UI_0112.md): 로딩 표시와 앱 검색을 개선하고 Todoist 라벨로 게임을 추가할 수 있습니다.

[0.11.0 연결·설정·진행도 화면 개선](docs/UI_0110.md): 설치된 앱의 패키지와 서명을 유지하며 표시 이름을 사이퍼링크로 정리했습니다.
