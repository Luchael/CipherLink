# 사이퍼링크 PC v0.10.5 — 로그인 진단 및 화면 재구성

기존 PC v0.10.4 기반 업데이트입니다. Android v0.10.3에는 변경 사항이 없습니다.

## 수정 내역

- **HoYoLAB**: 별도 Edge 로그인 프로필이 `ltoken_v2`만 수신한 순간 바로 닫혀 UID API 호출이 실패하던 경로 개선. 계정 ID/세션 쿠키 조합이 준비돼야 다음 단계로 진행. `genshin.py` 조회가 실패하거나 API를 지원하지 않는 경우 글로벌 게임 계정 목록의 읽기 전용 엔드포인트를 대체 경로로 시험. 원신, 스타레일, 젠레스 역할을 독립 조회. 비밀번호·쿠키 원문은 오류 화면에 출력하지 않음.
- **SKPORT**: GRYPHLINE `/user/info/v1/basic`의 `code/status`, `data.basicUser`, `data.user` 등의 차이를 수용. 기본 정보 API만으로 유효성을 판정할 수 없다면 실제 OAuth→cred→아시아 서버 캐릭터 바인딩으로 검증. 인증 거부(401/403 또는 명시적 실패 코드)는 계속 차단.
- **명조 가챠**: 글로벌 Asia 가챠의 검증된 출처가 없어 의도적으로 차단한 코드가 일반 `ValueError`로 표시되던 문제 수정. 이제 `출처 미검증으로 건너뜀`으로 별도 표시. 잘못된 한국 서버 날짜를 글로벌 계정 작업에 추가하지 않음. **명조 자동 수집이 성공한 것은 아닙니다**.
- **UI**: 사이드 메뉴(대시보드, 계정 연결, 동기화, 설정, 진단·로그), 넓은 카드, 개선된 배색과 상태 표시, 계정 연결 페이지 세로 스크롤, 오류 발생 시 로그 페이지로 이동. 모바일 아이콘 유지. 새 GUI 라이브러리 설치 필요 없음.
- **최초 실행**: `config.example.json`에 있던 `poll_hours=0.25`(15분)을 설정 검증에서 오류로 처리하던 초기 실행 버그 수정.

## 설치

1. 기존 `~/.gametodo` 및 PC 프로젝트 `config.json`, `data` 폴더를 백업합니다.
2. 소스 ZIP의 `pc` 폴더를 기존 프로젝트에 덮어씁니다. 앱 이름/설정 저장 경로는 이전과 동일합니다.
3. `pc/run_windows.bat` 실행. `계정 연결` 화면에서 HoYoLAB·엔드필드 버튼으로 공식 로그인합니다.
4. 실패 시 `진단·로그`에 표시된 단계와 HTTP 코드 **숫자만** 공유해 주세요. 비밀번호·쿠키·ACCOUNT_TOKEN은 공유하지 마세요.

## 검증 및 제약

- Python unittest 168개 통과. Tkinter 가상 디스플레이에서 대시보드·계정 화면 직접 구동 후 이미지 캡처.
- **실제 HoYoLAB 및 GRYPHLINE 계정으로 호출을 검증하지 못했습니다.** 인증 제공자의 API는 변동될 수 있습니다.
- Windows EXE/설치 프로그램 빌드는 포함되지 않았습니다. 소스 ZIP을 제공합니다.
- 명조 글로벌 가챠 일정은 아직 검증된 신뢰 가능한 제공처가 없어 수집 보류입니다. 한국 서버 일정으로 대체 등록하지 않습니다.

## 공개 구현 참조

- genshin.py 공식 문서: https://seria.is-a.dev/genshin.py/authentication/
- HoYoLAB 바인딩 API: https://github.com/seriaati/genshin.py
- GRYPHLINE/SKPORT 비공식 명세: https://github.com/AixLnyt/skport-api-docs
- CustomTkinter UI 디자인 참조: https://github.com/TomSchimansky/CustomTkinter (실제 프로젝트는 추가 라이브러리 없이 Tkinter 유지)
