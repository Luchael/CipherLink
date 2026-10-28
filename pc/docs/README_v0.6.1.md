# GameTodo Auto Sync v0.6.1 — 로그인·진단·가챠 수집 보완

> 기존 일반 이벤트 자동 등록 기능을 제거했습니다. **현재 진행 중인 캐릭터 픽업·복각**만 Todoist에 추가하고, 종료 시각이 지나면 자동으로 완료합니다. 기존 일일·주간·엔드콘텐츠 감지 기능은 유지합니다.


## v0.6.1에서 가장 먼저 할 일

화면에서 `Todoist: 연결됨`만 보인다면 **실제 API에 연결됐다는 의미가 아니었습니다**.
이번 버전은 *저장됨(미검증)*과 *실제 API 검증됨*을 구분합니다.

1. 기존 프로젝트에 v0.6.1 파일을 덮어씁니다. `config.json`과 `data/`는 삭제하지 않습니다.
2. `run_windows.bat` 실행 (한국어 CMD용 CP949/CRLF, `python` 명령 사용).
3. GUI에서 **Todoist 연결 시험**을 누릅니다. HTTP 401이면 새로 브라우저 로그인합니다.
4. **Todoist 대상 위치 선택**을 누르고 실제 프로젝트의 `이벤트 / 기간 한정` 섹션을 선택합니다.
5. **현재 가챠 미리보기**로 수집 데이터를 점검하고 **지금 동기화**를 누릅니다.
6. 문제가 남으면 `python -m gametodo doctor --config config.json`을 실행합니다.
   토큰·비밀번호·쿠키는 진단 화면에 표시하지 않습니다.

### 각 게임의 최초 로그인 지원 현황

| 게임 | 계정 조회 연동 | 현재 연결 방법 | 주의 |
|---|---|---|---|
| 원신·스타레일·젠존제 | HoYoLAB 계정 데이터 | HoYoLAB 웹 로그인 → `HoYoLAB 로그인 연동` | 최초 연결에 `genshin[cookies,rsa]` 필요. 지원되는 아시아 UID를 자동 등록 |
| 엔드필드 | SKPORT 상태 조회 | SKPORT 웹 로그인 → `엔드필드 계정 연결` | 브라우저가 인증 쿠키를 제공할 때만 자동 연결; API/쿠키 변경 시 실패 |
| 명조 | KuroBBS 상태 조회 | KuroBBS 웹 로그인 → `명조 계정 연결` | KuroBBS의 토큰이 브라우저 쿠키에 없어 자동 획득이 안 될 수 있음 |
| 명일방주 KR | ArkPRTS | `명일방주 Yostar 연결` → 메일 인증 | 사용자 본인 이메일·일회용 인증코드 입력 필요, 실제 계정 연동 미검증 |
| 리버스: 1999 | 없음 | 자동 로그인 없음 | 검증된 외부 계정 진행도 API 없음 |
| 림버스 컴퍼니 | 없음 | 자동 로그인 없음 | 게임 계정 로그인≠작업 데이터 API 제공 |
| 스텔라 소라 | 없음 | 자동 로그인 없음 | 공개 캐릭터·가챠 API와 개인 완료 정보는 별개 |

`컬러스위퍼`는 제외되어 있습니다. 위 표의 '연결 방법'은 코드로 구현한 절차이며
실제 브라우저·게임사의 로그인 정책에 따라 불가능한 환경이 있습니다.
게임의 내부 메모리·네트워크 암호화·안티치트를 우회하는 기능은 제공하지 않습니다.

### 게임 로그인 모듈 설치

GUI에서 **게임 로그인 모듈 설치** 버튼을 직접 누르거나 다음 명령을 사용합니다.

```bat
python -m pip install -r requirements-login.txt
```

`requirements-login.txt`는 `genshin[cookies,rsa]`, `browser-cookie3`, `arkprts`를 설치합니다.
필요한 라이브러리만 별도로 설치할 수 있습니다.

### 왜 가챠가 안 보일 수 있나?

- 데이터 수집 사이트가 현재 해당 게임의 픽업을 등록하지 않았거나, 페이지 구조가 바뀐 경우
- 서버가 응답하지 않거나 웹 자동 요청을 제한한 경우
- 로그인은 정상이어도 Todoist **프로젝트 / 섹션 ID가 기존 설정과 다를** 경우

이제 GUI에서 수집 실패 게임별 HTTP 상태/오류 종류를 볼 수 있고,
Todoist 연결 및 섹션 위치도 별도로 확인할 수 있습니다.
현재 픽업이 0개일 때 **기존 가챠를 임의로 완료하거나 삭제하지 않습니다**.

