package com.gametodo.nativeapp

import org.json.JSONObject

// 순수 JVM에서 실행할 API 판정 테스트를 위한 최소 모형.
data class GameRole(val game: String, val uid: String, val server: String, val nickname: String)
data class AccountGauge(val game: String, val account: String, val metric: String,
                        val current: Int, val maximum: Int) {
    val filled: Boolean get() = maximum > 0 && current >= maximum
}
fun readNumber(root: JSONObject, vararg paths: String): Int? {
    for (path in paths) {
        var at: Any? = root
        for (part in path.split('.')) at = (at as? JSONObject)?.opt(part)
        when(at) {
            is Int -> return at
            is Long -> if(at in Int.MIN_VALUE..Int.MAX_VALUE) return at.toInt()
            is String -> at.toIntOrNull()?.let { return it }
        }
    }
    return null
}

fun main() {
    fun obj(vararg entries: Pair<String, Any?>) = JSONObject(mapOf(*entries))
    val role = GameRole("hsr", "123", "prod_official_asia", "Test")
    fun gauge(note: JSONObject) = WeeklyProgress.hsr(note, role)
    check(gauge(obj("current_rogue_score" to 18000, "max_rogue_score" to 18000,
        "remaining_weekly_discounts" to 0, "max_weekly_discounts" to 3))?.filled == true)
    // 사용자 목표는 API 만점과 무관하게 18000점이다.
    check(gauge(obj("current_rogue_score" to 12000, "max_rogue_score" to 12000,
        "remaining_weekly_discounts" to 0))?.filled == false)
    check(gauge(obj("current_rogue_score" to 18000, "max_rogue_score" to 24000,
        "remaining_weekly_discounts" to 0))?.filled == true)
    check(gauge(obj("current_rogue_score" to 6000, "max_rogue_score" to 12000,
        "remaining_weekly_discounts" to 2))?.current == 0)
    check(gauge(obj("current_rogue_score" to 12000, "max_rogue_score" to 12000,
        "remaining_weekly_discounts" to 1))?.current == 0)
    check(gauge(obj("current_rogue_score" to 5000, "max_rogue_score" to 12000,
        "remaining_weekly_discounts" to 0))?.current == 1)
    // 기존의 화폐 전쟁 전용 필드만 있고 실제 통합 포인트가 없으면 완료 금지.
    check(gauge(obj("currency_wars" to obj("weekly_score" to 99999),
        "remaining_weekly_discounts" to 0)) == null)
    check(gauge(obj("current_rogue_score" to 18000,
        "remaining_weekly_discounts" to 0))?.filled == true) // 사용자 지정 목표
    check(gauge(obj("current_rogue_score" to 18000, "max_rogue_score" to 18000)) == null)
    check(gauge(obj("current_rogue_score" to 18000, "max_rogue_score" to 18000,
        "max_weekly_discounts" to 2, "remaining_weekly_discounts" to 0)) == null)
    check(gauge(obj("rogue_score" to "18000", "rogue_max_score" to "18000",
        "weekly_cocoon_cnt" to 0))?.filled == true)
    check(WeeklyProgress.diagnostic(obj("current_rogue_score" to 9000,
        "max_rogue_score" to 12000, "remaining_weekly_discounts" to 1), "hsr")
        .any { it.contains("9000/18000") })
    check(AutoCheckIntervals.minutes == listOf(15,30,60,120,180,360,720,1440))
    check(AutoCheckIntervals.normalize(3) == 15)
    check(AutoCheckIntervals.normalize(720) == 720)
    check(AutoCheckIntervals.display(60) == "1시간")
    println("WeeklyProgress + AutoCheckIntervals: 15 assertions passed")
}
