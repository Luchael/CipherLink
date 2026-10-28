package com.gametodo.nativeapp

import org.json.JSONObject

/**
 * 점수형 주간 콘텐츠 전용 판정기. API 응답의 없는 값은 절대 0점/완료로 가정하지 않는다.
 * 어떤 활동이 주간 보상과 다른 콘텐츠인지 주석으로 설명해 둔다.
 */
object WeeklyProgress {
    const val ZZZ_RIDU_POLY = 800 // 마지막 폴리크롬 구간: 800점, 전체 2100점과 다름
    const val ZZZ_BOUNTY = 8000   // 제로 공동 현상금 최종 보상 구간
    const val WEEKLY_BOSSES = 3
    const val HSR_WEEKLY_POINTS = 18000 // 사용자 지정 주간 목표

    /** 첫 번째와 두 번째 항목이 모두 확인된 경우만 합산 2/2 게이지를 만든다. */
    private fun both(role: GameRole, key: String, one: Boolean?, two: Boolean?): AccountGauge? {
        if (one == null || two == null) return null
        return AccountGauge(role.game, role.uid, key, (if (one) 1 else 0) + (if (two) 1 else 0), 2)
    }

    fun genshin(note: JSONObject, role: GameRole): AccountGauge? {
        val remaining = readNumber(note, "remain_resin_discount_num") ?: return null
        val max = readNumber(note, "resin_discount_num_limit") ?: return null
        if (max < WEEKLY_BOSSES || remaining !in 0..max) return null
        return AccountGauge(role.game, role.uid, "weekly", max - remaining, max)
    }

    /**
     * 4.2 버전 이후 화폐 전쟁·시뮬레이션 우주의 보상이 하나의 주간 점수로 통합됐다.
     * 실시간 메모의 current_rogue_score / max_rogue_score를 읽는다.
     * 이전 코드의 currency_wars.* 필드는 통합 점수라는 보장이 없어 사용하지 않는다.
     * 사용자가 요청한 18000점 목표를 적용한다. API 계정별 만점과 구별한다.
     */
    fun hsr(note: JSONObject, role: GameRole): AccountGauge? {
        val score = readNumber(note, "current_rogue_score", "rogue_score")
        val maxScore = HSR_WEEKLY_POINTS
        val scoreDone = if (score != null && score >= 0)
            score >= maxScore else null
        // 역전의 여운: 남은 *주간 할인 보상* 횟수. 보스 전투 횟수 자체는 API로 확인 불가.
        val remaining = readNumber(note, "remaining_weekly_discounts", "weekly_cocoon_cnt")
        val maxDiscounts = readNumber(note, "max_weekly_discounts") ?: WEEKLY_BOSSES
        val bossDone = if (maxDiscounts == WEEKLY_BOSSES && remaining != null &&
            remaining in 0..WEEKLY_BOSSES) remaining == 0 else null
        return both(role, "weekly", scoreDone, bossDone)
    }

    fun zzz(note: JSONObject, role: GameRole): AccountGauge? {
        val ridu = readNumber(note, "weekly_task.cur_point", "weekly_task.current")
        // num/total 은 현상금 임무 횟수이며 '8000점'과 같다고 보장할 수 없다.
        val bountyPoints = readNumber(note,
            "bounty_commission.total_score", "bounty_commission.current_score",
            "bounty_commission.score", "bounty_commission.points", "hollow_zero.bounty_points")
        return both(role, "weekly", ridu?.let { it >= ZZZ_RIDU_POLY },
            bountyPoints?.let { it >= ZZZ_BOUNTY })
    }

    fun diagnostic(note: JSONObject, game: String): List<String> = when(game) {
        "genshin" -> listOf("주간보스 할인 남음: " + (readNumber(note,"remain_resin_discount_num")?.toString() ?: "미확인") + "/3")
        "hsr" -> {
            val score = readNumber(note, "current_rogue_score", "rogue_score")
            val maxScore = HSR_WEEKLY_POINTS
            val remain = readNumber(note, "remaining_weekly_discounts", "weekly_cocoon_cnt")
            val maxBoss = readNumber(note, "max_weekly_discounts") ?: WEEKLY_BOSSES
            val validBoss = maxBoss == WEEKLY_BOSSES && remain != null && remain in 0..WEEKLY_BOSSES
            listOf("시뮬레이션 우주·화폐 전쟁 통합 주간 포인트: " +
                (score?.toString() ?: "미확인") + "/" + (maxScore?.toString() ?: "미확인"),
                "역전의 여운 주간 보상 잔여: " +
                (if (validBoss) "$remain/$maxBoss" else "미확인/3") +
                " (실제 전투 횟수가 아닌 할인 보상 횟수)",
                "이상 중재: 회차와 별 수 조회 API 확인 전 자동 체크 보류")
        }
        "zzz" -> {
            val point=readNumber(note,"weekly_task.cur_point", "weekly_task.current")
            val bounty=readNumber(note,"bounty_commission.total_score", "bounty_commission.current_score", "bounty_commission.score", "bounty_commission.points", "hollow_zero.bounty_points")
            val jobs=readNumber(note,"bounty_commission.num")
            listOf("리두 주간 폴리크롬: ${point?.toString() ?: "미확인"}/800",
                 "현상금 의뢰 포인트: ${bounty?.toString() ?: "API 미제공"}/8000",
                 "현상금 의뢰 횟수: ${jobs?.toString() ?: "미확인"} (8000점의 증거는 아님)")
        }
        else -> emptyList()
    }
}
