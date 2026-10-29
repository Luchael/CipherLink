# 설치 파일과 버전 관리

## 다운로드

[최신 버전](https://github.com/Luchael/CipherLink/releases/latest)에서 **CipherLink-Windows.exe** 또는 **CipherLink-Android.apk**를 누릅니다. GitHub **Assets** 목록에서 받으면 됩니다. 소스 ZIP을 받을 필요가 없습니다.

사용자는 전체 비공개 배포를 선택했습니다. GitHub 소유자 계정으로 로그인해야 비공개 저장소와 파일이 보입니다. Codex는 사용자의 GitHub 연결 권한으로 접근하며 별도 사람 계정/협업자를 추가하지 않습니다.

2026-10-29: 현재 GitHub 연결은 관리 API가 403을 반환하여 공개 범위 변경을 수행하지 못했습니다. 저장소 소유자가 [Settings](https://github.com/Luchael/CipherLink/settings) → 맨 아래 **Danger Zone → Change repository visibility → Make private**로 바꿔야 합니다. 그 전에는 새 바이너리를 **초안 릴리스에만** 보관하며 자동 게시하지 않습니다.

## 업데이트

- 앱 **설정 → 최신 버전 다운로드**에서 현재 버전과 릴리스 페이지를 확인합니다.
- Android: 기존 앱을 삭제하지 않고 새 APK를 열어 업데이트합니다. 휴대폰이 설치 승인을 받습니다. 패키지/서명이 다르면 중단합니다.
- Windows: 앱을 종료한 뒤 EXE를 교체합니다. 기존 설정/DB는 보존합니다. Python/pip 설치는 필요 없습니다.
- 새 버전 알림: GitHub 저장소 **Watch → Custom → Releases**. GitHub의 계정 알림 설정에 따라 알림/메일이 도착합니다.
- 전체 비공개 방식에서는 앱이 GitHub 토큰을 별도로 받지 않으므로 인증 없는 자동 버전 조회·다운로드와 무인 설치는 제공하지 않습니다. 앱에 GitHub 비밀번호/토큰을 입력하지 마세요.

## 버전 관리와 배포 — 개발자

PC `gametodo.__version__`와 Windows 버전 리소스, Android `versionName`을 함께 올립니다. Android `versionCode`는 반드시 증가시킵니다. `docs/releases/vX.Y.Z.md`에 변경 내용을 기록하고 커밋합니다.

서명이 유지되는 기존 Android 빌드 환경에서 다음 명령을 실행합니다.

```bash
python tools/publish_release.py X.Y.Z --output /workspace/artifacts
```

이 명령은 깨끗한 작업 트리/일치하는 버전/릴리스 노트를 확인하고, 기존 서명으로 APK를 빌드합니다. APK 공개 메타데이터(패키지·버전·서명 인증서 해시)와 무결성을 검사한 뒤 버전 태그와 초안 릴리스를 만들고 APK를 업로드합니다. 서명 키는 이 환경에만 남으며 저장소/CI에 올리지 않습니다.

이후 GitHub Actions **Publish versioned EXE and APK**가 해당 태그의 소스를 체크아웃하여 Windows 회귀 테스트와 EXE 빌드를 실행합니다. EXE·APK·SHA256SUMS.txt·update.json이 준비되고 저장소가 비공개일 때만 최신 릴리스를 게시합니다. 실패하면 초안으로 남습니다. 기존 릴리스 파일은 덮어쓰지 않습니다.

초안 준비 후 공개 범위를 비공개로 바꿨다면 다음 명령으로 남은 게시만 처리할 수 있습니다.

```bash
python tools/publish_release.py X.Y.Z --finalize
```

현재 GitHub 연결에는 Actions 비밀 저장소 등록 권한도 없습니다. 이 때문에 APK 서명은 로컬에서 계속하고, Windows 빌드·체크섬·게시를 CI가 맡습니다. 사용자는 서명 키나 계정 토큰을 전달할 필요가 없습니다. 서명 키가 사라지면 동일 패키지 업데이트가 불가능하므로 임의로 새 키로 교체하지 않습니다.

이전 버전은 [Releases](https://github.com/Luchael/CipherLink/releases)에 남습니다. 낮은 Android 버전을 기존 앱 위에 설치하는 다운그레이드는 일반적으로 허용되지 않습니다. 테스트/빌드 통과가 실계정·실기기 동작을 보증하지 않습니다.
