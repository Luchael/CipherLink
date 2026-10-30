# 새 버전 자동 배포

## 평소 작업

1. PC `__version__`, Android `versionName`, Windows 리소스 버전을 같은 새 버전으로 올리고 Android `versionCode`를 증가시킨다.
2. 소스를 main에 푸시한다. 버전 파일 변경을 감지한 `Release CipherLink`가 자동 실행된다.
3. 해당 소스의 버전 태그를 만들고 Windows와 Android를 독립 빌드한다.
4. Windows 설치·업데이트·제거 검증과 Android 패키지·버전 코드·서명 인증서·ZIP 무결성을 확인한다.
5. 양쪽 파일과 SHA256SUMS.txt/update.json이 준비되면 정식 릴리스를 게시한다.
6. README 맨 위 다운로드 영역을 실제 첨부파일로 갱신한다.

태그를 직접 푸시하거나 Actions → Release CipherLink → Run workflow로 실행해도 된다. 같은 버전이 이미 완전히 게시됐다면 빌드·업로드를 반복하지 않고 README 갱신만 다시 확인한다. 기존 버전 태그나 공개 릴리스 파일은 덮어쓰지 않는다. 릴리스 노트 파일이 없으면 GitHub의 자동 변경 내역을 사용한다.

## 한 번만 등록하는 비공개 서명 설정

[저장소 Actions Secrets](https://github.com/Luchael/CipherLink/settings/secrets/actions)에 등록한다.

| 이름 | 값 |
| --- | --- |
| `ANDROID_KEYSTORE_BASE64` | 본인의 PKCS12 키 파일을 Base64로 변환한 내용 |
| `ANDROID_KEYSTORE_PASSWORD` | 해당 키 저장소의 비밀번호 |

별칭은 `cipherlink-release`다. 개인 키는 임시 경로에서만 사용한 뒤 지운다. 업로드 아티팩트에는 서명된 APK만 들어간다. 키 파일·비밀번호·설정 ZIP을 공개 GitHub에 올리지 않는다.

2026-10-31 KST 사용자가 두 Secrets를 등록했고, [실행 41078740805](https://github.com/Luchael/CipherLink/actions/runs/41078740805)에서 실제 APK 서명·인증서 검증과 Windows·Android 정식 게시가 성공했다. 게시된 APK를 다시 받아 versionName 0.11.9, versionCode 37, 패키지·서명·체크섬을 확인했고 Windows 다운로드 주소도 HTTP 200을 확인했다. README 맨 위 세 설치 파일 링크는 모두 v0.11.9를 가리킨다. 설정 API는 현재 연결에서 403을 반환하며, Secrets 값이나 목록을 읽는 대신 실제 CI 사용 성공으로 검증했다.

## Android 설치 계열

0.11.9부터 패키지 `com.gametodo.cipherlink`와 release-config.json에 기록된 고정 공개 인증서 지문을 사용한다. 이전 `com.gametodo.nativeapp.preview` 앱과는 별도 설치다. 처음 한 번 계정·권한을 다시 설정하며, 기존 앱 자동 확인/게임 감지를 꺼서 동시 동작을 방지한다. 기존 데이터는 삭제하지 않는다.

새 키와 비밀번호는 사용자가 클라우드 환경 밖에도 백업해야 한다. 같은 앱을 업데이트할 때 패키지와 키를 다시 바꾸지 않는다. 이전 설치 계열의 공개 인증서 정보는 이력으로 보존한다.
