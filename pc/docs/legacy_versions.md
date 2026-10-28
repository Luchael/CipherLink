# GameTodo Auto Sync v0.3.0 — Todoist 게임 연동

Windows PC와 Android(Termux + 별도 Android 플로팅 앱 소스)에서 **별도 외부 서버/장비 없이** 같은 Todoist 계정에 동기화하는 개인용 프로젝트입니다.

**v0.2.0에서 적용됨:** 게임별 접두사·라벨, 기존 자동생성 이벤트 보정, 오프라인/경품/외부 캠페인 제외, 엔드필드 활성화, 휴대폰 게임 실행 시 펼치는 Todo 플로팅, 최초 1회 인증값 저장, *선택적* HoYoLAB 원신 일퀘 판정.

> v0.2.0 기준 설명(상단의 v0.3.0 항목 우선): Python 이벤트 등록·라벨·플로팅용 로컬 API는 구현 및 오프라인 단위테스트 완료. 실제 Todoist 계정에 대한 이번 버전 실연동 검증은 못 했습니다. **Android APK는 빌드되지 않았고 실제 휴대폰 테스트도 전입니다.** 실게임 자동완료는 원신 HoYoLAB 선택형 어댑터만 작성되어 있으며 다른 게임의 모든 보상 감지는 여전히 미완성입니다. 화면 OCR은 기본 꺼짐입니다.

## v0.3.0: 화면 인식 없이 계정 API로 게임 상태 조회 (NEW)

**추가된 실제 코드**: `gametodo/live_data.py` (보상 수령 상태 검증), `account_sources.py` (HoYoLAB/KuroBBS/SKPORT 어댑터), `skport.py` (SKPORT 인증 및 읽기 전용 조회), `account_watch.py` (2회 재검증/할 일 완료).

**현재 정확한 상태**: 정적 파서·요청 구조·Todoist 완료 판정은 모의 데이터로 테스트를 통과했습니다. **개인 계정 로그인/실제 계정 API/실제 Todoist 완료는 아직 검증되지 않았습니다.** 10개 게임의 모든 콘텐츠 자동완료를 보장하지 않습니다. PC와 Android 두 곳 모두 외부 서버 없이 독립 실행하되 모바일에서는 Termux 실행이 필요합니다. 플로팅 안드로이드 APK는 여전히 빌드되지 않은 소스 상태입니다.

### 게임별 신규 연동 현황

| 게임 | 계정 데이터 원천 | 조회 | 게임 내 일퀘 Todoist 자동 체크 |
|---|---|---|---|
| 원신 | HoYoLAB 실시간 메모 (genshin.py) | 진행도 + 추가 보상 수령 상태 | **명시적 수령 확인 후 자동** (실계정 테스트 전) |
| 붕괴: 스타레일 | HoYoLAB 실시간 메모 (genshin.py) | 일일 훈련·시뮬 우주 점수 | 점수만 있으면 **절대 자동 완료 안 함**; 전체 보상 수령 플래그까지 제공된 경우만 후보 |
| 젠레스 존 제로 | HoYoLAB 실시간 메모 (genshin.py) | 활약도·주간 점수 | 활약도만 있으면 **절대 자동 완료 안 함**; 전체 보상 수령 플래그까지 제공된 경우만 후보 |
| 명조 | KuroBBS 계정 위젯 API | 일일 활약도·주간 지표 | **읽기 전용** (모든 보상 수령 플래그 없음) |
| 엔드필드 | SKPORT 실시간 계정 카드 API | 일일 임무 포인트 | **읽기 전용** (모든 보상 수령 플래그 없음) |
| 리버스 1999 · 림버스 컴퍼니 · 스텔라 소라 · 명일방주(글로벌) · 컬러스위퍼 | 계정별 완료 상태를 제공하는 신뢰할 만한 글로벌/한국 읽기 전용 API 미확인 | 기존 플로팅/수동 체크 사용 | 자동 완료 구현 불가, 화면 OCR은 기본 OFF |

플랫폼 공식 게임 기록에 진척도가 있더라도 최종 보상 *수령* 여부가 없으면 완료 처리하지 않습니다. 잘못된 토큰/서버/데이터 구조/알 수 없는 값은 **보류**합니다. 이 원칙은 기존 `이벤트 / 기간 한정`에도 동일합니다. 외부 공개 이벤트 일정과 사용자 개인 보상 수령 데이터는 서로 다른 정보입니다.

