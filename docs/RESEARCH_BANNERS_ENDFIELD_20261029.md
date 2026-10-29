# 추가 가챠 출처와 엔드필드 주기 콘텐츠 조사

조사일: **2026-10-29 KST**. 공개 페이지/소스만 조회했다. 사용자 계정, 비밀번호, 쿠키, 토큰 또는 실계정 응답은 사용하지 않았다. 공개 구현의 타입에 필드가 있다는 사실과 한국/글로벌 Asia 계정의 실제 응답 확인은 구별한다. 이 문서는 조사 결과이며 새 개인 진행도 자동 완료를 구현했다는 뜻이 아니다.

## 추가 가챠: 찾을 수 있는 출처와 현재 한계

| 게임 | 확인한 출처 | 확인 결과 | 가능한 후속 작업 |
| --- | --- | --- | --- |
| 스텔라 소라 KR | [StellaSoraAPI 구현][stella-code], `https://api.ennead.cc/stella/banners?lang=KR` | CipherLink에 이미 KR 어댑터와 공개 응답 회귀 fixture가 있다. 이번 재조회는 HTTP 403이어서 최신 데이터를 다시 확인하지 못했다. 이를 서비스 전체 미지원으로 해석하지 않는다. | 기존 지원 상태를 표시하고 실패 시 다음 정상 응답까지 보류. CN/JP를 KR로 대체하지 않음. |
| 림버스 컴퍼니 | [제작사 Steam 뉴스 API][steam-api], [한국어/KST PickupCal][limbus-calendar] | Steam 공개 API 200, 최신 100건을 확인. 신규 인격 추출 공지는 본문이 YouTube 미리보기뿐인 경우가 많다. PickupCal에는 한국어 인격 이름과 시작/종료 시각, 공식 Steam 공지 링크가 있지만 중복·철자 차이도 있다. | 공식 이미지/공지에서 이름·종료 시각을 검증한 뒤 별도 림버스 파서와 중복 키 규칙 마련. 영상 공지 날짜에 임의로 2주를 더하지 않음. |
| 명일방주 KR | [ArknightsAssets 공개 게임 데이터][ark-data] | **KR 폴더의 실제 가챠 JSON 200**. 기간과 한글 이름을 가진 412개 풀 확인. 데이터 획득 구현이 공식 게임 자산 다운로드를 사용한다. | 확률 UP 캐릭터가 명시된 풀만 `character_table.json`과 결합해 수집 가능. 선택형·복귀형과 캐릭터 미확인 풀은 별도 처리해야 함. |
| 리버스: 1999 KR | [Kornblume 소스의 bannerData.ts][reverse-data] | 배너명/픽업 캐릭터 문자열 목록은 있지만 이 파일에 KR 서버 식별·시작/종료 기간이 없다. 조회한 공식 사이트 후보 경로도 404였다. | 이 자료만으로 KR 일정 수집을 구현할 근거는 부족. KR 공식 공지의 날짜와 지역을 확인하는 수집 경로가 더 필요함. |

### 명일방주: 현재 갱신되는 KR 게임 데이터

확인한 저장소 커밋: **`409bce70516f2420af61b1fc5680da60e448ab99`**. 2026-10-28에 갱신된 저장소다. [README][ark-readme]는 `arkprts`를 통한 게임 자산 다운로드임을 설명하며, [갱신 워크플로][ark-workflow]가 `python -m arkprts.assets . --server all`을 실행한다. 운영사 소유의 공개 문서 API가 아니라 **공식 클라이언트 데이터의 비공식 미러**라는 점은 유지한다. 공식 API 문서가 있는 서비스로 소개하면 안 된다.