**자동 테스트 90개는 외부 API를 모의 처리하는 오프라인 테스트**입니다.
실제 Windows 브라우저 계정 로그인, 제3자 서버의 API 응답, PyInstaller 빌드는 검증되지 않았습니다.

## 빠른 시작 · Windows

1. Python 3.10 이상을 설치합니다. `python --version`으로 확인합니다.
2. ZIP 압축을 풉니다. 기존 v0.5.x라면 기존 폴더에 덮어쓰고 **config.json, data 폴더는 유지**합니다.
3. `run_windows.bat`을 더블클릭합니다. CP949/CRLF이며 `python` 명령을 사용합니다.
4. GUI에서 **Todoist 브라우저 로그인**을 누릅니다. 공식 Todoist 페이지에서 본인이 로그인·승인합니다. **토큰이나 개발자 키를 직접 입력하지 않습니다.**
5. 로그인한 후 현재 가챠 미리보기 또는 지금 동기화를 누릅니다. 이후 GUI가 열려 있는 동안 자동 동기화가 실행됩니다.
6. GUI의 **로그인 시 자동 실행** 버튼을 누르면 Windows 사용자 로그인 시 프로그램이 열립니다. 관리자 권한은 필요 없습니다.

## 로그인 원리

**Todoist**: 공식 OAuth `https://api.todoist.com/oauth/register`(동적 앱 등록)를 이용하며, 동의 화면은 Todoist가 제공합니다. 인증 코드가 `localhost:18766`으로 돌아오면 OAuth 토큰을 자동으로 교환하고 로컬에 저장합니다. `refresh_token`이 있으면 자동 갱신합니다. **등록/로그인 자체는 실제 Todoist 계정에서 검증하지 못했으므로** Todoist 서비스 정책과 로컬 콜백 제약에 따라 추가 작업이 필요할 수 있습니다. 방화벽에 공용 접근을 열지 마세요.

**HoYoLAB**: 가챠 목록은 공개 페이지에서 수집하므로 HoYoLAB 로그인이 필요 없습니다. **기존 원신·스타레일·젠존제 계정 상태 자동 감지**를 이용할 때만 선택적으로 로그인합니다. `HoYoLAB 로그인 페이지`에서 브라우저 로그인 후 `HoYoLAB 로그인 연동`을 누르면 `genshin.py`가 지원하는 브라우저의 HoYoLAB 쿠키만 가져와 저장합니다. 최초 설정에 `python -m pip install "genshin[cookies]"`이 필요할 수 있습니다. 브라우저 암호화 정책 때문에 자동 추출이 실패할 수 있으며, 이를 우회하지 않습니다. Android의 다른 브라우저 앱 쿠키에는 Termux가 접근할 수 없으므로 Android HoYoLAB 연결은 현재 자동 동작을 보장하지 않습니다.

**저장 위치:** Windows 사용자 계정의 DPAPI로 암호화되어 `~/.gametodo/secrets/`에 저장됩니다. Linux/Termux는 `0600` 제한 파일에 저장(암호화 아님). 복사/백업/공유하지 마세요. OAuth 토큰, 비밀번호 및 세션 쿠키는 Git 저장소에 커밋하지 마세요.

## 게임별 Todoist 제목·라벨

| 게임 | 예제 제목 | 라벨 |
|---|---|---|
| 원신 | `[원신] 스커크` | `원신` |
| 붕괴: 스타레일 | `[열차] 펄` | `스타레일` |
| 젠레스 존 제로 | `[젠존제] 피닉스` | `젠레스존제로` |
| 명조 | `[명조] 캐릭터명` | `명조:워더링웨이브` |
| 림버스 컴퍼니 | `[림컴] 캐릭터명` | `림버스컴퍼니` |
| 명일방주: 엔드필드 | `[엔필] 캐릭터명` | `명일방주:엔드필드` |

캐릭터명은 **실제 소스에서 추출된 경우에만 등록**합니다. 버전 정보는 확인된 경우 `game_settings.게임키.version_label` 값을 제목 뒤 `(버전)`으로 추가할 수 있습니다. 버전 미확인 시 추측해 넣지 않습니다. 리버스: 1999·명일방주·스텔라 소라는 현재 검증된 KR 픽업 출처가 없어 자동 추가하지 않습니다. 컬러스위퍼는 제외합니다. 무기/광추/음동기 전용 가챠와 일반 이벤트는 의도적으로 제외합니다.

## 종료 자동 처리 (Todoist Free)

