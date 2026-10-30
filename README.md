# 사이퍼링크 · CipherLink

게임 진행도와 할 일을 Todoist에 연결하는 Windows·Android 앱입니다. 한국어와 한국 시간(KST)을 사용하며, PC가 꺼져 있어도 Android에서 독립적으로 동기화합니다.

## 버전 안내

| 구분 | 버전 | 바로 가기 |
| --- | --- | --- |
| 설치 파일 | **플랫폼별 버전은 아래 링크 참고** | Windows 설치판·무설치판, Android 이전 버전 |
| 최신 소스 | **0.11.8 · main** | [소스 보기](https://github.com/Luchael/CipherLink/tree/main) · [변경·검증 기록](docs/RESET_FLOATING_0118.md) |

Windows는 정식 릴리스의 설치판으로 설치·업데이트합니다. **0.11.8의 수정은 0.11.8 설치 파일부터 적용됩니다.** Android 0.11.8은 기존 서명키가 없어 설치용 업데이트 APK를 아직 제공하지 않으며, 기존 0.11.7 APK에는 이 수정이 포함되지 않습니다.

<!-- cipherlink-downloads -->
### 설치 파일 · 0.11.7

**GitHub 저장소 소유자 계정으로 로그인한 뒤 다운로드하세요.**

- [**Windows 설치·업데이트 다운로드**](https://github.com/Luchael/CipherLink/releases/download/untagged-f06c6b073a26012ef117/CipherLink-Windows-Setup.exe)
- [Windows 무설치 실행 파일](https://github.com/Luchael/CipherLink/releases/download/untagged-f06c6b073a26012ef117/CipherLink-Windows.exe)
- [Android APK 다운로드](https://github.com/Luchael/CipherLink/releases/download/untagged-f06c6b073a26012ef117/CipherLink-Android.apk)

[버전 상세 및 파일 목록](https://github.com/Luchael/CipherLink/releases/tag/untagged-f06c6b073a26012ef117)

<!-- /cipherlink-downloads -->

직접 다운로드가 시작되지 않으면 위 **버전 상세 및 파일 목록 → Assets**를 열어주세요. 정식 릴리스는 바로 받을 수 있고, 기존 0.11.7 초안 파일은 소유자 계정 로그인이 필요합니다. [릴리스 목록](https://github.com/Luchael/CipherLink/releases)에서도 확인할 수 있습니다.

## 0.11.8에서 달라진 점

- 게임 초기화 날짜·시각과 API의 실제 회차를 함께 검사해 이전 기록으로 새 할 일이 완료되는 상황을 차단
- PC·Android에서 게임별 초기화 시각을 분 단위로 설정
- 플로팅의 `새로고침 · + · ×`에서 이름·날짜·반복·프로젝트·섹션을 지정해 할 일 추가
- 추가 요청을 재시도할 때 중복 등록 방지
- 아이콘 이동을 프레임 단위로 갱신하고 화면 회전·노치·시스템 영역을 고려해 위치 제한

기존 게임의 초기화 시각 전체 공식 재검증, 실제 계정과 Android17 기기 동작은 아직 미완료입니다. [구현 내용과 남은 확인 사항](docs/RESET_FLOATING_0118.md)을 참고하세요.

## 주요 기능

- 연결한 게임 계정의 일일·주간·회차별 진행도 조회
- 현재 회차의 목표를 충족하면 Todoist 작업 완료 및 모바일 알림
- 게임 화면의 사이퍼링크 플로팅 버튼으로 할 일 확인·수동 체크
- 설치 앱 검색과 Todoist 라벨을 이용한 게임 연결
- 출처와 기간을 확인한 캐릭터 가챠 일정 수집, 게임 라벨과 `가챠` 라벨 적용

자동 진행도 연동은 원신·스타레일·젠레스 존 제로·엔드필드를 중심으로 구현되어 있습니다. API가 확인되지 않은 게임은 수동 체크를 사용합니다. 명일방주 자동 조회는 사용자가 허용한 PC 23:59 1회 정책을 따릅니다.

## 설치와 업데이트

- **Windows 설치판:** 설치 파일을 실행하면 처음 설치하거나 기존 위치에 업데이트합니다. Python 설치는 필요 없습니다.
- **Windows 제거:** Windows 설정 → 앱 → 설치된 앱 → 사이퍼링크 → 제거. 기본 계정·설정 데이터는 보존합니다.
- **Windows 무설치판:** EXE를 실행합니다. 업데이트할 때는 앱을 종료한 뒤 EXE를 교체합니다.
- **Android:** 설치에 성공했던 앱 위에 같은 패키지·서명의 APK로 업데이트합니다. 원본 0.10.2와 별도 설치판은 서로 자동 통합되지 않습니다.
- 업데이트를 위해 기존 앱이나 데이터 폴더를 삭제하지 마세요. 비밀번호·쿠키·토큰은 공유하지 마세요.

[설치·업데이트·제거 안내](docs/DOWNLOAD_AND_UPDATES.md) · [Android 업데이트 호환성 안내](docs/APK_UPDATE_DIAGNOSIS.md)

## 개발

최신 소스는 [main 브랜치](https://github.com/Luchael/CipherLink/tree/main)에 있습니다. [소스 ZIP 받기](https://github.com/Luchael/CipherLink/archive/refs/heads/main.zip)는 개발용이며 설치 파일이 아닙니다.

PC 개발·실행:

```bash
cd pc
python -m pip install -r requirements-login.txt -r requirements-endgame.txt
python -m unittest discover -s tests -q
python -m gametodo gui
```

Android는 [android/ 프로젝트](android/)를 Android Studio에서 엽니다. JDK 17·SDK 35·Gradle 8.10.2를 사용합니다. 기존 별도 설치판의 패키지를 유지하려면 `cipherlinkPreview=true` 옵션이 필요하며, 업데이트 APK에는 기존 개인 서명키가 필요합니다.

[프로젝트 시작 안내](CODEX_START_HERE.md) · [개발 지침](AGENTS.md) · [제품·Todoist 기준](docs/PRODUCT_AND_TODOIST.md)

## 검증 범위

0.11.8은 PC 테스트 **292개**, Kotlin 회귀 프로그램 **28개**, Android 서명 없는 release 빌드를 통과했습니다. 실제 계정 로그인·게임 API·Todoist 생성·Windows 실행·Android 설치 성공을 의미하지 않습니다. 확인하지 못한 기록은 0점이나 완료로 간주하지 않습니다.

[최신 변경 내역 · 0.11.8](docs/RESET_FLOATING_0118.md) · [기존 설치판 · 0.11.7](docs/INSTALLER_0117.md) · [이전 기능 변경 · 0.11.6](docs/PROGRESS_0116.md)