- 공개 JSON: `https://raw.githubusercontent.com/ArknightsAssets/ArknightsGamedata/master/kr/gamedata/excel/gacha_table.json` (실제 200, 515,757바이트).
- 한글 이름 JSON: 같은 `kr/gamedata/excel/character_table.json` (실제 200, 약 20MB). 신규 어댑터에서는 캐시/변경 검사 없이 매번 내려받지 않는 편이 적합하다.
- `gachaPoolClient[]`: `gachaPoolId`, `openTime`, `endTime`, `gachaPoolName`, `gachaRuleType`, `dynMeta`.
- 기간은 **Unix 초**다. UTC로 해석한 뒤 KST로 변환해야 한다. 표시용 `gachaPoolSummary`만으로 연도/시각을 추정하지 않는다.
- `gachaRuleType == CLASSIC_DOUBLE`에서 `dynMeta.main6RarityCharId`, `dynMeta.sub6RarityCharId`는 구체적인 6성 ID다. 한글 캐릭터 테이블과 결합 가능하다.
- 실제 미래 예: `CLASSIC_DOUBLE_KR_42_0_2`는 **2026-11-03 04:00 ~ 2026-11-17 03:59:59 KST**, 두 ID의 한글명은 **사일라흐·유넥티스**다. 아직 시작하지 않았으므로 10월 29일 현재 가챠로 등록하면 안 된다.
- `SPECIAL`, `FESCLASSIC`, 복귀형은 `rarityPickCharDict`가 **선택 가능한 캐릭터 목록**일 수 있다. 전부 현재 확률 UP 캐릭터로 등록하면 오류다.
- 일부 `DOUBLE`의 `gachaPoolName`은 “다양한 전투에서 활약하는 강력한 오퍼레이터”이고 `dynMeta`는 null이다. 이런 자료에서 캐릭터 이름을 만들어내면 안 된다.
- 과거에 자주 참조하던 [Kengxxiao/ArknightsGameData_YoStar][ark-old]의 한국 폴더는 `ko_KR`이다. 이번 응답에서 가장 늦은 배너 종료가 2025-12-18 UTC여서 현재 일정 자료로는 오래됐다. 최신 미러의 `kr`와 예전 미러의 `ko_KR`를 혼동하지 않는다.

현재 CipherLink의 명일방주 게임 개인 데이터 조회 정책(PC opt-in, 23:59 KST 1회)과 이 **공개 배너 JSON**은 별개다. 배너를 위해 게임 계정에 로그인할 필요가 없다.

### 림버스: 단순 “지원 게임 목록” 이외의 파싱 문제

공식 뉴스 요청:

```text
https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=1973530&count=100&maxlength=0&format=json
```

`appnews.newsitems[]`의 `title`, `date`, `feedname`, `url`, `contents`를 확인했다. 2026.10.29 신규 인격 추출 공지의 `contents`는 `[previewyoutube=...][/previewyoutube]` 50글자뿐이었다. `date`는 게시일이며 가챠 종료일이 아니다. `l=koreana`를 붙인 재조회도 같은 영어 제목이었다. 한국어 지원을 이 파라미터만으로 보장하면 안 된다.

[PickupCal 림버스 페이지][limbus-calendar] 자체는 실제 HTTP 200이며 한국어 시간 범위와 제작사 Steam 링크가 있다. 기존 CipherLink `character_name()`은 인용부호나 별도 ` - `가 없는 림버스 제목을 버리기 때문에, 사이트에 항목이 있어도 결과가 0일 수 있다. 다만 파싱 허용만 넓히면 충분하지 않다. 925219/925220은 같은 2026-10-29 12:00 ~ 11-12 10:00의 히스클리프/홍루 인격을 철자·순서가 다르게 반복한다. `rarityPickCharDict`와 마찬가지로, 자료 형태를 그대로 새 Todoist 작업으로 바꾸기 전에 정규화·원문 검증이 필요하다.

## 엔드필드: 추가할 수 있는 주기 콘텐츠 후보

가장 직접적인 추가 후보는 **주간 임무**다. 공개 구현에는 `data.detail.weeklyMission.score`, `data.detail.weeklyMission.total`가 있다.

- [글로벌 SKPORT 명칭의 tracker 응답 계약][endfield-tracker-contract]에 `weeklyMission: { score: number; total: number }`가 정의되어 있다. 같은 프로젝트의 [fetcher][endfield-tracker-fetcher]는 응답 `data.detail`을 직접 읽는다. 다만 호스트는 설정값이고 예제는 placeholder이므로, 이 타입만으로 특정 글로벌 서버 응답이 반드시 필드를 제공한다고 확정할 수 없다.
- [EndUID 모델][endfield-model]에도 `WeeklyMission(score, total)`와 선택적 `CardDetail.weeklyMission`이 있다.
- [nonebot-plugin-skland 카드 모델][endfield-skland-card]도 `WeeklyMission(score, total)`를 정의한다.
- 현재 CipherLink는 카드 detail에서 `dailyMission.dailyActivation/maxDailyActivation`만 읽는다. 주간 데이터가 실제 응답에 있어도 표시하지 않는 구조다.
- 계정 토큰 없이 실계정 주간 수치를 확인할 수 없으므로 **현재 사용자 Asia 계정에 필드가 실제로 있는지 미검증**이다. 빠진 값을 `0/0`이나 완료로 만들면 안 된다.

