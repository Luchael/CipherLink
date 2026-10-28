# GameTodo Auto Sync v0.6.2: 로그인 단계별 검증판

> **테스트 범위**: 102개 오프라인 모의 응답 테스트 통과. 게임사의 실제 로그인·Windows Edge·실제 Todoist 계정 연결까지 성공했다는 뜻은 아닙니다. **이 문서의 상태 구분은 정확히 읽어주세요.**

## 가장 먼저 확인할 것

- **명조는 글로벌 서버**를 대상으로 합니다. 중국 KuroBBS 로그인은 글로벌 계정 연결이 아닙니다. 기존 중국 KuroBBS 기반 일일 조회는 **차단**했습니다. 글로벌 데이터 연동을 구현했다고 주장하지 않습니다.
- 인증 도중에는 **해당 회사가 제공하는 실제 로그인 웹사이트**에서 이메일, 비밀번호, 캡차, 이메일 코드 등을 사용자가 입력합니다. 앱은 인증코드나 비밀번호를 수집하지 않습니다.
- 인증된 토큰은 Windows 사용자 계정 DPAPI로 암호화하여 `~/.gametodo/secrets/`에 저장합니다. 최초 로그인 창은 Windows Edge의 독립 프로필(`~/.gametodo/browser_profiles/`)을 사용하며, 이 프로필에도 공식 사이트 로그인 쿠키가 남을 수 있습니다. 컴퓨터 계정을 안전하게 보호하세요.
- 자동으로 로그인할 수 없는 서버나 인증 검증이 실패하는 경우에는 저장·Todoist 자동 완료를 **진행하지 않습니다**.

## v0.6.2 실행 (Windows)

1. 기존 프로그램이 실행 중이면 종료합니다.
2. **v0.6.2 ZIP을 기존 설치 폴더에 덮어풉니다.** `config.json`과 `data/`는 삭제하지 마세요.
3. 같은 폴더의 CMD에서 최초 1회 필요한 패키지를 설치합니다.

   ```bat
   python -m pip install -r requirements-login.txt
   ```

   `genshin`, `arkprts`, `browser-cookie3`, `playwright` 등이 설치됩니다. `playwright`는 **이미 Windows에 있는 Edge**를 초기 로그인 창으로 실행합니다. 대부분의 Windows에서는 별도 브라우저 다운로드가 필요하지 않습니다. Edge가 설치되지 않았다면 실행이 실패합니다.

4. `run_windows.bat` 실행 (한국어 CMD: **CP949**, Python 실행 명령: **`python`**, `py -3` 미사용).
5. **Todoist 연결 시험**을 눌러 프로젝트 조회까지 성공했는지 확인합니다. 실패하면 Todoist 공식 OAuth 로그인을 새로 진행합니다.
6. **HoYoLAB 앱 내 로그인** 버튼을 누릅니다. 별도 Edge 창에서 로그인·캡차를 직접 완료합니다. 설치 화면에는 다음 로그가 표시됩니다.
   - `[1/4]` 로그인 창 열기
   - `[2/4]` 공식 페이지 로그인 및 세션 쿠키 확인
   - `[3/4]` 아시아 게임 UID를 서버에서 조회
   - `[4/4]` 성공한 경우에만 비밀값과 설정을 저장
7. **엔드필드 앱 내 로그인** 버튼은 별도로 실행합니다. 별도 Edge 창의 SKPORT 공식 로그인에서 인증코드를 직접 입력합니다.
   - `[1/5]` 공식 로그인 페이지
   - `[2/5]` `cookie_store/account_token`에서 인증 토큰 수령
   - `[3/5]` GRYPHLINE `/user/info/v1/basic`에서 토큰 검증
   - `[4/5]` SKPORT OAuth/서명 검증 및 바인딩된 아시아 캐릭터 조회
   - `[5/5]` 인증 성공 시에만 설정 저장
8. **명일방주 KR 이메일 인증**은 메일 전송·코드 확인·한국 서버 계정 데이터 조회·저장 순서로 동작합니다.
9. **계정 연결 상태 확인**에서 어떤 게임이 연결됐는지 확인한 다음 `accounts-status` 진단을 실행합니다.

   ```bat
   python -m gametodo accounts-status
   python -m gametodo doctor --config config.json
   ```

게임사가 자동화 접속을 거절하거나 지역 계정이 연결되어 있지 않으면 보안 우회 없이 오류 단계만 표시합니다.

## 게임별 상태 (이 버전)

