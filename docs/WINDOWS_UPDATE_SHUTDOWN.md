# Windows 업데이트 자동 닫기

## 재현과 범위

사용자 보고는 작업 관리자에서는 종료되지만 설치 프로그램의 자동 닫기로는 종료되지 않는 상황이다. 앱이 백그라운드로 실행된다는 이유만으로 종료 요청이 전달되지 않는다고 단정하지 않는다.

기존 0.11.9 설치판은 `CloseApplications=yes`로 일반 종료 요청만 사용했다. 기존 설치 수명주기 검사는 실행 중인 앱이 없는 상태에서 이뤄져 이 경로를 검증하지 못했다.

[기존 설치판 Windows 재현 실행 41085505261](https://github.com/Luchael/CipherLink/actions/runs/41085505261)에서 응용 프로그램이 종료 요청을 거부하며 설치 대상 EXE를 열어 둔 경우 `AUTOCLOSE_BLOCKED mode=visible exit=5 processStillRunning=True`가 확인됐다. 이는 제어 가능한 합성 응용 프로그램으로 실제 Restart Manager와 기존 설치 프로그램을 구동한 결과다. 사용자 기기의 CipherLink 프로세스 내부 상태까지 재현한 것은 아니다.

## 수정

Inno Setup의 `CloseApplications=force`를 사용한다. 설치 프로그램이 등록한 대상 파일을 사용하는 프로세스에 한해 Restart Manager가 종료를 수행한다. 파일명으로 모든 `python.exe`/`CipherLink.exe`를 무차별 종료하는 코드를 넣지 않는다. 앱의 X 동작이나 예약·계정 조회 정책도 바꾸지 않는다.

공식 Inno Setup 도움말은 force 설정이 응용 프로그램을 강제로 닫으며 미저장 작업이 사라질 수 있다고 설명한다. 사용자는 설치 전에 진행 중인 입력을 마무리해야 한다. 기존 계정·설정·DB의 설치·제거 보존 정책은 유지한다.

## 검증 명령

Windows에서 빌드된 설치판을 준비한 후:

```powershell
$env:PYTHONPATH = 'pc'
$env:CIPHERLINK_SHUTDOWN_INSTALLER = (Resolve-Path publish/CipherLink-Windows-Setup.exe).Path
$env:CIPHERLINK_SHUTDOWN_VERSION = '0.11.10'
python -m unittest pc.tests.test_installer_shutdown -v
```

두 검사는 숨겨진 창/보이는 창 각각에서 프로세스 종료와 잠긴 EXE 교체를 함께 확인한다. 임시 앱과 프로세스는 검사 후 정리한다. Linux의 PC 전체 테스트에서는 Windows 전용 두 검사를 명시적으로 건너뛴다. 실제 Windows 배포 CI에서는 반드시 실행하며 통과하기 전에는 릴리스를 게시하지 않는다.

## 종료 설정만 바꾼 비교 검증

[수정 후 비교 실행 41086593611](https://github.com/Luchael/CipherLink/actions/runs/41086593611)이 성공했다. 기존 0.11.9 EXE를 그대로 사용하고 설치 프로그램의 종료 설정만 force로 바꿔 검증했다. 숨김 창과 보이는 창의 두 종료 거부/파일 잠금 시나리오가 모두 통과했다. 일회성 진단 워크플로는 제거하고 같은 검사를 정상 Windows 릴리스 과정에 편입했다.
