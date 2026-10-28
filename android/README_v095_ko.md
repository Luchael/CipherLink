# 사이퍼링크 v0.9.5 — Android 전적 진단 개선 + PC 조회 보강

기준 Android 소스: 사용자가 올린 v0.9.4 소스 ZIP. **기존 로그인 데이터, 앱 패키지 이름, Todoist 완료 조건, 플로팅 정책을 유지합니다.**

## Android 수정 사항

- `EndgameRecords.kt`의 API 진단 및 결과 판독기를 수정했습니다.
- 스타레일 **혼돈의 기억/허구 이야기/종말의 환영** 조회 후보에 `challenge`, `story`, `challenge_boss` 전적 타입을 사용합니다. 종말의 환영도 실제 현재 회차의 별 수/시각이 확인되지 않으면 완료를 보류합니다.
- 젠존제 **시유 방어전 = mem 계열**, **강습전 = hadal 계열**로 기존 소스의 잘못 연결된 전적 경로를 바로잡았습니다. `mem_info` / `mem_info_v2`를 순서대로 시도합니다. 이 주소는 계정마다 404 또는 권한 오류가 날 수 있으므로 시험 데이터가 아닙니다.
- 원신 **환상극** API의 `need_detail=true` 경로 및 대체 호스트, 중첩 `data`와 `stella` 필드 후보를 검사합니다. **메달·공연 회차 수를 스텔라로 추정하지 않습니다.**
- 일부 전적 응답의 `data`, `detail`, `record`, `list`, `records`, `schedules` 중첩 스키마와 `2026-07-06 04:00` 형식(아시아 서버 UTC+08)을 읽도록 개선했습니다. **여러 시즌이 섞여있는데 어떤 게 현재인지 결정할 수 없다면 자동 완료를 하지 않습니다.**
- API 응답의 필드명은 진단에 표시할 수 있지만 원문 JSON, 쿠키, UID는 출력하지 않습니다.
- 기존에 수정한 **Android 슬라이드 ON/OFF와 조회 간격 15분~24시간**, 스타레일 주간 포인트·역전의 여운, 플로팅 정책은 보존합니다.

## PC 보강 모듈

- `pc/cipherlink_endgame/`에 **표준 라이브러리 기반 HoYoLAB 읽기 전용 전적 조회와 같은 날짜/점수 파서**를 구현했습니다.
- `pc/cipherlink_endgame/arknights_kr.py`는 **선택적으로 ArkPRTS**를 사용해 한국 서버 스태미나 등 사용자 상태를 조회합니다. 실게임 연결이 끊길 수 있으므로 명시적 동의 플래그를 요구합니다.
- `pc/README_PC_v095_ko.md`의 PC 사용법을 참고하세요.
- **주의:** 현재 작업 환경에 과거 PC 전체 소스 ZIP이 없으므로 PC 기존 Windows GUI, 인증 저장소, Todoist 스케줄러까지 직접 교체한 완성판이 아닙니다. PC 모듈은 독립 진단과 기존 PC 코드 통합을 위한 업데이트 부품이며, Android와 완전 동일한 통합 배포라 주장하지 않습니다.

## 명조 글로벌 / 명일방주 KR

- **명조**: 현재 확인된 글로벌 API는 *소집(가챠) 기록*만 제공하므로 일일/주간 임무 자동 완료와 연결하지 않습니다. 중국 KuroBBS 개인 조회를 글로벌 계정에 사용하지 않습니다.
- **명일방주 KR**: `arkprts.YostarAuth('kr')`로 본인 OTP 로그인 후 읽기 전용 계정 데이터를 받을 수 있습니다. 다만 API가 제공하는 자원 수치만으로 일퀘 달성으로 추정하면 안 됩니다. Android 네이티브 직접 연동은 아직 미구현입니다.

## 업데이트 — Android Termux

```sh
ZIP="$(ls -t ~/storage/downloads/CipherLink_Android_v0.9.5*.zip 2>/dev/null | head -n 1)"
[ -f "$ZIP" ] || { echo '다운로드 폴더에 v0.9.5 소스 ZIP을 넣어 주세요'; exit 1; }
unzip -o "$ZIP" -d ~/projects/gametodo
studio build ~/projects/gametodo/android :app:assembleDebug
cp ~/projects/gametodo/android/app/build/outputs/apk/debug/app-debug.apk ~/storage/downloads/CipherLink-v0.9.5.apk
```

기존 APK를 삭제하지 않고 **동일한 서명 키로** 업데이트 설치해야 연결 정보가 보존됩니다.

## 테스트 범위

- Android `EndgameRecords.kt`: Kotlin/JVM 컴파일 및 샘플 응답 **9개 검증** 통과.
- PC `records.py`: Python unittest **6개 테스트** 통과.
- 기존 작업에서 제공된 회차/플로팅/주간 데이터 정책을 수정하지 않았습니다.
- 실제 Android APK 빌드·실계정 HoYoLAB 및 ArkPRTS 호출 성공은 시험하지 못했습니다. 화면에서 성공했다고 표시하려면 본인 계정에서 서버 응답을 재검증해야 합니다.

## 조사한 공개 구현

- genshin.py: https://github.com/seriaati/genshin.py
- 공개 HoYoLAB 전적 계층 예시: https://github.com/dot-1x/hoyo-apy
- 젠레스 전적 분석 구현: https://github.com/whitefallen/Zenless-Inflation-Watcher
- ArkPRTS: https://github.com/ashleney/ArkPRTS
- 명조 글로벌 가챠 전용 수집: https://github.com/dyar7474/WuWa_local_tracker
