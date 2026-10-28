package com.gametodo.nativeapp

import org.json.JSONObject

/**
 * HoYoLAB '실시간 메모(Real-Time Notes / Sticky Notes)' 부가 정보.
 *
 * 기존 엔드콘텐츠 전적 API와 별도의 출처다. 실시간 메모에만 등장하는
 * 원정/화폐/가게/현상금/주간 보스 할인 정보를 화면에 표시한다.
 * API 버전마다 필드가 다를 수 있으므로 확인된 값만 표시하며,
 * '횟수'를 '점수'나 '보상 수령'으로 억지로 변환하지 않는다.
 * 계정 세션은 기존 HoyoProvider.note()의 인증 경로를 그대로 재사용한다.
 */
object RealTimeMemo {
    fun detailLines(game: String, data: JSONObject): List<String> {
        val result = mutableListOf<String>()
        fun gauge(name: String, vararg keys: String) {
            // 인수는 '현재 필드 후보 묶음' / '최대 필드 후보 묶음'으로 구분한다.
            val partition = keys.indexOf("|")
            if (partition < 0) return
            val cur = readNumber(data, *keys.sliceArray(0 until partition))
            val max = readNumber(data, *keys.sliceArray(partition+1 until keys.size))
            if (cur != null && max != null && max > 0) result.add("$name $cur/$max")
        }
        fun number(name: String, vararg paths: String) {
            readNumber(data, *paths)?.let { result.add("$name $it") }
        }
        fun state(name: String, vararg paths: String) {
            for (path in paths) {
                val value = readString(data,path) ?: continue
                // 계정 토큰 등 민감한 문자열은 표시하지 않는다. 고정된 상태 필드만 읽는다.
                if (value.length <= 48) result.add("$name $value")
                break
            }
        }
        when (game) {
            "genshin" -> {
                gauge("선계 화폐", "current_home_coin", "current_realm_currency", "|",
                    "max_home_coin", "max_realm_currency")
                gauge("탐사 파견", "current_expedition_num", "|", "max_expedition_num")
                state("추가 의뢰 보상", "is_extra_task_reward_received")
            }
            "hsr" -> {
                gauge("시뮬레이션 우주·화폐 전쟁 통합 주간 포인트", "current_rogue_score", "rogue_score", "|",
                    "max_rogue_score", "rogue_max_score")
                gauge("차분화 우주 보너스 포인트", "current_bonus_synchronicity_points", "|",
                    "max_bonus_synchronicity_points")
                gauge("역전의 여운 주간 할인 잔여", "remaining_weekly_discounts", "weekly_cocoon_cnt", "|",
                    "max_weekly_discounts")
                gauge("탐사 파견", "accepted_expedition_num", "|", "total_expedition_num")
                state("예비 개척력 가득 참", "is_reserve_stamina_full")
            }
            "zzz" -> {
                gauge("메모 일일 활약도", "engagement.current", "vitality.current", "|",
                    "engagement.max", "vitality.max")
                gauge("제로 공동 현상금 임무", "hollow_zero.bounty_commission.cur_completed",
                    "hollow_zero.bounty_commission.num", "bounty_commission.num", "|",
                    "hollow_zero.bounty_commission.total", "bounty_commission.total")
                gauge("제로 공동 조사 포인트", "hollow_zero.investigation_point.num", "|",
                    "hollow_zero.investigation_point.total")
                gauge("주간 일정", "weekly_task.cur_point", "|", "weekly_task.max_point")
                gauge("사원 운영 화폐", "temple_running.current_currency", "|",
                    "temple_running.weekly_currency_max")
                state("스크래치 카드 완료", "scratch_card_completed")
                state("비디오 가게", "video_store_state", "vhs_sale.sale_state")
                state("커피·출석 상태", "card_sign")
                state("방부 원정", "temple_running.expedition_state")
            }
        }
        return result
    }
}
