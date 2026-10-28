# Codex 새 대화에 복사할 프롬프트

사이퍼링크(CipherLink) 기존 프로젝트의 개발을 이어서 해 주세요. 이 디렉터리가 전체 소스입니다. 먼저 `CODEX_START_HERE.md`, `AGENTS.md`, `docs/OPEN_ISSUES.md`, `docs/PRODUCT_AND_TODOIST.md`를 읽고 코드와 일치하는지 확인하세요.

현재 기준은 PC Python/Tkinter v0.10.5, Android Kotlin v0.10.3입니다. PC의 `python -m unittest discover -s tests -q` 168개가 인수인계 시점에 통과했습니다.

우선순위는 ① PC HoYoLAB 공식 로그인 후 3/4 계정 UID 확인 실패, ② PC 엔드필드 GRYPHLINE 로그인 후 3/5 토큰 검증 실패를 실제 소스/공개 API 구현과 대조하여 진단·최소 수정, ③ 명조 글로벌 가챠 일정 수집 경로를 신뢰 가능한 출처로 검증, ④ UI/UX 및 쉬운 Windows EXE 배포입니다. 현재 로그인 수정은 실계정 검증이 끝나지 않았으므로 실제로 작동한다고 가정하지 마세요.

비밀번호·쿠키·토큰을 절대 요구/출력/저장소에 커밋하지 말고, HTTP 상태/retcode/응답 필드 구조만으로 재현 가능하게 만들어 주세요. 원신·스타레일·젠존제의 현재 회차/점수와 실제 Todoist 제목 연결, PC·Android 중복 방지, 플로팅, 명일방주 PC 23:59 사용자가 허용한 1회 조회 정책을 깨지 마세요.

먼저 파일 구조와 테스트 결과, 문제 원인 가설/검증 방법, 수정할 파일과 구체적인 계획을 보여준 뒤 실제 코드를 수정하고 회귀 테스트 결과를 남겨 주세요. Windows EXE 및 Android APK 실환경 검증을 하지 못했다면 분명히 미검증이라고 표시하세요.