| 추가 후보/표시명 | 공개 소스에서 확인한 필드 | 주기·판정 근거 | 사용자에게 제안 가능한 수준 |
| --- | --- | --- | --- |
| **주간 임무** | `detail.weeklyMission.score`, `.total` | 주간 점수형 모델. 갱신 요일·시각/회차 ID는 이 모델에 없음. | 사용자가 추가한 실제 제목 `[엔필] 주간퀘스트`와 매주 월요일 규칙을 사용한다. 실제 두 수치가 있고 현재 회차·예정일 검사를 통과할 때만 연동할 수 있다. |
| **그림자 이정표** — 원문 `影拓丰碑`, 게임 영문 `Umbral Monument` | `indieHard.indieHardGroups[].activityStartTs/activityEndTs/isInActivity`; `dungeonGroups[].normalDungeon.isPass`, `.hardDungeon.isPass`; 업적 정보 | 실제 시작/종료 시각과 일반/고난도 개별 클리어 필드 존재. CN 모델과 endpoint 소스에서 확인. | 한국어 클라이언트 이름은 공개 문자열에서 확인했다. 글로벌 Asia API 제공 여부는 미확인. “주간”으로 단정하지 말고 기간별 콘텐츠 후보로만 제안. |
| 시즌 도전 — 원문 `战争回响`, 소스 `war-echoes` | 주차 `startTs/endTs`, `stars`, `allPlusTasks`, 난이도별 `isPass`; 시즌 구조 | CN 공개 구현의 별도 `.../card/war-echoes` 경로와 주차/시즌 모델 존재. | 한국/글로벌 지원과 목표 별 수 미검증. 기간·별 수를 임의 확정해 자동 완료하지 않음. |
| **위기 협약** — 원문 `危机合约`, 소스 `crisis-contract` | `status.weeklyMission.count/total`, `indicatorMission`, `stageMission`, `startAtTs/endAtTs/gameplayEndAtTs` | 같은 이름의 `weeklyMission`이라도 카드의 주간 점수와 다른 별도 이벤트 임무 카운트다. | 한국어 클라이언트 이름은 공개 문자열에서 확인했다. 글로벌 실제 응답 확인 전에는 카드 주간 임무와 합치거나 같은 Todoist 작업으로 처리하지 않음. |
| 배틀패스 레벨 | `detail.bpSystem.curLevel/maxLevel` | 레벨 진행도일 뿐 일일/주간 보상 수령 증거가 아님. | 참고 진행도 표시 후보. 주간 퀘스트 완료로 쓰지 않음. |
| 스태미나·거점·우주선 상태 | `detail.dungeon.curStamina/maxStamina/maxTs`, 거점/우주선 모델 | 실시간 자원·생산 정보이며 특정 정기 임무 완료를 직접 뜻하지 않음. | 자원 알림이나 참고 정보 후보. 사용자가 추가할 주기 Todoist 자동 완료 근거와 구별. |

세부 도전 경로와 모델은 [EndUID API 상수][endfield-api]에서 확인했으며, 그 기본 호스트는 **`zonai.skland.com`(중국)** 이다. 이 경로를 `zonai.skport.com`으로 치환해 요청해 본 적은 없고 글로벌 성공도 주장하지 않는다. 후속 공개 클라이언트 문자열 대조로 그림자 이정표·위기 협약의 한국어 이름을 확인했다. `战争回响`는 한국어 이름을 확인하지 못해 번역명을 확정하지 않았다. 후속 사용자 확인으로 정확한 Todoist 제목은 **`[엔필] 주간퀘스트`**, 반복일은 **매주 월요일**이다. 이 요일은 API 모델에서 추정한 값이 아니라 사용자 제공 규칙이다. Asia 실제 수치는 해당 응답에 `score/total`이 있을 때만 읽는다.

## 재현 자료와 범위

