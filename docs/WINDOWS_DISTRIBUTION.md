# Windows EXE 배포와 검증

이 저장소는 Windows용 `CipherLink.exe`를 만드는 경로를 제공합니다. **현재 Windows EXE 실행·공식 로그인·설치·업데이트와 Android APK 실환경 동작은 미검증입니다.** Linux에서의 Python 회귀 테스트 통과 또는 GitHub Actions 빌드 성공은 이 검증을 대신하지 않습니다.

## EXE 만들기 — 개발자

GitHub의 Actions → **Build Windows EXE (manual, unverified)** → **Run workflow**를 선택합니다. 워크플로는 수동 실행만 가능하며 릴리스를 자동 게시하지 않습니다. 성공한 실행의 `CipherLink-Windows-unverified-<commit>` 아티팩트를 내려받습니다. 아티팩트에는 EXE와 `SHA256SUMS.txt`, 이 안내가 들어 있습니다. 아티팩트 보관 기간은 14일입니다.

Windows 개발 PC에서는 Python 3.10 이상으로 `pc/build_windows.bat`를 실행해 같은 빌드를 수행할 수 있습니다. 스크립트는 로그인·엔드 콘텐츠 의존성 설치, 모듈 import, 필수 리소스 확인, PC 전체 unittest를 통과한 뒤 PyInstaller로 패키징합니다. CI에서는 `CIPHERLINK_BUILD_NONINTERACTIVE=1`로 일시정지를 생략합니다. 실패한 실행 이후 남은 `dist/` 파일을 새 빌드 결과로 배포하지 마세요.

이 경로는 휴대용 EXE를 만듭니다. 설치 프로그램, 코드 서명, 자동 업데이트 및 OCR용 별도 도구 패키징은 아직 제공하지 않습니다. Windows에서 실제 빌드가 성공했는지도 실행 결과로 별도 확인해야 합니다.

## 실행 — 최종 사용자

검증된 빌드의 ZIP을 사용자 쓰기 가능한 폴더에 풀고 `CipherLink.exe`를 실행합니다. Python/pip 또는 라이브러리 수동 설치가 필요 없는 구성이 목표입니다. 공식 로그인 창에는 이 PC에 설치된 Microsoft Edge가 필요합니다. CAPTCHA와 인증 코드는 공식 사이트에서 직접 처리합니다.

앱에서 Todoist와 게임 계정을 연결합니다. 비밀번호·쿠키·토큰을 개발자에게 전달하지 마세요. EXE에서는 개발용 “로그인 모듈 설치” 버튼을 표시하지 않습니다. 모듈 누락 오류가 있으면 빌드 문제로 보고하고 수정된 EXE로 교체합니다.

기존 `~/.gametodo` 저장 경로와 호환 키를 유지합니다. 기존 설치 폴더에 `config.json`이 있으면 그 설정을 우선 사용하므로, 업데이트할 때 설정과 `data` 폴더 및 사용자 홈의 `.gametodo`를 보존하세요. 신규 EXE에는 개인 설정·DB·브라우저 프로필·인증값을 동봉하지 않습니다.

## Windows에서 남은 확인

- Python이 설치되지 않은 Windows 일반 사용자 계정에서 EXE 시작, 아이콘 및 다섯 화면 표시.
- Edge 공식 로그인 → HoYoLAB UID 확인, GRYPHLINE/SKPORT 아시아 바인딩 확인. 모의 테스트 성공과 실계정 성공을 구분합니다.
- 로그인 실패·시간 초과 후 재시도, 기존 연결 정보 보존, 로그의 HTTP 상태/retcode/응답 필드 구조 확인. 닉네임·UID·URL 쿼리·인증값을 공유하지 않습니다.
- 업데이트 전후 기존 설정·DB 보존. Todoist 읽기 전용 확인부터 진행하고 실제 완료 동작은 별도로 점검합니다.
- EXE의 SHA-256을 PowerShell `Get-FileHash .\CipherLink.exe -Algorithm SHA256`로 계산하여 같은 빌드의 `SHA256SUMS.txt`와 비교합니다. 체크섬은 전송 중 변조 확인용이며 코드 서명이나 실행 검증을 대신하지 않습니다.

앱이 동작하는 것으로 확인되기 전에는 이 빌드를 검증된 설치판으로 표기하지 않습니다. Android APK 빌드·실기기 검증은 별도 작업입니다.
