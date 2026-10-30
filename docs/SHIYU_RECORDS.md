# 시유 방어전: S 등급과 미도전 표시

0.11.11에서 Windows·Android의 시유 응답 해석과 표시를 맞췄다.

## 사용자에게 보이는 상태

| API에서 확인한 내용 | 표시 | 자동 완료 |
| --- | --- | --- |
| 정상 V2 응답, 실제 회차 기간, 통과하지 않음, 전선 도전 기록·점수 없음 | **기록 없음** · 미도전, 진행 막대 숨김 | 안 함 |
| 일부 전선/방의 등급만 있음 | 확인된 S 개수 / 4 S, 누락된 기록 설명 | 안 함 |
| 제4전선 S와 제5전선 각 방 S, 총 네 개, 제5전선 통과 확인 | 4 / 4 S | 실제 현재 회차·Todoist 회차 검증까지 통과해야 가능 |
| 인증/요청 실패, 모르는 형식, 기간 없는 빈 응답 | 정보 없음 · 확인 필요와 사유 | 안 함 |

기록 없음은 내부 진행도 0과 별도 표시 상태로 관리한다. A/B 등급 도전 기록이 있어 S가 0개인 경우의 `0 / 4 S`와 구별한다. API에 기록이 없다는 이유로 이미 지난 회차의 미완료 Todoist를 닫지 않는다.

## S 기준

기존 제품 규칙인 **제4전선 S 1개 + 제5전선 세 방의 S 3개**를 유지한다. `rating`을 직접 세며 별 개수, 종합 `brief.rating=S+`, 총점, 방별 임의 점수 경계로 S를 대신하지 않는다. 게임 내 보상 버튼을 실제 눌렀다는 플래그는 확인되지 않았으므로, 이 표시는 보상 조건 달성 기준이지 실제 수령 확인이 아니다.

구형 V1은 원본 `all_floor_detail[].rating` 또는 `rating_list[].{rating,times}`의 7개 노드 S 개수로 읽는다. SDK가 돌려주는 V1/V2의 평탄한 응답과 API의 `hadal_info_v1/v2` 봉투를 모두 지원한다.

통과 상태가 불분명해도 실제 S 개수를 줄여 표시하지 않는다. `completion_verified`/`completionVerified`로 자동 완료를 별도 보류하고 화면에도 설명한다. 방 ID가 제공되면 중복 방으로 개수를 채울 수 없다.

## 근거와 확인 범위

- [genshin.py 공개 모델](https://github.com/seriaati/genshin.py/blob/2c513b398008b5b8c2d6e98ec156a8b7abe70996/genshin/models/zzz/chronicle/challenge/shiyu.py): V1 필드 별칭, V2의 선택적인 `fourth_layer_detail`, `fitfh_layer_detail`(원 API 오타), 방별 `rating`, `pass_fifth_floor`, 실제 회차 기간.
- [genshin.py 조회 구현](https://github.com/seriaati/genshin.py/blob/2c513b398008b5b8c2d6e98ec156a8b7abe70996/genshin/client/components/chronicle/zzz.py): `get_shiyu_defense(raw=True)`도 버전 봉투를 제거한다. 로컬 1.7.31 배포본과 대조했다.
- [공개 API 응답 예제](https://github.com/whitefallen/Zenless-Inflation-Watcher/blob/55e09044187fffe5c8f894be182d041b938aabf4/hadal_info_v2.json): 제4전선과 제5전선 세 방의 등급 구조. 제3자 예제이며 게임사의 보상 수령 증명은 아니다.
- 사용자 제공 `CipherLink_api_diagnostic_safe.json`과 `(2).json`에 시유 V2 기록이 있다. 첫 파일은 등급/날짜가 가려졌고 두 번째는 읽을 수 있다. 배열은 원본 배열이 아니라 `_array_length`/`_first_samples`로 요약되어 있다. 전 항목이 보존된 두 번째 파일만 로컬에서 배열을 복원해 재생했다. **진단 샘플 배열은 앱의 원본 API 입력으로 받아들이지 않는다.** 원본 첨부 파일은 저장소에 넣지 않는다.
- 두 종료된 회차의 실제 기록은 기존 0.11.10과 수정 코드 모두 봉투/SDK 평탄 응답에서 **4/4 S**로 읽었다. 따라서 이 형식 자체가 사용자의 현재 오류 원인이라고 단정하지 않는다.
- 미도전·부분 기록·V1 별칭 누락은 실제 SDK 호출을 모의 응답으로 실행해 실패를 재현했다. 미도전 응답을 정상 상태로 표시하고, 별 필드에 의한 잘못된 완료를 제거했다. 현재 계정의 실시간 응답을 직접 조회한 것은 아니므로 실제 기기 재확인은 남아 있다.

## 검증

로컬 PC 312개 중 일반 검사 310개 통과, Windows 전용 2개는 Windows CI에서 실행한다. Kotlin 검사 29개 통과. 기존 실제 회차/초기화 경계 검사도 포함한다.

```bash
PYTHONPATH=pc python -m unittest discover -s pc/tests -p test_shiyu_response_contract.py -v
PYTHONPATH=pc python -m unittest discover -s pc/tests -q
python tools/run_kotlin_tests.py
gradle --no-daemon --max-workers=2 --console=plain -p android :app:assembleRelease
```

확인 필요 상태가 계속되면 카드의 `v1/v2`, 제4전선 등급 유무, 제5전선 방 개수 설명만으로 추가 확인할 수 있다. 쿠키·토큰·UID·전체 원본 응답은 공유하지 않는다.