- 공개 원문은 `/tmp/cipherlink-limbus-news.json`, `/tmp/pickupcal-limbus.html`, `/tmp/ark-current-kr-gacha.json`, `/tmp/ark-current-kr-characters.json`, `/tmp/endfield-model.py` 등에 보관했다. 계정 데이터가 아니다.
- 최소 KR 게임 데이터 fixture는 `/tmp/cipherlink-ark-kr-public-fixture.json`에 저장했다. 선택형/고정 캐릭터/범위 밖 기간의 차이를 검사하는 데 쓸 수 있다.
- 이 조사에서는 프로덕션 코드나 사용자 설정을 변경하지 않았다. 실계정 호출 및 Todoist 생성/완료도 실행하지 않았다.

[stella-code]: https://github.com/torikushiii/StellaSoraAPI/tree/cccc784c915fb7f0ae38ea2f617257120b8b4296
[steam-api]: https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=1973530&count=100&maxlength=0&format=json
[limbus-calendar]: https://www.pickupcal.com/games/limbus/
[ark-data]: https://github.com/ArknightsAssets/ArknightsGamedata/blob/409bce70516f2420af61b1fc5680da60e448ab99/kr/gamedata/excel/gacha_table.json
[ark-readme]: https://github.com/ArknightsAssets/ArknightsGamedata/blob/409bce70516f2420af61b1fc5680da60e448ab99/README.md
[ark-workflow]: https://github.com/ArknightsAssets/ArknightsGamedata/blob/409bce70516f2420af61b1fc5680da60e448ab99/.github/workflows/update.yml
[ark-old]: https://github.com/Kengxxiao/ArknightsGameData_YoStar/blob/57010cb5b2afea112cae57daa756b58676ba6850/ko_KR/gamedata/excel/gacha_table.json
[reverse-data]: https://github.com/windbow27/kornblume/blob/aaca2c53bf7ad6914fbf9739b07d263790877564/src/utils/bannerData.ts
[endfield-tracker-contract]: https://github.com/ivaqis/arknights-tracker/blob/d17e841ff6e54fb7eb5461593a7a8f937644d565/goyfield-backend/src/services/skportDetailFetcher/contracts/DetailData.ts
[endfield-tracker-fetcher]: https://github.com/ivaqis/arknights-tracker/blob/d17e841ff6e54fb7eb5461593a7a8f937644d565/goyfield-backend/src/services/skportDetailFetcher/SkportDetailFetcher.ts
[endfield-model]: https://github.com/Loping151/EndUID/blob/e08cd754217f85250eefe0b158db0362584f414b/EndUID/utils/api/model.py
[endfield-api]: https://github.com/Loping151/EndUID/blob/e08cd754217f85250eefe0b158db0362584f414b/EndUID/utils/api/api.py
[endfield-skland-card]: https://github.com/FrostN0v0/nonebot-plugin-skland/blob/29a0e428c7df4a522cdcdb784784d514e2f86f04/nonebot_plugin_skland/schemas/endfield/card.py


## 후속: 엔드필드 장기·시즌 콘텐츠의 주기 검증 범위

사용자가 `[엔필] 주간퀘스트`를 Todoist에 추가하고 **매주 월요일** 반복임을 확인했다. 이 항목은 기존 “추가 후보”에서 사용자 확정 연결 대상으로 바뀌었다. 나머지 콘텐츠의 회차 길이를 월요일 주간 규칙으로 통일하지 않는다.

추가 확인한 원문 접근:

- 공식 한국 사이트 `https://endfield.gryphline.com/ko-kr/` 및 `https://endfield.gryphline.com/news`는 현재 환경에서 **CONNECT 403**으로 원문에 접근하지 못했다. 사이트의 장애나 미지원이라는 뜻이 아니다.
- [lsy-404/EndfieldGameData](https://github.com/lsy-404/EndfieldGameData)는 2025-01 갱신 자료여서 2026년 글로벌/KR 시즌 길이의 근거로 쓰지 않았다.
- [3aKHP/EndFieldGameData](https://github.com/3aKHP/EndFieldGameData)의 공개 README는 게임 클라이언트에서 추출한 테이블과 CN/EN/JP/TC/KR 문자열을 배포한다고 설명한다. 다만 공개 core table 목록은 캐릭터·적·장비·재료이며 시즌 일정 테이블은 포함하지 않는다. README의 `v0.2/v0.3` 같은 SemVer는 도구/미러 버전이지 게임 콘텐츠의 시즌 번호나 반복 주기가 아니다.

| 콘텐츠 후보 | 이번에 확인한 기간·진행 근거 | 고정 반복 주기(일수) | 글로벌/KR 상태 |
| --- | --- | --- | --- |
| 카드 주간 임무 | `weeklyMission.score/total`; 사용자가 월요일 반복 확인 | 매주 월요일(사용자 제공) | 실제 Asia 필드가 있을 때 사용 |
| **그림자 이정표** (`indieHard`) | 각 그룹 `activityStartTs/activityEndTs`, `isInActivity`, 일반·고난도 `isPass` | **미확인** | CN 원본 구현 확인, 글로벌 실제 기간값 미확인 |
| `war-echoes` 시즌/주차 도전 | 주차 `startTs/endTs`, `stars/allPlusTasks`, 시즌 구조 | **미확인**; 주차 필드명만으로 7일을 확정하지 않음 | CN 구현 확인, 글로벌 실제 응답·기간 미확인 |
| **위기 협약** (`crisis-contract`) | `startAtTs/endAtTs/gameplayEndAtTs`, 주간·지표·스테이지 임무 카운트 | **미확인**; 이벤트의 플레이 종료와 전체 종료도 구별 | CN 구현 확인, 글로벌 실제 응답·기간 미확인 |
| 배틀패스 | `bpSystem.curLevel/maxLevel` | **미확인**; 레벨만으로 종료일/기간을 계산할 수 없음 | 카드 구조의 참고 진행도 |

안전한 구현 범위는 실제 글로벌 응답이 제공한 **개별 회차의 시작/종료 시각과 진행도**를 표시하는 것이다. 한 회차가 N일이라는 사실도 곧 “N일마다 반복한다”는 뜻은 아니다. 이번 조사로 14일·28일·장기 N일 규칙을 확인하지 못했으므로 숫자를 만들어 Todoist 반복을 등록하지 않는다. 실제 응답의 날짜창이 없는 콘텐츠는 `기간 확인 필요`로 남긴다. `isPass`는 통과 여부이며 보상 수령 여부와 같다고 가정하지 않는다.


### 추가 확인: 한국어 클라이언트 이름

[공개 게임 데이터 v0.3.0 릴리스](https://github.com/3aKHP/EndFieldGameData/releases/tag/v0.3.0)의 `endfield-tables.zip`을 실제 내려받아 동일 문자열 ID의 `i18n/CN.json`, `EN.json`, `KR.json`을 대조했다. 이 미러는 [클라이언트 추출 도구](https://github.com/Variante/endfield_research_kit)를 출처로 밝힌다. 운영사가 발행한 API 문서와 구별하되, 번역을 임의로 만들어낸 자료는 아니다.

| 문자열 ID | 중국어 원문 | 한국어 클라이언트 문자열 | 영문 클라이언트 문자열 |
| --- | --- | --- | --- |
| `-4585656025522540760` | 影拓丰碑 | **그림자 이정표** | Umbral Monument |
| `-6182699278298470459` | 危机合约 | **위기 협약** | Contingency Contract |

동일 자료에서 `战争回响`의 정식 한국어 이름은 찾지 못했다. 이 공개 번들에 없는 후속 콘텐츠일 수도 있으므로 “해당 게임에 없다”고 결론짓지 않는다.

`위기 협약 재점화 실험 작전` 개방 전 특별 보급 이벤트의 문자열에는 “모든 임무 진도 및 보상 획득 상태는 매일 서버 시간 04:00에 초기화”라는 규칙이 있다. 하지만 문맥이 **개방 전 기간 한정 보급 이벤트의 일일 임무**이므로 이 수치를 위기 협약 본 콘텐츠, 그림자 이정표 또는 장기 시즌의 반복 주기로 적용하면 안 된다. 해당 지역 서버 시간의 KST 변환도 이 문장만으로 정할 수 없다.

파일 SHA256: `f36942c203637611b0ae41bc7d5c50a912daea364ac289f8ab74b88cbf55c926`. 최소 문자열 증거는 `/tmp/endfield-kr-content-names.json`, 공개 원본은 `/tmp/endfield-public-tables.zip`에 보관했다. 확정된 새 고정 반복 일수는 없으며, **사용자 제공 월요일 주간 규칙 + 실제 응답의 콘텐츠별 시작/종료 날짜창**을 사용하는 접근이 적합하다.