- **due 날짜/마감일(deadline)을 아예 설정하지 않습니다.** 종료시간은 `GameTodo-Banner-ID`와 함께 작업 설명에만 기록합니다.
- 매 동기화에 프로그램이 현재 시각(한국 시간)과 저장된 종료 시각을 비교해 종료 작업에 `item_close`를 보냅니다.
- Todoist에 이미 존재하는 예전 일반 이벤트, 수동 등록한 작업 및 정기 콘텐츠는 자동 종료하지 않습니다.
- 두 기기에서 실행해도 같은 픽업은 결정적인 Todoist Sync 명령 UUID와 원격 설명 ID로 중복 생성을 줄입니다.
- 사이트가 접속되지 않아도 *이미 알고 있는* 종료 시각을 토대로 처리하지만, 종료일 변경 공지가 반영되기 전에 닫힐 수 있으므로 **변경된 실제 서버 일정은 출처 확인이 필요**합니다.
- PC/폰 프로그램이 모두 종료되어 있다면 정확한 종료 순간에 체크할 수 없습니다. 다음 실행 시 체크합니다. Windows 로그인 시 자동 시작을 권장합니다.

## 직접 실행하는 CLI

```bash
python -m gametodo gui               # PC 설정 창
python -m gametodo login-todoist     # Todoist 웹 로그인 (토큰 직접 입력 X)
python -m gametodo login-hoyolab     # HoYoLAB 로그인 웹사이트 열기
python -m gametodo hoyolab-import    # 브라우저의 HoYoLAB 세션 가져오기
python -m gametodo banners-preview  # 가챠 목록 미리보기 (Todoist 변경 없음)
python -m gametodo banners-once     # 가챠 등록/종료 처리 1회
python -m gametodo run              # 가챠 + 기존 계정/주간 감지 지속 실행
python -m gametodo accounts-status  # 계정 진행도 조회만
```

## Android (별도 장비 불필요)

Termux에서는 기존 `run_termux.sh`로 PC와 동일한 동기화 코어가 실행됩니다. 한 번 `python -m gametodo login-todoist`를 실행하면 Android 웹 브라우저로 OAuth 로그인을 엽니다. APK 폴더(`android/companion`)는 **기존 게임 실행 감지·플로팅용 Kotlin 소스**이고 이 ZIP에 설치 가능한 APK는 없습니다. Termux와 앱의 내부 저장소가 분리되므로 앱 화면과 계정 동기화는 브리지를 이용합니다. Android 실기기 OAuth/빌드/배터리 최적화는 검증하지 못했습니다.

## 배포하기

PC에 PyInstaller가 설치돼 있다면 `build_windows.bat`으로 **독립 실행 파일**을 만들 수 있습니다. 생성 경로는 `dist/GameTodo.exe`입니다. 자동 빌드 스크립트를 제공하지만 이 작업 환경에는 PyInstaller/Windows SDK가 없어 **EXE를 실제로 빌드하지는 못했습니다.** 개인정보 파일과 `config.json`을 공개 배포본 ZIP에 절대 포함하지 마세요.

프로그램 자체는 오픈소스 라이브러리/API의 기능을 활용하지만, 사전 조사에 언급된 타사 GitHub 소스 코드를 그대로 복사한 것은 아닙니다. 공개 캘린더 출처: https://www.pickupcal.com/ (비공식, 데이터의 정확성은 공식 게임 공지로 검증하세요.) Todoist OAuth 문서: https://developer.todoist.com/api/v1/ . HoYoLAB 로그인: https://seria.is-a.dev/genshin.py/authentication/ .

## 수정하기 쉬운 파일

- `gametodo/banners.py`: 한국 서버 픽업 HTML 파서, 캐릭터명 추출, 버전 표기
- `gametodo/banner_sync.py`: Todoist 등록·종료·중복 방지 규칙, 마감일 미사용
- `gametodo/oauth_login.py`: Todoist 최초 로그인/토큰 갱신
- `gametodo/hoyolab_login.py`: HoYoLAB 브라우저 세션 인증
- `gametodo/gui.py`: Windows 팝업 디자인·사용자 설정
- `gametodo/games.py`: 접두사·라벨 규칙
- `gametodo/account_watch.py`: 기존 일일·주간 자동 체크
- `gametodo/store.py`: SQLite 저장소와 다음 가챠 종료 시각
- `tests/test_banners.py`: 빈 데이터, 종료 시각, 중복 방지, 무료 플랜 테스트

`python -m unittest discover -s tests -q`로 기존 기능 포함 오프라인 테스트를 실행하세요.
