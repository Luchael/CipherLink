package com.gametodo.nativeapp

/**
 * 사용자가 설정한 콘텐츠별 최대 보상 조건.
 * PC endgame_goals.json, Android assets/endgame_goals.json과 동일하게 유지한다.
 *
 * 특히 환상극의 Stella(스텔라, 별·꽃)와 공연 메달은 서로 다른 수치이다.
 * 도전 방 수, 공연 메달 개수, 계시카드 진행도는 완료 조건으로 사용하지 않는다.
 * 실제 현재 회차 기록이 확인되었을 때만 AccountSync에서 Todoist를 완료한다.
 */
object EndgameGoals {
    const val THEATER_STELLA = 12
    private val targets = mapOf(
        "spiral" to 36,
        "theater" to THEATER_STELLA,
        "moc" to 36,
        "pure_fiction" to 12,
        "apocalyptic" to 12,
        "deadly" to 9,
        "arbitration" to 12
    )

    fun target(mode: String): Int? = targets[mode]

    /** 실제로 같은 척도의 달성 수치가 확보됐을 때만 계산한다. */
    fun met(mode: String, achieved: Int?): Boolean =
        achieved != null && achieved >= 0 && (targets[mode]?.let { achieved >= it } ?: false)
}
