# 0.11.8 초기화 회차와 플로팅 개선

2026-10-30 KST. 이전 대화의 마지막 미완성 요청을 구현했다. 소스는 PC/Android 0.11.8, Android versionCode 36이며, README의 기존 0.11.7 다운로드는 그대로 유지한다. 새 설치판을 배포했다는 의미가 아니다.

## 재현한 문제와 수정

- Android `EndgameRecords.currentPeriod()`는 시유 같은 엔드 콘텐츠에 API 기간만 검사했다. 10월 30일 04:59 KST에 05:00까지 유효한 이전 시유 4/4 기록이 완료 근거로 허용되는 테스트가 수정 전 실패했다. 엔드 콘텐츠에도 게임별 초기화 시각과 기존 20분 캐시 유예를 함께 적용한다.
- PC는 엔드 콘텐츠의 종료 시각을 전달했지만 시작 시각은 완료 판정에 전달하지 않았다. 이전 시즌 시작일과 아직 미래인 종료일을 가진 점수가 오늘의 새 Todoist 회차를 완료하는 테스트가 수정 전 실패했다. 실제 API 시작/종료 기간을 보존하고 Todoist 현재 예정일의 게임 초기화 경계와 대조한다. 시작 기간을 확인하지 못하면 완료를 보류한다.
- Android도 Todoist 예정일과 API 시즌 시작일을 대조한다. 과거 미완료 작업의 플로팅 표시는 유지하며, 오늘의 새 작업만 해당 게임 초기화 전에는 숨긴다. 초기화 시각 미설정 게임의 오늘 작업은 보류하고 설정 안내를 표시한다.
- Android 엔드 콘텐츠 완료 명령의 회차 문자열을 PC의 기존 `rotation:until:<Unix seconds>`와 맞췄다. 같은 작업과 회차에 같은 UUIDv5가 생성된다. 기존 작업·사용자 반복·제목을 수정하지 않는다.
- 점수와 유효 회차를 한 번 확인하면 즉시 완료하는 정책과 승인 후 Android 알림은 유지한다. 새로 2회 관측 대기를 추가하지 않는다.

주요 파일: `SharedPeriods.kt`, `EndgameRecords.kt`, `AccountSync.kt`, `account_sources.py`, `account_watch.py`, `cycles.py`.

## 초기화 시각 설정

- Android 설정 → 게임 초기화 시각 → 게임 선택 → 시각 변경. 24시간 시간 선택기와 빠른 선택 버튼, 저장/취소/기본값 복원을 제공한다. 새 게임 라벨을 추가할 때도 시각 설정을 안내한다.
- 분 단위 HH:MM 설정을 자동 완료와 플로팅이 함께 사용한다. PC 설정에도 게임 선택과 시·분 선택/저장을 추가했다.
- 설정은 각 기기에 저장된다. PC와 Android를 함께 사용하면 같은 서버의 같은 KST 시각을 지정한다. Todoist에 마감 시각을 넣는 것으로 게임 회차 검사를 대신하지 않는다.
- 기존 설정과 인증은 보존한다. 기존 게임의 기본값이 공식 최신값이라고 새로 확정한 것은 아니다.

### 공개 출처 확인 범위

공식 HoYoLAB, GRYPHLINE 엔드필드, 명일방주, Steam 림버스 공지 접근을 시도했지만 현재 클라우드 프록시에서 CONNECT 403으로 차단됐다. 조사 대상 도메인을 환경 설정 **초안**에 저장했다. 초안은 현재 네트워크 적용·게시 완료를 의미하지 않는다.