### 설정: Windows / Termux 공통

기존 `config.json`/`data/`는 절대 삭제하지 마세요. ZIP의 파일을 덮어쓰고 `config.json`만 **기존 내용을 유지하면서** 아래 키를 합쳐 넣으면 됩니다. 새 설치라면 `config.example.json`을 복사합니다.

1. `python -m pip install genshin` (원신/스타레일/젠존제 연동을 쓸 기기에서만, HoYoLAB 비공식 라이브러리).
2. `python -m gametodo auth hoyolab` — 처음 한 번, HoYoLAB `ltuid_v2`/`ltoken_v2`를 포함하는 개인 로그인 쿠키를 안전하게 로컬 저장. 채팅으로 보내지 마세요.
3. `config.json`에서 아래 `hoyolab` 값 활성화 후 각 게임의 **아시아 서버** UID 등록(숫자만):

```json
"hoyolab": {
  "enabled": true,
  "uids": {"genshin": "본인_원신_아시아_UID", "hsr": "본인_스타레일_아시아_UID", "zzz": "본인_젠존제_아시아_UID"},
  "interval_minutes": 20,
  "daily_task_name": "[원신] 일퀘"
}
```

4. 외부 계정 상태 **조회만** 해보려면: `python -m gametodo accounts-status`. 이 명령에는 Todoist 토큰이 필요 없고, 현재 조회 가능한 점수와 보상 수령 상태만 출력합니다. UID 끝 4자리만 표시합니다.
5. 보상 수령이 명확히 확인된 항목을 Todoist와 연결: `python -m gametodo accounts-once` 또는 원래의 `python -m gametodo run`. 동일 날짜에 2회(120초 이상 간격, 90분 이내) 확인해야 적용합니다. 20분 간격 폴링에도 정상 작동하도록 v0.2.0의 재검증 창 버그를 수정했습니다.

**명조 KuroBBS**: 공개 문서에 있는 위젯 데이터 조회 기능을 사용합니다. `python -m gametodo auth kurobbs`로 KuroBBS 세션 토큰을 저장한 뒤 `account_data.wuthering`의 `enabled`, `role_id`, `server_id`를 설정하고 `account_data.enabled=true`로 변경합니다. 명조 중국 서버는 거부하며, 서버명에 지역 정보가 없는 경우 공식 앱에서 아시아 서버를 확인한 후 `asia_server_verified=true`를 최초 한 번 설정해야 합니다. **로그인/응답 실계정 검증 전**입니다.

**엔드필드 SKPORT**: `python -m gametodo auth skport`로 개인 `ACCOUNT_TOKEN`을 저장합니다. `account_data.endfield`의 `enabled`, `role_id`, `server_id`를 설정한 뒤 글로벌 `account_data.enabled=true`로 변경합니다. 계정 바인딩 정보의 아시아 서버를 검증한 경우에만 조회합니다. 서버명이 생략된 경우 공식 SKPORT에서 확인 후 `asia_server_verified=true` 사용. 인증 및 서명 코드는 비공식 문서를 기반으로 작성되어 **실제 계정에서 성공 여부 미검증**입니다.

설정 예시는 [`config.example.json`](config.example.json)을 참고하세요. 게임별 주기, 일퀘 제목은 `account_data.interval_minutes`/`account_data.task_names`에서 변경할 수 있습니다.

### 자동 체크 작동 원리

`계정 인증(첫 1회)` → `개별 게임 API 상태 조회(기본 20분)` → `수치/완료 보상 플래그 분리` → `동일 계정/날짜 2회 확인` → `정확히 일치하는 Todoist 할 일 1개만 완료`. 현재 기본 설정에는 **주기적 스크린샷/기기 메모리 접근/게임 패킷 가로채기/자동 클릭을 사용하지 않습니다.** API 조회가 가능한 상태라면 게임을 실행할 필요도 없습니다. 인증이 만료된 경우에만 새 로그인값이 필요합니다.

