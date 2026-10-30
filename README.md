# 사이퍼링크 · CipherLink

<!-- cipherlink-downloads -->
### 설치 파일 · 0.11.10

- [**Windows 설치·업데이트 다운로드**](https://github.com/Luchael/CipherLink/releases/download/v0.11.10/CipherLink-Windows-Setup.exe)
- [Windows 무설치 실행 파일](https://github.com/Luchael/CipherLink/releases/download/v0.11.10/CipherLink-Windows.exe)
- [Android APK 다운로드](https://github.com/Luchael/CipherLink/releases/download/v0.11.10/CipherLink-Android.apk)

[버전 상세 및 파일 목록](https://github.com/Luchael/CipherLink/releases/tag/v0.11.10)

<!-- /cipherlink-downloads -->

게임 진행도와 할 일을 Todoist에 연결하는 Windows·Android 앱입니다. 한국어·한국 시간(KST)을 사용하며 PC가 꺼져 있어도 Android에서 독립적으로 동기화합니다.

## Android 0.11.9 처음 설치

새 서명키를 사용하는 정식 앱입니다. **처음 한 번은 기존 앱 위의 업데이트가 아니라 별도 앱으로 설치**되며 계정 연결과 접근성·알림 권한을 다시 설정해야 합니다. 기존 앱과 데이터는 유지됩니다.

기존 앱의 **자동 확인과 게임 감지를 먼저 끈 뒤** 새 APK를 설치해 주세요. 두 앱의 자동 동기화를 동시에 켜지 마세요. 새 앱의 패키지는 `com.gametodo.cipherlink`이며, 이후 버전은 같은 패키지·서명키로 업데이트합니다.

## 설치·업데이트

0.11.10부터 Windows 설치 프로그램의 자동 닫기를 보강해, 종료 요청에 응답하지 않는 프로세스도 설치 대상 파일을 놓도록 처리합니다. 업데이트 전에 진행 중인 입력은 마무리해주세요. [검증 기록](docs/WINDOWS_UPDATE_SHUTDOWN.md)

- **Windows:** 설치·업데이트 파일을 실행하세요. 기존 위치에 업데이트하며 Python 설치는 필요 없습니다.
- **Windows 무설치판:** 앱을 종료한 뒤 EXE를 교체합니다.
- **Android:** 위의 APK를 설치합니다. 0.11.9 이후에는 새 정식 앱 위에 업데이트할 수 있습니다.
- **Windows 제거:** Windows 설정 → 앱 → 설치된 앱 → 사이퍼링크 → 제거. 기본 계정·설정 데이터는 보존합니다.

[설치·업데이트 안내](docs/DOWNLOAD_AND_UPDATES.md) · [릴리스 목록](https://github.com/Luchael/CipherLink/releases)

## 주요 기능

- 게임 계정의 일일·주간·회차별 진행도 조회와 Todoist 자동 완료
- 게임 초기화 날짜·시각과 실제 API 회차를 함께 검사해 이전 기록의 오완료 방지
- PC·Android에서 게임별 초기화 시각 설정
- 게임 화면의 플로팅에서 확인·수동 완료·할 일 추가
- 이름·날짜·반복·프로젝트·섹션 선택과 추가 재시도 중복 방지
- 게임 앱 검색·Todoist 라벨 연결, 프레임 단위 아이콘 이동과 화면 경계 처리
- 출처·기간을 확인한 캐릭터 가챠 일정 수집과 게임·`가챠` 라벨 적용

자동 진행도 연동은 원신·스타레일·젠레스 존 제로·엔드필드를 중심으로 구현되어 있습니다. API가 확인되지 않은 게임은 수동 체크를 사용합니다. 명일방주 자동 조회는 사용자가 허용한 PC 23:59 1회 정책을 유지합니다.

## 새 버전 자동 배포

버전을 올려 `main`에 반영하면 GitHub Actions가 버전 태그 생성 → Windows·Android 빌드 → APK 서명 확인 → 릴리스 게시 → **이 페이지 맨 위 다운로드 링크 갱신**을 자동으로 수행합니다. 버전 태그를 직접 올리거나 Actions에서 수동 실행할 수도 있습니다. 완료된 버전은 중복 게시하지 않습니다.

Android 개인 서명키는 GitHub Actions의 비공개 Secrets 두 개로 관리합니다. 서명키와 비밀번호는 공개 저장소·릴리스에 포함하지 않습니다. [자동 배포 설정과 검증](docs/AUTOMATIC_RELEASES.md)

## 개발·검증

현재 소스와 버전은 main 및 위 다운로드 영역에서 확인할 수 있습니다. [main 소스](https://github.com/Luchael/CipherLink/tree/main) · [개발용 소스 ZIP](https://github.com/Luchael/CipherLink/archive/refs/heads/main.zip)

```bash
cd pc
python -m pip install -r requirements-login.txt -r requirements-endgame.txt
python -m unittest discover -s tests -q
python -m gametodo gui
```

Android는 JDK 17·SDK 35·Gradle 8.10.2를 사용합니다. [프로젝트 시작 안내](CODEX_START_HERE.md) · [개발 지침](AGENTS.md)

회귀 테스트·빌드 성공은 실제 계정 로그인·게임 API·사용자 Windows·Android17 동작 검증을 대신하지 않습니다. 기존 게임의 공식 초기화 시각 전체 재검증도 남아 있습니다.

[0.11.10 변경](docs/releases/v0.11.10.md) · [Android 첫 전환 안내](docs/releases/v0.11.9.md) · [초기화·플로팅 구현과 검증](docs/RESET_FLOATING_0118.md) · [제품·Todoist 기준](docs/PRODUCT_AND_TODOIST.md)
