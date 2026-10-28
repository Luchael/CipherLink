# 2026-10-28 개발 재개 기록

## 인수·보안·기준선

- 사용자가 제공한 ZIP 172개 파일을 기존 빈 checkout에 경로 검증 후 추출했다. 원본은 `65bb974`로 GitHub `main`에 업로드했다.
- `CODEX_START_HERE.md`, `AGENTS.md`, `OPEN_ISSUES.md`, `PRODUCT_AND_TODOIST.md`와 실제 소스·매핑을 대조했다. PC 인수 기준 0.10.5, Android 0.10.3-alpha.
- `cd pc && python3 -m unittest discover -s tests -q`: 168 tests, OK. PC/Android Todoist 매핑·엔드 목표 파일 동일, 34개 = 자동15/조건부3/수동16.
- ZIP 파일명·내용 패턴·참고 화면을 검사했으며 사용자 config/DB/log/서명키와 실제 인증값으로 의심되는 패턴을 발견하지 못했다. `.gitignore`의 인증·로컬 데이터 제외도 확인했다. 이는 모든 형태의 비밀 부재를 보장하는 검사는 아니다.

## PC 로그인: 가설과 확인된 결함

처음 순위는 ① 성공 UID를 cleanup 단계에서 폐기 ② 로그인 토큰과 대체 API의 인증 계열 불일치 ③ 기본정보/OAuth 응답의 상태·스키마 오분류였다. 실계정 원인 전체와 아래 재현된 결함을 구분한다.

### HoYoLAB

- 설치한 `genshin==1.7.31` 및 공개 upstream에는 `Client.close()`가 없다. 기존 `finally: await client.close()`가 성공 UID를 폐기하고 fallback으로 이동하는 문제를 모의 클라이언트로 재현했다.
- `ltoken`용 `getUserGameRolesByCookie`와 `cookie_token`용 `getUserGameRolesByCookieToken`을 혼용했다. 대체 API도 동일 버전 토큰·계정 ID 이름쌍이 있을 때만 호출하며, ltoken 경로의 DS 헤더는 라이브러리의 정상 helper를 사용한다.
- `GenshinAccount`가 API `region`을 `.server`로 노출하는데 기존 선택기는 `.region`만 읽었다. 정확한 Asia 서버 식별자를 검증하고 성공한 빈 계정 목록은 인증 실패로 바꾸지 않는다.
- `hoyo_client.py` 호환 경계를 추가했다. 나머지 진행도/진단의 동일 cleanup 호출만 교체했으며 점수·회차 판정은 바꾸지 않았다.
- 최초 cleanup/server 두 회귀가 red였고, 빈 목록 회귀도 red를 확인했다. 새 HoYoLAB 13개 green, 설치한 실제 Client/모델에 HTTP만 대체한 검사도 포함한다.