**중요:** HoYoLAB 웹 출석체크는 게임 안의 일일 퀘스트가 아닙니다. 스타레일 `500/500`, 젠존제 `400/400`, 명조 `100/100`, 엔드필드 일일 점수 최대치도 '보상 수령'을 입증하지 않습니다. 그래서 조건 11을 어기면서 자동 완료하는 기능은 제공하지 않습니다. 최종 보상 수령 정보를 명시적으로 주는 API 응답이 발견되면 `gametodo/live_data.py`의 단일 판정 모듈에 추가할 수 있습니다.

### 조사에 사용한 오픈소스 및 문서

- HoYoLAB 3게임: https://github.com/Liesegang/ha-hoyolab · https://seria.is-a.dev/genshin.py/reference/clients/chronicle/zzz/
- 명조 KuroBBS 위젯: https://github.com/TomyJan/Kuro-API-Collection/blob/master/API/gamer/widget/game3/getData.md
- 엔드필드 계정 카드 API: https://github.com/AixLnyt/skport-api-docs
- 엔드필드 실시간 데이터 공식 설명: https://endfield.gryphline.com/en-us/news/0748

---

## 게임별 제목 및 Todoist 라벨

| 게임 키 | 새 이벤트 제목 예시 | 라벨 |
|---|---|---|
| `genshin` | `[원신] 꽃의 축제` | `원신` |
| `hsr` | `[열차] 꽃의 축제` | `스타레일` |
| `zzz` | `[젠존제] 꽃의 축제` | `젠레스존제로` |
| `wuthering` | `[명조] 꽃의 축제` | `명조:워더링웨이브` |
| `limbus` | `[림컴] 꽃의 축제` | `림버스컴퍼니` |
| `stella` | `[스소] 꽃의 축제` | `스텔라소라` |
| `reverse1999` | `[립9] 꽃의 축제` | `리버스1999` |
| `colorsweeper` | `[색지뢰] 꽃의 축제` | `컬러스위퍼` |
| `arknights` | `[명방] 꽃의 축제` | `명일방주` |
| `endfield` | `[엔필] 꽃의 축제` | `명일방주:엔드필드` |

제목을 제외한 정보(종료 시간, URL 등)는 Todoist 설명에만 적습니다. 마감 날짜는 **한국 서버 이벤트 종료일**. Todoist에 동일 이벤트가 이미 자동 등록되어 있고 현재 수집 대상에 포함되어 있으면 새로 만들지 않고 접두사/라벨/연장된 날짜만 교정합니다. **기존 수동 작업은 수정하지 않습니다.** 예전 버전이 등록한 오프라인 이벤트를 자동 삭제하지도 않습니다.

## 업데이트시 데이터 보호

- 현재 버전에서 **`config.json`, `data/` 폴더는 유지**합니다. 새 ZIP에는 `config.example.json`만 들어 있습니다.
- 압축을 기존 상위 폴더에 **덮어쓰기**하면 Python 코드만 변경됩니다.
- 단, 이미 사용하던 `game_todo_auto_sync` 폴더 전체를 삭제하면 `config.json` 및 SQLite 기록이 삭제됩니다. 삭제 대신 별도 백업 권장.
- 옛 0.1 설정에서 `endfield.enabled=false`는 '추후 추가' 임시값이라 0.2로 올릴 때 자동으로 True 취급합니다. `schema_version: 2`인 설정은 사용자의 True/False 선택을 존중합니다.

## Windows 실행 — Python 3.10 이상

1. ZIP을 풀고 **`game_todo_auto_sync`** 폴더 안에서 CMD를 엽니다.
2. `config.json`이 없다면 `copy config.example.json config.json`
3. **처음 한 번만** `python -m gametodo auth todoist`를 실행하여 직접 토큰을 입력합니다. 입력은 화면에 나타나지 않습니다.
4. `python -m gametodo preview` — 등록 예정 이벤트를 미리 확인합니다.
5. `python -m gametodo once` — 실제 Todoist 등록/기존 0.1 이벤트 제목·라벨 보정.
6. 계속 실행하려면 `run_windows.bat`.

