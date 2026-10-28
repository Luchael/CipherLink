# GameTodo Android v0.8.0 — 휴대폰 전용 빌드 설명서

이 파일은 **기존 v0.8.0 앱 소스**에 휴대폰만으로 APK를 만들기 위한 GitHub Actions 설정을 추가한 것입니다. Kotlin 소스를 수정하거나 빌드를 성공했다고 주장하지 않습니다.

## 방법 A: 휴대폰에서 직접 빌드 (Code on the Go)
1. https://appdevforall.org/code-on-the-go/ 의 공식 설치 안내에 따라 CoGo 앱 설치.
2. ZIP 압축을 풀고 `android/` 폴더를 기존 프로젝트로 열기.
3. SDK 및 빌드 환경 초기화 후 Gradle 동기화, Run/Build 실행.
4. 이 앱은 현재 유지보수되는 AndroidIDE의 후속 프로젝트입니다. Gradle Wrapper가 없는 프로젝트에서 호환성 문제가 발생할 수 있습니다.

## 방법 B: GitHub Actions 빌드 — 추천 대체 방법
1. F-Droid의 Termux 설치 후 실행:
   ```bash
   pkg update -y
   pkg install git gh unzip -y
   termux-setup-storage
   ```
2. 내려받은 ZIP 압축을 풉니다. 실제 파일명은 저장한 다운로드 파일에 맞추세요.
   ```bash
   mkdir -p ~/projects/gametodo_mobile
   unzip -o ~/storage/downloads/GameTodo_Android_v0.8.0_phone_build.zip -d ~/projects/gametodo_mobile
   cd ~/projects/gametodo_mobile/android
   ```
3. GitHub 로그인과 비공개 저장소 업로드:
   ```bash
   gh auth login --web --git-protocol https
   git init -b main
   git config user.name "$(gh api user --jq .login)"
   git config user.email "$(gh api user --jq .id)+$(gh api user --jq .login)@users.noreply.github.com"
   git add .
   git commit -m 'Build GameTodo Android'
   gh repo create GameTodo-Android --private --source=. --remote=origin --push
   ```
   기존에 동일한 이름의 저장소가 있으면 다른 이름으로 변경하세요.
4. GitHub 웹에서 해당 저장소의 **Actions → Build GameTodo Android APK → 최신 작업 → Artifacts → GameTodoAndroid-debug-apk**를 눌러 결과를 다운로드합니다.
5. 다운로드한 ZIP 안의 `app-debug.apk`를 설치합니다. 휴대폰 보안 설정에서 해당 파일 관리자/브라우저의 앱 설치 권한을 허용해야 할 수 있습니다.

### 주의
- GitHub 업로드 전 `config.json`, 비밀번호, API 토큰, 실제 게임 계정 쿠키를 소스에 넣지 마세요.
- 이 프로젝트는 이전에 Android 빌드를 성공한 적이 없는 **alpha 소스**입니다. Kotlin/Gradle 오류가 발생하면 GitHub Actions 로그에서 실패 지점이 표시됩니다.
- APK가 만들어져도 Todoist 로그인 및 게임사 인증의 성공은 따로 검증해야 합니다.
- GitHub Actions 무료 사용량과 저장소 제한은 본인 계정에 따라 달라질 수 있습니다.