접근 가능한 공개 코드로 [Hoyo Buddy의 서버 초기화 설정](https://github.com/seriaati/hoyo-buddy/blob/master/hoyo_buddy/constants.py)을 확인했다. Asia 서버 UTC+8 04시를 KST 05시로 환산하는 기존 HoYoverse 설정과 부합한다. 이는 커뮤니티 구현의 보조 근거이며 공식 공지를 새로 확인한 결과는 아니다. Todoist 필드와 위치 조회는 [공식 Python 클라이언트](https://github.com/Doist/todoist-api-python/blob/main/todoist_api_python/api.py)도 대조했다.

| 게임 | 현재 설정 취급 |
| --- | --- |
| 원신·스타레일·젠존제 Asia | 기존 05:00 KST 유지; 커뮤니티 서버 설정과 대조 |
| 명조 Asia·엔드필드 Asia | 기존 05:00 KST 유지; 이번 공식 재검증 미완료 |
| 림버스 | 기존 일간 06:00·주간 목요일 유지; 이번 공식 재검증 미완료 |
| 명일방주 | KR/글로벌 서버를 혼용하지 말 것. Android 기존 미설정 유지; PC 레거시 값은 사용자 설정에서 확인 필요 |
| 스텔라소라 KR·리버스1999 KR | 기존 미설정 유지. 검증되지 않은 시각을 추가하지 않음 |
| 컬러스위퍼·새 라벨 게임 | 사용자가 직접 시각 지정 |

기존 게임 전체의 공식 초기화 시각 조사는 아직 완료하지 못했다. 특히 일일 초기화 시각을 모든 시즌 콘텐츠의 고정 초기화 날짜로 일반화하지 않으며 API의 실제 시즌/주차 기간을 계속 확인한다.

## 플로팅에서 할 일 추가

- 목록 헤더를 `새로고침 · + · ×`로 구성했다.
- `+`에서 이름, 날짜(날짜 선택기·오늘/내일), 반복(없음/매일/매주/매월/N일/직접 입력), 프로젝트/섹션을 지정한다.
- 실제 Todoist 프로젝트와 섹션을 페이지네이션으로 읽는다. 기존 플로팅 제외 정책과 일치하도록 가챠·이벤트 섹션은 선택 목록에서 제외한다. 현재 게임의 라벨을 함께 저장한다.
- 저장 중 중복 클릭을 막는다. 네트워크 결과가 불확실하면 입력과 요청 UUID를 기기에 보존하고 동일 요청으로 재시도한다. 계정별로 대기 요청을 분리한다. 명시적 서버 거절일 때만 편집을 다시 허용한다.
- 미래 날짜나 오늘 초기화 전의 작업은 추가에 성공해도 시작 시각 전까지 목록에 나오지 않는다. 실제 계정으로 생성·반복 날짜 해석·기기 키보드 동작은 미검증이다.

주요 파일: `FloatingTaskComposer.kt`, `FloatingTaskDraft.kt`, `FloatingTaskRequest.kt`, `TodoistApi.kt`.

## 이동과 화면 경계

아이콘 이동 요청을 화면 프레임 단위로 합쳐 과도한 WindowManager 갱신을 줄였다. 손을 뗄 때 마지막 좌표를 반영하고 위치를 저장한다. 여러 손가락의 포인터 전환, 화면 회전, 시스템 바·디스플레이 컷아웃을 고려해 좌표를 제한한다. 회전 시 열린 패널의 폭과 목록 높이도 조정한다. 실제 기기의 체감 이동 품질은 미검증이다.

## 검증

- PC 전체 unittest **290개 통과**. 로그인/진행도 개발 의존성을 설치한 가상 환경에서도 통과했다.
- Kotlin 회귀 **28개 프로그램 통과**. 신규 초기화 경계, 분 단위 사용자 설정, 이전 미완료 유지, 입력 검증, 실제 추가 요청 JSON과 재시도 UUID, PC/Android UUID 일치를 포함한다.
- Android `-PcipherlinkPreview=true :app:assembleRelease` 성공. 결과는 **서명되지 않은 APK**이며 `com.gametodo.nativeapp.preview`, versionCode 36, 0.11.8을 확인했다. ZIP 무결성 및 release lint vital 검사 통과.
- PC/Android/Windows 리소스 버전 일치 검사 통과. Windows EXE/설치판 재빌드와 실제 GUI 실행은 이번 환경에서 미실행이다.
- Android17 실제 설치·게임 로그인·알림·Todoist 실제 생성·초기화 실응답은 미검증이다. 위 테스트·빌드 성공을 실제 계정 동작 성공으로 보고하지 않는다.

기존 APK 업데이트에 필요한 개인 서명키는 현재 `/workspace`와 `/tmp`에서 찾지 못했다. 새 키를 만들거나 원본 앱 삭제를 요구하지 않았다. 기존 설치 계열의 키를 안전한 기존 빌드 환경에서 복구한 뒤 같은 인증서로 서명해야 설치용 업데이트 APK를 제공할 수 있다. APK나 인증서 지문에서 개인 키를 복구할 수는 없다.

## 개발 환경

JDK 17.0.21, Gradle 8.10.2, Kotlin 2.0.21, Android SDK 35/Build Tools 35.0.0과 PC 로그인/진행도 의존성을 `/workspace/.tools/cipherlink`에 준비했다. 공급자 체크섬·TLS 검증을 유지했으며 새 서명키는 생성하지 않았다.

```bash
source /workspace/.tools/cipherlink/env.sh
cd /workspace/CipherLink/pc
python -m unittest discover -s tests -q
cd /workspace/CipherLink
python tools/run_kotlin_tests.py
gradle --no-daemon --max-workers=2 --console=plain -p android -PcipherlinkPreview=true :app:assembleRelease
```

위 Gradle 명령은 설치 가능한 서명 APK를 만들지 않는다. 실제 계정 비밀이나 서명키를 로그/채팅/저장소에 넣지 않는다.

## 후속 정식 배포

사용자가 별도 테스트 브랜치·초안 대신 main과 정식 릴리스에 적용하도록 지시했다. 최신 소스는 main에 반영하고, `Release CipherLink` 워크플로는 버전 태그에서 Windows 설치판·무설치판을 빌드해 검증 후 정식 게시한다. 새 Windows 전용 메타데이터 및 Android 이전 버전 링크 검사까지 PC 테스트는 292개다. Android의 기존 설치 계열과 서명은 유지하며, 0.11.8 설치용 APK는 기존 서명키 없이는 제공하지 않는다.

### 정식 배포 확인 결과

[Release CipherLink 실행 41059750779](https://github.com/Luchael/CipherLink/actions/runs/41059750779)이 성공했다. Windows EXE 빌드와 설치·업데이트·제거 검사를 통과한 뒤 [v0.11.8 정식 릴리스](https://github.com/Luchael/CipherLink/releases/tag/v0.11.8)에 설치판·무설치판·체크섬·Windows 전용 update.json을 게시했다. 릴리스와 두 실행 파일 다운로드 주소 모두 HTTP 200을 확인했다. update.json의 버전 0.11.8 및 Android 업데이트 미포함도 확인했다. main의 README 다운로드 링크는 CI가 실제 첨부파일에 맞춰 갱신했다. 사용자 PC의 실계정 동작 검증과 Android 기존 서명키 복구는 별도다.