Windows에서는 저장된 인증값을 **해당 Windows 계정 DPAPI로 암호화**하므로 재실행마다 입력할 필요가 없습니다. `.gametodo/secrets`는 사용자 홈 디렉터리에 있으며 프로젝트 ZIP에 포함하지 않습니다. 인증이 만료/변경되면 `auth todoist` 명령을 다시 사용하세요.

## Android — Termux 동기화 + 플로팅 앱

다음 명령을 Termux에서 실행합니다. ZIP을 휴대폰 다운로드 폴더에 넣고 Termux 저장소 권한을 이미 허용했다고 가정합니다.

```sh
pkg install python unzip
cd ~/storage/downloads
unzip -o game_todo_auto_sync_v0.2.0.zip -d ~/
cd ~/game_todo_auto_sync
cp -n config.example.json config.json
python -m gametodo auth todoist       # 최초 1회
python -m gametodo mobile-key         # 최초 1회 생성된 연결 비밀키 확인
python -m gametodo run
```

- Android 플로팅 앱은 `android/companion/`에 **소스 코드만 제공**합니다. **이번 파일에 설치 가능한 APK는 없습니다.** Android Studio/Android SDK 등으로 빌드해야 하며, Android 휴대폰만으로 빌드·설치하는 방법은 검증하지 않았습니다. APK를 한 번 설치하고 나면 휴대폰 자체 + Termux만으로 실행하며 PC 서버가 필요 없습니다.
- 앱 최초 사용 시: `mobile-key` 출력 키를 앱에 1회 입력 → 접근성 권한 → '다른 앱 위에 표시' 권한 → `패키지명=게임키` 대응표 입력 → 저장.
- 이후 게임을 실행하면 작은 `☑ 게임` 버튼이 나타나며, **눌렀을 때만** 해당 게임의 미완료 Todoist 작업을 불러옵니다. '완료'는 직접 눌렀을 때에만 전송됩니다. 자동으로 텍스트를 읽거나 지속 화면 캡처하지 않습니다.
- 기본 등록된 패키지는 원신·스타레일·젠존제 *예시*뿐입니다. 나머지 게임은 먼저 실행한 후 앱 홈에 표시되는 **최근 감지된 미등록 앱 패키지**를 보고 한 번 등록해야 합니다. 스토어/국가별 패키지명이 다를 수 있습니다.
- `LOCAL_BRIDGE_SECRET` 환경변수를 사용하던 경우에는 해당 값이 우선합니다. 모바일 앱에도 **같은 키**를 저장해야 합니다. 따로 입력하지 않으면 `mobile-key`로 생성한 키가 자동 사용됩니다.
- Android 설정이 Termux 프로세스를 중단하면 플로팅 목록을 불러오지 못합니다. 배터리 절약/상시 연결은 트레이드오프입니다.
- Termux에 저장되는 비밀값은 홈 폴더의 `0600` 파일이며 **Android Keystore 암호화는 아닙니다.** 휴대폰을 루팅하거나 다른 앱에 Termux 데이터를 공개하지 마세요. 인증 쿠키/토큰을 이 대화에 붙여넣지 마세요.

### 게임별 플로팅 작동 흐름

`게임 실행 감지(접근성 창 전환 이벤트)` → `작은 버튼 표시` → `사용자가 펼침` → `Termux의 127.0.0.1 로컬 브리지` → `Todoist에서 해당 게임만 읽음` → `직접 완료 버튼을 누르면 Todoist에 반영`.

백그라운드에서 일정한 주기로 스크린샷을 찍지 않으며, 게임이 꺼지면 플로팅도 닫힙니다. 이미지를 외부 서버로 보내지 않습니다. 필요할 때만 옵션으로 OCR을 켤 수 있지만 실제 게임별 보상 수령 문구를 검증하기 전까지 해당 OCR이 Todoist를 자동완료하지 않습니다.

## HoYoLAB 원신 일퀘 자동완료 (선택형, 기본 OFF)

HoYoLAB **웹 출석체크와 게임 안 일퀘는 다릅니다.** 원신 실시간 메모에서 `완료한 의뢰 = 전체 의뢰`, `추가 보상 수령 = True`인 경우에만 `[원신] 일퀘`를 체크하도록 했습니다. 서버 초기화 직후에는 20분간 판정하지 않고, 2회 2분 이상 간격을 두고 확인합니다.

