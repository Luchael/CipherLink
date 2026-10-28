# 미해결 이슈 / 재현 / 우선순위

## P0: Windows HoYoLAB 로그인 성공 후 `[3/4 계정 확인]` 실패

- 사용자 보고: 공식 HoYoLAB 로그인까지 성공하지만 `HoYoLAB 계정 API 조회 실패: 세션 권한/게임 공개 설정/라이브러리 버전을 확인해주세요` 출력.
- PC v0.10.5 수정: `embedded_login.py`에서 인증 쿠키+계정 식별자 준비까지 대기, 기본 `genshin.py` 실패 시 글로벌 UID API 대체 경로 시험, 원신/스타레일/젠존제 캐릭터 독립 조회.
- **아직 입증하지 못한 것**: 실제 계정으로 UID/Asia 서버 역할 조회가 성공하는지, 오류가 쿠키 부족인지 라이브러리 버전인지 응답 스키마인지.
- 재현: 계정 연결 → HoYoLAB 공식 브라우저 로그인 → 단계 3/4. 로그에는 URL의 인증 쿼리/쿠키/UID를 넣지 말 것.
- 조사 파일: `pc/gametodo/embedded_login.py`(`extract_hoyolab_cookie`, `_discover_hoyolab_accounts`, 연결 단계), `hoyolab.py`, `hoyolab_login.py`, `account_setup.py`, `requirements-login.txt`.
- 기대: 유효한 글로벌 Asia 캐릭터 선택; 0 캐릭터/권한 없음/로그인 미완료/HTTP 오류를 구분. 여러 게임/계정 선택 가능. 반복 로그인 없이 기존 자격 증명 보존.

## P0: Windows 엔드필드 로그인 성공 후 `[3/5 코튼 검증]` 실패

- 사용자 보고: 공식 로그인 성공 뒤 `GRYPHLINE 계정 조회 실패: 토큰 만료 또는 API 사양 변경`.
- PC v0.10.5: `validate_gryphline_basic()`가 `code/status`, `data.basicUser`, `data.user` 등 응답 차이를 수용하며 기본 정보가 애매할 때 OAuth/Asia 캐릭터 바인딩으로 검증 계속. 명시적 401/403/인증 거부는 차단.
- 검증 필요: 실제 GRYPHLINE/SKPORT 최신 계정 응답과 OAuth cred/salt/HMAC/아시아 계정 조회 흐름.
- 조사 파일: `pc/gametodo/embedded_login.py`, `skport.py`, `account_setup.py`.
- 기대: 의미 있는 오류 단계, 유효 계정 연결 확인, 세션 토큰 노출 방지, 기존 로그인 보존.

## P1: 명조 글로벌 가챠 일정 수집

- 사용자 오류: `가챠 수집 실패: wuthering(입력 설정 또는 응답 형식 오류 (ValueError).)`.
- v0.10.5 조사: `pc/gametodo/banners.py`의 `UnsupportedBannerSource`로 검증되지 않은 글로벌 Asia 일정 수집 의도적 차단. `banner_sync.py`는 이제 일반 ValueError 대신 미지원 출처를 구분.
- **미해결**: 실제 글로벌 Asia 캐릭터 픽업 시작/종료 시각을 신뢰할 수 있는 안정된 출처 확보 및 기계 판독.
- 중국 KuroBBS/한국 팬 캘린더를 검증 없이 글로벌 서버 일정으로 바꾸지 말 것. 가챠 기록 URL(뽑기 내역)과 **진행 중 배너 일정**은 서로 다른 정보임.
- 기대: 출처/서버/시작·종료일 검증 및 소스 신뢰도 표시. 출처 없으면 Todoist 잘못된 작업 자동 생성 금지.

## P1: Windows 실행 파일 배포 UX

- 현재 `pc/build_windows.bat`는 PyInstaller `--onefile --windowed --icon` 기반 소스 빌드 스크립트이지만 실제 Windows EXE/설치 테스트는 미완료.
- 목표: 최종 사용자는 `CipherLink.exe` 또는 `CipherLink Setup.exe` 하나만 실행한 후 앱 내에서 최초 계정 로그인. Python/pip/수동 패키지 설치 불필요. 일반 사용자 권한 설치. 업데이트 후 설정/토큰 보존.
- GUI는 `pc/gametodo/gui.py`의 Tkinter 사이드바 대시보드 기반. `reference_ui/`는 v0.10.5 실행 화면 캡처. 접근성, 스크롤, 작은 창, 오류 안내, 상태 표시 개선.
- 의존성: `requirements-login.txt`, `requirements-endgame.txt`, OCR 선택 패키지 `requirements-pc.txt`. Playwright 관련 배포 및 Edge 실행 환경을 실제 Windows에서 검증해야 함.

## P2: Android 호환 / 명조·명일방주

- Android 소스 v0.10.3 기준. 개별 게임 조회 스위치(작동하는 게임 위주), 기존 작은 원형 게임 아이콘 플로팅, 회차 필터, 15분 등 주기 설정 유지.
- Android 명일방주 KR/EN/JP 개인 데이터 자동 로그인은 구현/실기기 검증 전이며 세션 충돌 가능성 때문에 비활성. PC 쪽에만 사용자가 명시적으로 활성화한 23:59 KST 1회 시도가 있음.
- 명조 글로벌 개인 일일/엔드 점수 API 미검증; 자동 완료 연동을 임의로 활성화하지 말 것.
- 원신/스타레일/젠존제 엔드 콘텐츠는 이미 실제 비식별 진단 데이터로 필드 구조/회차를 상당 부분 검증했지만 게임 API 변경 가능. `docs/API_AND_CYCLE_NOTES.md` 참조.

## 지금 Codex가 사용자에게 요청하면 좋은 안전한 증거

1. 앱 자체의 단계별 **HTTP status/retcode, 응답 필드 이름, 로그인 쿠키 이름만** 표시하는 비식별 진단.
2. 로컬 테스트에서 재현된 완전한 예외 **유형·안전한 문구·스택 위치**(인증값과 URL 쿼리 제거).
3. 가능하다면 새로운 빌드를 사용자 기기에서 실행해 테스트한 결과. 사용자는 비밀번호·쿠키·ACCOUNT_TOKEN을 공유하지 않아야 함.
