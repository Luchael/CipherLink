# 설치·업데이트·제거

## 다운로드

[저장소 첫 화면](https://github.com/Luchael/CipherLink#readme)의 **Windows 설치·업데이트 다운로드**를 누른다. 버튼은 실제 릴리스에 첨부된 파일만 연결한다. 기존 초안 파일은 저장소 소유자 계정으로 GitHub 로그인해야 보인다. README의 버전 상세 링크에서 Assets를 펼쳐도 된다. 소스 ZIP은 설치 파일이 아니다.

## 정식 배포

사용자 지시에 따라 최신 코드는 `main`에 반영하고 Windows 설치 파일은 정식 릴리스로 배포한다. `v*` 태그를 올리면 `Release CipherLink` 워크플로가 해당 태그의 소스를 빌드하고 설치·업데이트·제거 검사를 거친 뒤 실제 Windows 파일과 체크섬을 게시한다. README 링크도 첨부된 파일에 맞춰 갱신한다. 기존 초안 릴리스나 파일은 삭제하지 않는다.

## 현재 제공 버전

- **최신 소스: 0.11.8, [main](https://github.com/Luchael/CipherLink/tree/main).** [변경 기록](RESET_FLOATING_0118.md)을 참고한다.
- **Windows:** [0.11.8 정식 릴리스](https://github.com/Luchael/CipherLink/releases/tag/v0.11.8)의 설치 파일을 사용한다. 파일은 Windows 빌드와 설치 검사가 성공한 뒤 게시된다.
- **Android:** 0.11.8은 서명 없는 빌드까지만 검증됐다. 기존 서명키를 복구한 뒤 같은 서명으로 업데이트 APK를 만들어야 한다. README의 Android 링크는 기존 0.11.7이며, 새 버전의 수정은 포함하지 않는다.

### Android 다운로드 안내

기존 안내의 “APK 업로드 예정”은 과거 상태다. 이후 서명된 APK 전송 코드와 README의 실제 APK 링크 갱신 커밋이 반영됐다. 현재 README는 [0.11.7 APK 링크](https://github.com/Luchael/CipherLink/releases/download/untagged-f06c6b073a26012ef117/CipherLink-Android.apk)를 제공한다. 다만 이번 환경에서는 GitHub 릴리스 API가 403을 반환해 첨부파일의 현재 상태와 실제 다운로드를 재검증하지 못했다.

다운로드가 시작되지 않으면 소유자 계정으로 로그인한 뒤 [0.11.7 릴리스 초안의 Assets](https://github.com/Luchael/CipherLink/releases/tag/untagged-f06c6b073a26012ef117)를 확인한다. 서명 없는 0.11.8 파일이나 다른 버전의 APK를 0.11.7 다운로드 파일로 바꾸지 않는다.

## Windows 설치판

1. `CipherLink-Windows-Setup.exe`를 실행한다. 한국어 설치 화면이며 관리자 권한·Python 설치가 필요 없다.
2. 처음에는 현재 사용자의 `%LOCALAPPDATA%\Programs\CipherLink`에 설치한다. 시작 메뉴에 사이퍼링크 바로 가기를 추가하며 바탕 화면 바로 가기는 선택이다.
3. 새 버전 설치 파일을 실행하면 기존 설치 위치를 찾아 업데이트한다. 이전 앱을 실행 중이면 종료 안내를 따른다. 이전 버전으로의 설치는 거부한다.
4. 제거는 **Windows 설정 → 앱 → 설치된 앱 → 사이퍼링크 → 제거**를 사용한다. 설치 폴더의 `unins000.exe`도 같은 제거 기능이다.

기본 계정·설정·DB 폴더 `~/.gametodo`는 설치·업데이트·제거 시 삭제하지 않는다. 무설치판에서 별도로 두었던 로컬 `config.json`도 원본 위치에 남으며, 임의 폴더 검색이나 비밀정보 복사는 하지 않는다. 무설치판의 시작 프로그램 경로가 등록돼 있으면 설치 경로로 갱신하며 Windows에서 사용 안 함으로 선택한 상태를 바꾸지 않는다. 자동 시작을 새로 켜지는 않는다. 제거 시 자신의 설치 경로를 가리키는 시작 항목만 지우고 다른 무설치판을 가리키는 항목은 보존한다.

Windows 무설치 EXE도 별도 제공한다. 이 파일은 설치·제거 등록을 하지 않는다. 종료 후 EXE를 교체해 업데이트하고, 사용하지 않으면 해당 EXE를 지운다. 설치판과 동시에 실행하지 않는다.

## Android

APK를 열어 기존 앱 위에 업데이트한다. 같은 패키지·서명이 필수이며 versionCode가 증가해야 한다. 앱 삭제는 Android의 일반 앱 제거 기능을 사용하며 앱 데이터를 지우므로 업데이트를 위해 먼저 삭제하지 않는다. 원본 0.10.2와 설치 성공한 별도 설치판은 패키지/서명 호환성을 구별한다. 사용자에게 토큰이나 서명키를 요구하지 않는다.

앱 사용에 GitHub 계정은 필요 없으며 다운로드 시에만 로그인한다. 무인 설치·GitHub 토큰 입력은 제공하지 않는다.

## 개발·버전 관리

- PC·Android 버전과 Windows EXE 리소스 버전을 일치시키고 Android versionCode를 증가시킨다. `tools/release_metadata.py`가 오래된 EXE 리소스를 거부한다.
- `tools/publish_release.py`는 기존 Android 서명으로 APK를 확인하고 버전 태그·초안을 만든다. 업로드 차단 해제 후 `--resume`으로 기존 초안에 APK를 첨부할 수 있다.
- `release.yml`은 태그의 Windows EXE와 Inno Setup 설치 파일을 만든다. `tools/build_windows_installer.ps1`은 EXE의 실제 ProductVersion을 확인한다.
- Windows CI는 0.11.5 EXE로 만든 이전 설치판→현재 설치판 업데이트→낮은 버전 거부→제거·재설치를 실행한다. 기존 설치 경로 자동 발견, Windows 제거 등록, 사용자 데이터 보존과 다른 무설치 시작 항목 보존을 확인한 뒤 설치 파일을 첨부한다. CI에서는 게임/Todoist 계정을 연결하거나 앱을 실행하지 않는다.
- 새 `release-windows.yml`은 검증한 Windows 파일을 정식 게시한다. Android가 준비되지 않았으면 Windows 전용 메타데이터를 생성하고 Android 업데이트가 있는 것처럼 표시하지 않는다. 기존 `release.yml`과 `publish_release.py`의 비공개·양 플랫폼 초안 절차는 구 배포 경로로 남아 있다.
- `tools/update_download_links.py VERSION --github`는 현재 실제 첨부파일을 읽어 README 다운로드 부분만 갱신한다. 실제 첨부된 파일과 사용자가 요청한 APK 업로드 예정 주소를 구별하며 이전 버전 작업이 최신 링크를 덮어쓰지 않는다.

실제 사용자 Windows의 로그인·SmartScreen·사용 중인 앱 종료·계정 유지와 Android 기기 설치는 CI 빌드/설치 검사와 별도로 확인한다.
