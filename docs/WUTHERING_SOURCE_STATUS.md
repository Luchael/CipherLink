# 명조 글로벌 Asia 가챠 출처 검증 상태

2026-10-28 사용자가 **글로벌/CN 가챠 일정이 같으므로 CN 일정도 사용해도 된다**고 명시했습니다. 이는 가챠 출처에 대한 정책이며, 글로벌 개인 진행도에 중국 계정 API를 연결하는 허용이 아닙니다.

PC `pc/gametodo/banners.py`와 Android `BannerSource.kt`에서 명조만의 무조건 차단을 제거했습니다. 다른 게임과 같은 한국어 PickupCal 경로 `https://www.pickupcal.com/games/wuthering/`를 사용합니다. 기존 한국어/KST 근거, 개별 카드의 지역 표시, 정확한 시작·종료 시각, 현재 진행 여부, 캐릭터 픽업·무기 제외 조건은 유지합니다. 날짜나 이름을 추측하지 않으며, PC/Android 공통 배너 키도 바꾸지 않았습니다. PC는 `source=pickupcal` 외의 출처를 계속 `UnsupportedBannerSource`로 분류합니다.

**현재 PickupCal 명조 경로의 실제 응답과 최신 일정은 검증하지 못했습니다.** 해당 도메인은 현재 클라우드 프록시에서 CONNECT `403 Forbidden`을 반환했습니다. 한국어 합성 페이지 fixture로 파서 경로와 잘못된 일정의 등록 보류를 확인했으며, 라이브 수집이 성공했다는 의미가 아닙니다. 실제 페이지가 없거나 구조가 다르면 가챠를 생성하지 않습니다.

글로벌 공식 사이트의 뉴스 경로 후보 `https://wutheringwaves.kurogames.com/en/main/news`를 읽기 전용으로 확인하려 했으나, 현재 클라우드 네트워크 프록시가 CONNECT `403 Forbidden`을 반환했습니다. 해당 도메인은 현재 허용 목록에 없었습니다. 따라서 페이지 내용, 경로의 유효성, 기계 판독 가능한 일정 API 및 서버별 시간 규칙은 확인하지 못했습니다. 접근 실패가 해당 사이트의 일정 제공 여부를 뜻하지는 않습니다.

직접 CN 공식 Wiki를 읽는 후속 경로를 추가하려면 다음 근거가 필요합니다.

- 공식 글로벌 공지 또는 출처가 추적되는 신뢰 가능한 자료에서 캐릭터 픽업임을 확인.
- 사용자 허용 범위인 공통 가챠 일정을 사용하되, 원본 CN 시간대와 시작·종료 시각의 의미를 명시적으로 확인하여 KST로 변환.
- 날짜만 있는 공지에서 시간을 추측하지 않고, 종료 시각 누락·스키마 변경·빈 응답은 등록 보류.
- 고정된 공개 자료로 파서 회귀 테스트를 만든 뒤, PC·Android가 같은 배너 키·Todoist 명령 UUID를 생성하는지 확인.

공개 [GachaClock 구현](https://github.com/iaoongin/GachaClock/blob/99d16c10bfeeb5f885e9cb42861c50f993f3a746/spider/spider/spiders/ww.py)은 무인증 `POST https://api.kurobbs.com/wiki/core/homepage/getPage`와 `wiki_type: 9`, `source: h5` 헤더를 사용합니다. `data.contentJson.sideModules[].content.tabs[]`에 배너명·`countDown.dateRange`·캐릭터 항목 링크가 있고, `POST /wiki/core/catalogue/item/getEntryDetail`의 `data.name`을 읽습니다. 이 API도 현재 CONNECT 403으로 실제 원본 응답을 확보하지 못했습니다. 공개 구현의 가공 데이터는 과거 일정이므로 현재 일정 대신 사용하지 않습니다. 주요 픽업 등급, 한국어 이름 연결, 시간대 및 종료 시각 의미를 확인하기 전까지 직접 CN 어댑터는 구현하지 않았습니다.

한국어 이름 연결의 후속 후보는 공개 추출 데이터 [Dimbreath/WutheringData](https://github.com/Dimbreath/WutheringData/tree/e9234ffe094b2d944d16b222d31102e8ab32d954)입니다. 조사한 커밋에서 `ConfigDB/RoleInfo.json`의 `Id=1402`, `QualityId=4`, `Name=RoleInfo_1402_Name`과 `TextMap/zh-Hans/MultiText.json`의 같은 키 `秧秧`, `TextMap/ko/MultiText.json`의 같은 키 `양양`을 실제 HTTP 200 응답으로 대조했습니다. 이는 공인 API가 아닌 비공식 게임 데이터이며, Wiki 항목 ID가 게임 역할 ID와 같다는 뜻이 아닙니다. 적용하려면 같은 버전의 CN 이름→역할 Name 키→한국어 텍스트가 유일하게 매칭되는 경우만 허용하고, 등급·중복 이름·누락 키를 검증해야 합니다. 현재 실행 경로에는 이 데이터를 연결하지 않았습니다.

가챠 기록 URL은 과거 뽑기 내역을 제공하는 별개 정보입니다. 이를 진행 중 배너 일정 출처로 사용하지 않습니다. 글로벌 개인 일퀘·엔드 콘텐츠 API도 별도 검증 대상이며 이번 가챠 정책 변경으로 활성화하지 않습니다.
