# Codex 에이전트 작업 지침

이 저장소는 게임 Todoist 자동화 앱 **CipherLink**이다. 반드시 `CODEX_START_HERE.md`를 먼저 읽고 실제 코드를 확인한다.

## 작업 방식

- 사용자가 명시적으로 요청한 범위만 변경; 임의 리라이트/기능 삭제 금지.
- 행동을 바꾸는 수정에는 `pc/tests/` 또는 Android 순수 Kotlin 테스트를 추가한다. 파일을 고친 뒤 해당 테스트와 PC 전체 테스트를 실행.
- API 스펙은 변할 수 있다. 확인되지 않은 엔드포인트/필드/시즌 점수는 추정치로 작성하거나 자동 완료에 쓰지 않는다.
- 비식별 정보만 진단으로 출력한다. 사용자 인증 비밀, 개인정보 식별값, 주소, 쿠키, URL 인증 querystring 등을 콘솔/로그/테스트 아티팩트에 남기지 않는다.
- Windows GUI 배포는 사용자가 Python/pip를 설치하지 않아도 실행되게 패키징한다. 빌드 스크립트에서만 Python/pip 사용 가능.
- Windows/Android 동시 동기화와 Todoist idempotency(중복 방지), 회차 오판 방지를 항상 확인한다.
- Android 앱 서명, 패키지 ID, Keystore, PC 저장 경로와 UUID 표식, 사용자 데이터베이스 호환성 유지.
- 게임 로그인과 게임 접속 방해 가능성을 숨기지 않는다. 명일방주는 opt-in·PC에서 23:59 1회 제한; 모바일 자동 로그인은 기본적으로 꺼짐.
- 로컬에서 재현되지 않는 실제 게임 API 문제는 성공으로 보고하지 않고 미검증/요청 필요 상태로 표기한다.
- 사용자에게 제공할 결과: 변경 파일/기능, 테스트 결과, 아직 미검증인 사항, 단순한 설치·실행 방법, 비밀정보 없는 진단 방법.

## 기준 명령

```powershell
cd pc
python -m unittest discover -s tests -q
python -m gametodo gui
```

Android: `android/` Gradle 프로젝트, JDK17/SDK35. 브라우저 인증, 게임사 API와 Todoist 갱신은 가능하면 모의 HTTP로 테스트한다.