1. 선택 패키지 설치: `python -m pip install genshin`
2. 현지/아시아 서버의 본인 원신 UID를 `config.json` → `hoyolab.genshin_uid`에 입력합니다. 아시아 서버에 해당하는지 직접 확인하세요.
3. **최초 한 번만** `python -m gametodo auth hoyolab`를 실행하여 개인 HoYoLAB 로그인 세션 쿠키를 기기에 입력합니다. 토큰은 공개하거나 전송하지 마세요.
4. `config.json`에서 `"hoyolab": {"enabled": true, "genshin_uid": "본인UID", "interval_minutes": 20, "daily_task_name": "[원신] 일퀘"}` 로 설정합니다.
5. `python -m gametodo hoyolab-once`로 점검하거나 `run_windows.bat` / Termux의 `run`으로 20분 간격 점검합니다.

**주의:** HoYoLAB의 비공식 조회 방식은 계정 보안 정책·인터페이스 변경·로그인 만료 등으로 중단될 수 있습니다. 게임 계정 인증정보는 프로젝트 개발자/ChatGPT에 공유할 필요가 없습니다. 로그인 자동연장이나 보안 우회 기능은 만들지 않았습니다. 실제 계정 성공 테스트를 완료한 것은 아니므로, 최초에는 Todoist 결과를 직접 확인하는 것이 안전합니다. 스타레일·젠존제는 읽을 수 있는 상태값이 있어도 보상 *수령* 확정 판정이 검증되지 않아 이번 버전에 자동완료하지 않습니다.

## 한국 서버/이벤트 수집 정책

- PickupCal에서 명시된 한국 서버 기간만 수집하며, 검증되지 않은 글로벌 Steam/중국 서버 일정을 한국 일정으로 추정하지 않습니다.
- 기본 활성 일정 수집: 원신, 붕괴: 스타레일, 젠레스 존 제로, 명조, 림버스 컴퍼니, **엔드필드**.
- 서버 일치 여부가 검증되지 않은 리버스 1999, 명일방주, 스텔라 소라, 컬러스위퍼는 기본 비활성화. **일정 출처가 검증되기 전까지 임의로 켜도 자동 등록되지 않습니다.**
- 오프라인 행사, 경품/댓글/굿즈 행사, 팬아트, 상점 할인, 방송 시청 드롭스, 외부 SNS 참여는 보수적으로 제외. 단어 기반 분류의 한계로 오탐/누락 가능성은 남습니다.
- 정기 콘텐츠 제외 목록(환상극, 나선 등)은 `gametodo/models.py`에서 관리합니다. **오프라인 이벤트/정기 콘텐츠는 신규 등록하지 않지만 기존 완료되지 않은 Todoist 항목을 자동 삭제하지는 않습니다.**
- 6시간마다 일정 확인(설정에서 조정 가능). HTTP ETag 캐시 지원. 기록 식별자에 고정 UUID 사용해 기기간 중복 생성 최소화.
- 단, Todoist 최종 사용자 직접 생성이나 이미 완료된 작업까지 100% 중복이 제거되는 것은 아닙니다.

## 테스트 / 소스 구조

```sh
python -m unittest discover -s tests -v
```

- `gametodo/games.py` 제목/라벨 매핑, 게임 분류
- `gametodo/models.py` 이벤트 구조 및 필터
- `gametodo/todoist.py` 생성/마감 변경/라벨 보정/완료/중복 방지
- `gametodo/credentials.py` 사용자 인증값 최초 1회 저장
- `gametodo/hoyolab.py` 원신 실시간 메모 선택 연동
- `gametodo/bridge.py` 휴대폰 로컬 플로팅용 읽기·완료 HTTP API
- `gametodo/pickupcal.py` 한국 서버 일정 추출
- `android/companion/app/src/main/java/com/example/gametodo/FloatingTodoOverlay.kt` 게임별 선택형 Todo UI
- `android/companion/app/src/main/java/com/example/gametodo/ScreenOCRService.kt` 게임 창 감지(기본 OCR 꺼짐)

***보안상 게임 프로세스 메모리 해킹, 패킷 복호화, 안티치트 우회, 자동 조작 기능은 포함하지 않습니다.***