| 게임 | 로그인 방식 | 현재 구현·검증 범위 |
|---|---|---|
| 원신 | HoYoLAB 자체 로그인 창 | 세션 감지 → Asia UID API 조회 → 설정 저장 코드, 모의 테스트 |
| 붕괴: 스타레일 | HoYoLAB 자체 로그인 창 | 위와 동일, 독립 UID 자동 발견, 모의 테스트 |
| 젠레스 존 제로 | HoYoLAB 자체 로그인 창 | 위와 동일, 독립 UID 자동 발견, 모의 테스트 |
| 명일방주: 엔드필드 | SKPORT 자체 로그인 창 | 토큰 발급 → 사용자 검증 → OAuth → 서명 → 아시아 바인딩, 모의 테스트 |
| 명일방주 한국 | Yostar 이메일 코드 | 로그인 후 실제 계정 `syncData` 확인을 거쳐 저장, 모의 테스트 |
| 명조 글로벌 | 글로벌 게임 서버 | **개인 일퀘 API 미확인.** 중국 KuroBBS 조회 차단·자동 체크 제외 |
| 리버스: 1999 / 림버스 컴퍼니 / 스텔라 소라 | 외부 데이터 API 확인 안 됨 | 자동 감지 제외; Todoist 기존 작업 유지 |

가챠 일정 수집과 종료 시점 Todoist 자동 완료, 서버 초기화 시간/반복일 처리 로직은 이전 버전에서 유지됩니다. **가챠가 보이지 않는 문제는 로그인 문제와 다를 수 있습니다.** 먼저 `현재 가챠 미리보기`에서 출처 오류가 있는지 확인하세요.

## 수정한 핵심 파일

- `gametodo/embedded_login.py` (**신규**): 단계별 자체 로그인 창, 별도 프로필, 로그인 쿠키·토큰 검증, 성공 후 저장. 한국어 주석 포함
- `gametodo/skport.py`: 갱신 응답 `data.token` 필드도 서명 키로 읽도록 오류 수정
- `gametodo/arknights.py`: 문서화된 `YostarAuth.login_with_token` + `Client(auth=...)` 순서로 한국 서버 조회
- `gametodo/account_sources.py`: 글로벌 명조를 중국 API로 잘못 조회하는 경로 차단
- `gametodo/account_setup.py`: 중국 KuroBBS를 글로벌 명조 로그인으로 표시하지 않음
- `gametodo/settings.py`: 과거 설정의 글로벌 명조 KuroBBS 자동 조회도 비활성화
- `gametodo/gui.py`: 자체 로그인 버튼·단계별 로그·명일방주 계정 검증 추가
- `gametodo/diagnostics.py`: 민감정보를 포함하지 않는 단계별 오류
- `tests/test_v062.py`: 12개 로그인·글로벌 서버 혼동 방지 테스트

## 오류 발생 시 필요한 정보

프로그램 로그에서 `오류` 메시지의 **단계명**(`[2/5]`, `[4/5]` 등)과 에러 종류만 보내주세요. **계정 비밀번호, 인증코드, 쿠키, Todoist 토큰, SKPORT ACCOUNT_TOKEN은 절대 보내지 마세요.**

## 한계와 안전성

- **아직 실제 개인 계정으로 동작 검증하지 않았습니다.** 공식 계정 인증 정책이 변하면 최초 로그인 창 또는 실시간 메모 API 연동이 실패할 수 있습니다.
- 앱이 사용하는 Playwright는 공식 로그인 페이지를 보여주기만 하며, 안티치트·DRM·게임 내 패킷 암호화 우회는 하지 않습니다.
- Playwright의 로그인 창은 초기 인증 중에만 실행됩니다. 일반적인 자동 데이터 동기화는 기존처럼 낮은 빈도의 HTTP 요청만 사용합니다.
- 개발자가 배포 시 GUI/EXE를 만들 수 있도록 `build_windows.bat`를 유지했습니다. **EXE와 Android APK를 실제로 빌드해서 검증한 것은 아닙니다.**

## 참고 소스

- HoYoLAB/`genshin.py`: https://seria.is-a.dev/genshin.py/authentication/
- SKPORT/Gryphline 커뮤니티 API 문서: https://github.com/AixLnyt/skport-api-docs
- SKPORT 토큰 웹 로그인 사례: https://github.com/AureliusGemini/EndField-AutoDaily
- ArkPRTS: https://github.com/ashleney/ArkPRTS
- KuroBBS 중국 위젯 명세: https://github.com/TomyJan/Kuro-API-Collection/blob/master/API/gamer/widget/game3/getData.md
- Todoist OAuth: https://developer.todoist.com/api/v1/