공개 근거: [genshin.py BaseClient](https://github.com/seriaati/genshin.py/blob/2c513b398008b5b8c2d6e98ec156a8b7abe70996/genshin/client/components/base.py), [계정 모델](https://github.com/seriaati/genshin.py/blob/2c513b398008b5b8c2d6e98ec156a8b7abe70996/genshin/models/hoyolab/record.py), [라우트](https://github.com/seriaati/genshin.py/blob/2c513b398008b5b8c2d6e98ec156a8b7abe70996/genshin/client/routes.py).

### GRYPHLINE / SKPORT

- basic Bearer 요청, appCode, OAuth→cred→refresh 및 binding/detail HMAC은 공개 문서와 일치했다. 엔드포인트·서명식을 추측해서 바꾸지 않았다.
- 최상위 숫자 문자열 `code`를 OAuth 승인 코드로 사용하거나, nonzero 상태와 `data:{}`를 성공으로 통과시키는 문제를 모의 HTTP로 재현했다. OAuth는 `data.code`만 사용하고 실패 envelope는 단계에서 즉시 중단한다.
- 기본정보의 알 수 없는 status가 명시적 비영 code를 가리지 않도록 거부 우선순위를 보완했다. 비영 상태를 곧바로 “토큰 만료”라고 단정하지 않는다. HTTP401/403은 중단하고 기타 보조 API 실패는 실제 OAuth·바인딩 성공을 요구한다.
- 잘못된 서버명 America/Europe 등을 `serverId=2`만으로 Asia로 선택하지 않는다.
- 신규 SKPORT 계약10개, 진단4개, 브라우저 경계 로그인 흐름6개가 통과했다. 실패 시 기존 설정·credential 미저장, HMAC 고정 벡터, 정상/빈/오류 스키마와 비밀 비노출을 검사한다.

공개 근거: [비공식 skport-api-docs](https://github.com/AixLnyt/skport-api-docs/blob/54fd90ccca6b2e1de4fc9827b4bc3aaf35872cd6/README_EN.md). 공개 문서와 모의 테스트는 실계정 인증 성공의 증거가 아니다.

## 비식별 재검증 방법

수정된 앱에서 계정 연결 → 공식 브라우저 로그인 → 실패한 단계의 진단을 확인한다. 공유할 내용은 단계 번호, HTTP 숫자, 정수 retcode/code/status, `schema=`의 고정 필드 이름·타입뿐이다. 닉네임·UID·전체 로그·네트워크 캡처·인증 URL·쿠키·토큰은 공유하지 않는다. `token:str`, `uid:str` 등은 값이 아닌 필드 이름과 타입이다.

`login_diagnostics.py`는 고정 키 목록만 표시하고 모든 응답 문자열·식별자 값·임의 키·예외 원문을 버린다. HTTP 성공 상태는 HttpClient가 실제 관찰한 경우에만 표시한다. 전적용 `safe_diagnostic`은 점수·날짜도 포함하므로 로그인 진단과 구분하고 공유 전 직접 검토한다.

실계정 HoYoLAB/GRYPHLINE/SKPORT 로그인은 미검증이다. 실패 원인 중 인증 만료·권한·공개 설정·실제 API 변경 가능성은 남아 있다.

## 추가 요구사항과 모바일 운영

- 한국어 UI와 KST 날짜 표시. 한국 서버가 따로 있으면 KR, 없으면 글로벌 서비스의 Asia를 선택한다. 서버 구분은 실제 서비스 근거를 따른다.
- Android가 주 실행 기기이며 PC가 계속 켜져 있지 않아도 동작해야 한다. 기존 SyncWorker는 가챠와 계정 조회를 독립 수행하며 WorkManager는 정확한 시각·무중단 실행을 보장하지 않는다.
- 기기 모델을 고정하지 않는다. Android17 포함 이후 기기와 Play/갤럭시/원스토어 앱 차이는 기존 “설치 앱 연결”로 지정한다. 검증되지 않은 패키지 ID를 추가하지 않는다.
- 네 화면의 일일·주간·월간·N일 주기와 기존 한국어 제목/하위 작업을 보존한다. 후속 사용자 선택에 따라 `[색지뢰] 일퀘`를 수동 체크 전용으로 다시 포함한다(현재 전체35개 = 자동15/조건부3/수동17). 자동 감지·가챠 조회 대상에는 넣지 않는다.
- 사용자는 중국 명조 가챠 일정 사용을 허용했다. 이는 중국 개인 계정 API를 글로벌 개인 진행도로 쓰는 허용이 아니다.

## 추가 게임의 조사 경계

| 게임 | 가챠 후보 | 개인 진행도 |
| --- | --- | --- |
| 명조 | 기존 한국어/KST PickupCal 경로, 중국 공식 Wiki 공개 API 후보 | KuroNet의 BBS overseas URL은 비어 있다. 글로벌 wish history는 뽑기 이력이며 일퀘·탑·폐허·매트릭스 증거가 아니다. 자동 완료 보류. |
| 림버스 | 기존 PickupCal, Valve 공식 뉴스 후보 | 찾은 공개 프로젝트는 정적 캐릭터 DB 또는 IL2CPP export 도구. 현재 회차의 엔케팔린 소모/거던 점수 API를 확보하지 못했다. |
| 리버스1999 | 한국 공식 공지 추가 확인 필요 | M9A는 이미지 인식+게임 조작 자동화, Kornblume는 계획/정적DB·뽑기 추적. 읽기 전용 개인 임무 API 근거가 아니다. |
| 스텔라소라 | StellaSoraAPI의 `lang=KR` 배너 후보 | 해당 공개 API는 정적DB/가챠/뉴스이며 개인 임무·점수 API가 아니다. |

확인한 공개 소스: [KuroNet](https://github.com/PaiGramTeam/KuroNet/tree/401c8eba5345acc51b8ef38b2d73fb4d08f7c427), [GachaClock 명조 파서](https://github.com/iaoongin/GachaClock/blob/99d16c10bfeeb5f885e9cb42861c50f993f3a746/spider/spider/spiders/ww.py), [StellaSoraAPI](https://github.com/torikushiii/StellaSoraAPI/tree/cccc784c915fb7f0ae38ea2f617257120b8b4296), [M9A](https://github.com/MAA1999/M9A), [Kornblume](https://github.com/windbow27/kornblume).

이 조사로 API가 존재하지 않는다고 단정하지 않는다. 계정/서버·현재 점수/목표·시즌 기간·서버시각·신선도가 확인되는 응답 근거를 확보해야 자동 완료를 추가할 수 있다. 현재 네트워크 정책은 공식 뉴스·Wiki·외부 API·검색을 CONNECT403으로 차단했다. 필요한 도메인은 환경 설정 초안에 추가했지만 사용자 저장/게시 전에는 live 수집 성공을 주장할 수 없다.

## 실행·배포 상태

- PC: Python3.12 격리환경에 로그인·전적 의존성 설치, `pip check`와 CLI help 통과. 사용하지 않는 `rsa` extra를 제거했다. 독립 검토에서 HTTP JSON/gzip/캐시/재시도5건도 통과했다.
- Windows: 모듈·리소스·PC 회귀 사전검사, 비대화형 빌드와 SHA256을 추가했다. GitHub 수동 Windows EXE workflow와 [배포 안내](WINDOWS_DISTRIBUTION.md)를 제공한다. 실제 EXE 빌드/실행·설치/업데이트는 미검증이다.
- Android: 공식 체크섬을 검증한 JDK17.0.12·Gradle8.10.2·SDK35로 첫 `:app:assembleDebug` 전체빌드 성공(33 tasks). 후속 변경은 최종 통합 결과를 별도 기록한다. Android17 실기기·로그인·백그라운드·기존 서명 업데이트는 미검증이다.
- 새 디버그 APK는 테스트용 새 서명을 사용한다. 기존 앱을 삭제하거나 저장소/키를 전달해서 업데이트 문제를 해결하지 않는다. 로그인·Keystore 보존에는 기존 배포 서명과의 호환이 필요하다.

## 모바일 할 일 UI 및 배너 변경

- 35개 제목을 공통 JSON에서 읽어 일일/주간/월간/N일 주기와 자동/조건부/수동 이유를 한국어로 표시한다. 자동 감지 표시는 실계정 성공을 뜻하지 않으며 연결·점수·현재 회차 검증을 요구한다.
- Android 플로팅은 접두사 없는 하위 작업에도 부모의 게임 소속과 누락된 예정일을 상속한다. 명시적 자식 날짜는 보존하고 순환/누락부모/프로젝트 불명·불일치/이벤트 조상은 거부한다. 완료 직전 최신 계층과 표시 회차를 비교한다. 자동 완료 매핑·UUID는 변경하지 않았다. 기존 수동 REST 완료의 PC 자동완료와의 원자적 race까지 해결한 변경은 아니다.
- 사용자 승인에 따라 명조 전용 무조건 차단을 제거하고 기존 한국어/KST PickupCal 파서에 연결했다. 미지원 출처·기간/시간대 누락·만료·무기 배너는 보류한다. 직접 중국 Wiki 수집은 아직 미구현이다. 리버스/스텔라 개인 진행도와 가챠 신규 live 출처는 미검증 상태로 남는다.

## 최종 통합 검증

- 저장할 설치 스크립트를 현재 환경에서 그대로 재실행: 의존성 설치/갱신, `pip check`, PC `python -m unittest discover -s tests -q` **224개 모두 통과**, CLI help, 체크섬 검증된 Android 도구 재사용 모두 성공. skipped/expected failure 없음.
- Kotlin 회귀 프로그램 **15개 모두 컴파일·실행 통과**(기존12개 + 하위작업 + 지원현황/비식별오류 + 배너). JSON/네트워크 등의 stub을 사용하는 오프라인 검사이며 실기기 UI 검사가 아님. 배너는 정상1·보류11 사례 및 PC와 동일키를 확인.
- Android 최종 assets/소스를 포함한 전체 APK 빌드·서명 무결성 확인 결과와 산출물 정보는 빌드 기록을 따른다. 기존 서명 호환과 실제 기기 동작은 미검증.
- 명조·림버스 live 일정, 리버스/스텔라 신규 일정 출처, 추가 게임 개인 진행도 API 조사는 네트워크 설정 반영과 실제 공식 응답 근거가 남아 있다. 이 기능들이 모두 자동 동작한다고 보고하지 않는다.
- 클라우드 install_script/start_skill 및 조사 도메인 허용 목록을 초안에 저장했다. 초안 저장은 적용/게시/새 태스크 복원 검증과 다르다.
