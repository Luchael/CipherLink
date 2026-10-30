# 계정 API / 비식별 진단에서 확인된 필드 / 회차 주의사항

다음은 사용자가 이전에 공유한 **비식별 진단 JSON의 구조적 사실만** 요약한 것입니다. 원본 JSON·UID·쿠키·토큰·정확한 플레이 기록은 인수인계 ZIP에 포함하지 않습니다.

## 원신 (HoYoLAB)

- `spiral`: `total_star`, `floors[]`, `start_time`, `end_time`. 최신 기록에서 36별 확인 사례.
- `theater`: 최상위 `data[]`가 회차별 기록이고 각 `schedule.{start_date_time,end_date_time}`, `stat.get_medal_round_list[]`, `detail.detail_stat`, `detail.rounds_data[]`가 있음. `get_medal_round_list`는 **12개 배열 길이**만으로 완료 판정 금지. 각 원소 획득 여부/메달 상태를 검사. 과거 시즌 기록이 함께 올 수 있음.

## 스타레일

- 혼돈 `moc`: `star_num`, `begin_time`, `end_time`, `groups[]`, `all_floor_detail[]`.
- 허구 `pure_fiction`, 종말 `apocalyptic`: `star_num`, `groups[]`의 기간, 전적 층별 `star_num`/노드 점수. 이전 회차도 별도 요청할 수 있으니 현재 회차만 자동 완료.
- 이상 중재 `arbitration`: `challenge_peak_records[]`가 **여러 회차 기록**을 가질 수 있음. `group.begin_time/end_time`의 현재 기간만 선택 후 `mob_stars + boss_stars` 판정. 이전 기록과 합산 금지.
- 전적 요청에 DS 서명/언어 헤더/유효 세션 쿠키 필요할 수 있고 API 세부 구조는 변경될 수 있음. Android 과거 `retcode=-10001` 진단은 헤더/서명 차이 수정 후 실제 조회 성공 사례가 있었으나, PC 계정 연결 실패 원인과 혼동 금지.

## 젠레스 존 제로

0.11.11의 응답 재생·미도전/부분 기록 처리·검증 범위는 [시유 기록 안내](SHIYU_RECORDS.md)를 따른다. 시유는 별이 아닌 API S 등급을 세며, 정상 미도전은 `기록 없음`으로 표시한다.

- 시유 `shiyu`: `hadal_ver=v2`, `hadal_info_v2.hadal_begin_time/hadal_end_time`, `fourth_layer_detail.rating`, `fitfh_layer_detail.layer_challenge_info_list[].{rating,score}`, `brief.{score,max_score,rating}`. 현재 완주 기준: 제4전선 S + 제5전선 **세 방 개별 S**, 총합 90,000점 등으로 대체하지 말 것. 과거 사용자 진단에 제4전선 S 및 제5전선 S/S/S 기록이 있었음.
- 위험한 강습전 `deadly`: **`list[]`는 일반**, `hard_list[]`는 절망, `has_data`, `has_hard`, `total_star`, `total_score`, `start_time`, `end_time`.
- **핵심 버그가 고쳐진 사실**: API `retcode=0`, `has_data=false`, `list=[]`, `total_star=0`은 현재 회차 **미도전(0/9별)**이므로 오류로 표시하지 말 것. 과거 시즌 `list[]` 3개/9별이고 `hard_list[]` 별도 전적도 존재했음. 일반 보상 완료는 현재 회차 **일반 9별만**으로 판단.

## 인증·보호

- 사용자가 원래 공유한 비식별 JSON 진단 파일은 이 아카이브에서 **의도적으로 제외**. Codex에서 실제 스키마 확인이 추가로 필요하면 사용자가 비식별 파일을 별도 제공할 수 있음.
- 민감 정보 제거는 키 이름만 제거하는 것으로 충분하지 않음. JSON 텍스트, Authorization 헤더, Cookie, `ltoken`, UID, URL 쿼리의 인증 파라미터, 토큰 재발급 값/디바이스 지문도 출력 금지.
- `retcode`, 상태 코드, 점수, 회차 시작·종료일, JSON 키/타입/배열 길이 같은 진단 가능한 정보 중심으로 수집.
