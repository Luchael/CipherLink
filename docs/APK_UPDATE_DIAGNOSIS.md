# 기존 0.10.2 APK 업데이트 실패 진단

사용자가 마지막으로 설치할 수 있었던 0.10.2 APK와 클라우드0.10.6 APK를 직접 대조했다. APK는 저장소에 포함하지 않는다.

| 항목 | 설치 가능했던0.10.2 | 클라우드0.10.6 |
| --- | --- | --- |
| applicationId | com.gametodo.nativeapp | com.gametodo.nativeapp |
| versionCode | 23 | 27 |
| targetSdk | 35 | 35 |
| 서명 인증서 SHA256 | 71492ec6a09f4635d7449d2242cd1a1807b4d81a63f252a58dcacb6e96958c36 | 2f5505f8e8b1b8b00ea9ed27d6e2ce733ad8b8f46aa19797eb8a5a68de5897cb |

두 APK 모두 v2 서명검증, ZIP CRC, 16KB zipalign 검증을 통과했으며 네이티브 라이브러리는 없다. 새 버전 번호는 더 높지만 같은 패키지의 서명이 달라 덮어쓰기 업데이트는 불가능하다. APK만으로 원래 개인 서명키를 복구하거나 다른 키를 같은 서명으로 만들 수 없다. 기존 앱을 삭제해서 해결하도록 안내하지 않는다. 원래 빌드 환경에 기존 키가 보존돼 있다면 그 환경에서 새 소스를 같은 키로 빌드해야 하며, 키/비밀번호를 채팅이나 저장소로 전달해서는 안 된다.

별도 설치판은 com.gametodo.nativeapp.preview로 분리되어 원래앱과 서명충돌이 없다. 이는 기존 앱의 업데이트나 데이터이전이 아니다. 별도 로그인해야 하며 기존 설정/Keystore에는 접근하지 않는다. 별도 설치판까지 실패하면 서명충돌만으로 설명할 수 없으므로 기기 설치 오류 상세/알 수 없는 앱 설치 허용상태 등의 추가 확인이 필요하다. 이 기기의 실제 설치 성공은 아직 미검증이다.

재발방지 검사: `python3 tools/check_apk_update.py OLD.apk NEW.apk --build-tools <SDK/build-tools/35.0.0>` . 업로드된 원본과 새 APK 비교에서 SIGNATURE_MISMATCH/exit1 재현. 패키지 분리와 동일클라우드서명 상위버전은 별도 상태로 구분하며, APK 내부 계정데이터/키파일을 읽지 않는다. signer rotation lineage는 지원하지 않으며 같은 인증서 기반 업데이트만 판정한다. metadata호환 통과는 실제 기기 설치 보장이 아니다.

PC231 tests 통과. 앱 실행 동작이나 패키지/서명은 이 진단을 위해 변경하지 않았다.
