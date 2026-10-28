# GameTodo Android v0.8.0-alpha

Termux 없이 Kotlin 네이티브 단독 실행을 목표로 개발한 **소스 프로젝트**입니다.

Android Studio에서 `android/`를 열고 SDK35/JDK17에 맞춰 빌드합니다. APK는 포함되지 않았으며 현재 Android Studio/실기기 테스트가 수행되지 않았습니다.

진입점: `MainActivity.kt` → `GameAccountLoginActivity.kt` → `AccountProviders.kt` → `AccountSync.kt` → `TodoistApi.kt`.
주기 실행: `SyncWorker.kt`; 앱 전환/플로팅: `GameDetectionService.kt`, `FloatingOverlay.kt`.
가챠: `BannerSource.kt`, `BannerExpiry.kt`. 회차·PC 동일 UUID: `SharedPeriods.kt`.

로그인 및 계정 조회가 실패하면 Todoist 자동 완료를 건드리지 않고 기존 플로팅 수동 체크를 사용합니다.

상세 상태/주의사항은 상위 README.md 참조.


## v0.9.2 반복 회차 필터
자세한 사항: ZIP 루트 README_v092_ko.md 참고.

## v0.9.4 ON/OFF 및 통합 주간 포인트
설정 화면의 슬라이드 스위치/확인 주기를 설정할 수 있으며 스타레일 통합 주간 포인트 판정이 보완됐습니다.
상세 설명: ZIP 루트 `README_v094_ko.md` 참고.

## v0.9.5 엔드 콘텐츠 조회
`EndgameRecords.kt`의 다중 API 경로 및 엄격한 시즌/별 수 판독을 참조하십시오.
실계정 응답이 API 변경으로 미검증이라면 자동 완료를 수행하지 않습니다.
