# v0.6.2 변경 이력

- Windows 내장 Edge 프로필을 사용한 HoYoLAB·SKPORT 자체 로그인 기능 추가 (선택 의존성 Playwright)
- `API 키/쿠키 수동 입력 없이` 공식 로그인창에서 사용자 인증; 성공 단계마다 안전한 메시지 표시
- SKPORT refresh 결과의 `data.token` 사용 버그 수정
- ArkPRTS KR `Client.from_token` 대신 README 인증 절차(`YostarAuth.login_with_token`) 사용
- 명일방주 KR 인증코드 확인 후 한국 서버 `syncData` 조회 성공 시에만 로그인 저장
- 글로벌 명조와 중국 KuroBBS의 API/계정체계를 구분하고 중국 KuroBBS 계정 자동 조회 비활성화
- 12개의 모의 로그인·필터·시크릿 저장 순서·회귀 테스트 추가 (총 102개 통과)
- 로그인 비밀과 API 실패 원문을 숨기고 실패 단계만 표시
- 기존 가챠 동기화·서버 초기화·일일/주간 자동 완료 로직 유지

**한계**: 실계정 인증, Windows Edge GUI 및 EXE 실제 실행 검증은 이 환경에서 완료되지 않음. 글로벌 명조 개인 진행도 API는 검증된 출처 없음.
