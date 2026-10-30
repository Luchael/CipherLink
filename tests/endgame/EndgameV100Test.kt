package com.gametodo.nativeapp
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant

private fun j(vararg pairs: Pair<String, Any?>) = JSONObject(mapOf(*pairs))
fun main() {
    val hsr = GameRole("hsr", "redacted", "prod_official_asia", "")
    val zzz = GameRole("zzz", "redacted", "prod_gf_sg", "")
    val now = Instant.parse("2026-10-30T03:00:00Z").epochSecond
    val old = j("mob_stars" to 9, "boss_stars" to 2,
        "group" to j("begin_time" to now - 800_000, "end_time" to now - 100_000))
    val active = j("mob_stars" to 9, "boss_stars" to 3,
        "group" to j("begin_time" to now - 3600, "end_time" to now + 3600))
    val past = j("mob_stars" to 9, "boss_stars" to 3,
        "group" to j("begin_time" to now - 1_200_000, "end_time" to now - 800_000))
    val peak = EndgameRecords.parse(hsr,"arbitration",j(
        "challenge_peak_records" to JSONArray(listOf(old,active,past))))!!
    check(peak.current==12 && peak.maximum==12 && peak.periodKey!=null)
    check(EndgameRecords.currentPeriod(peak,now * 1000))
    // 기간을 알아도 현재 시즌이 아니면 절대 자동 완료하지 않음
    val nonactive = EndgameRecords.parse(hsr,"arbitration",j(
        "challenge_peak_records" to JSONArray(listOf(old,past))))!!
    check(!EndgameRecords.currentPeriod(nonactive,now * 1000))

    val groupNow = Instant.now().epochSecond
    val pf = EndgameRecords.parse(hsr,"pure_fiction",j(
        "star_num" to 12, "groups" to JSONArray(listOf(
            j("begin_time" to groupNow-600_000,"end_time" to groupNow-300_000),
            j("begin_time" to groupNow-3600,"end_time" to groupNow+7200)))))!!
    check(pf.current==12 && pf.periodKey!=null)
    check(pf.periodStartMs == (groupNow-3600) * 1000 && pf.periodEndMs == (groupNow+7200) * 1000)

    // 사용자 2026-10-28 진단: 26390, 48516, 45724 / 150000, 4전선 등급 검증
    val rooms = JSONArray(listOf(j("score" to 26390, "rating" to "S"),j("score" to 48516, "rating" to "S"),j("score" to 45724, "rating" to "S")))
    fun shiyu(grade: String) = j("hadal_ver" to "v2", "hadal_info_v2" to j(
        "begin_time" to now-3600, "end_time" to now+7200,
        "pass_fifth_floor" to true,
        "fourth_layer_detail" to j("rating" to grade),
        "fitfh_layer_detail" to j("layer_challenge_info_list" to rooms),
        "brief" to j("score" to 120630,"max_score" to 150000)))
    val shy = EndgameRecords.parse(zzz,"shiyu",shiyu("S"))!!
    check(shy.current==4 && shy.maximum==4 && shy.periodKey!=null)
    check(EndgameRecords.parse(zzz,"shiyu",shiyu("A"))!!.current==3)
    check(EndgameRecords.parse(zzz,"shiyu",j("hadal_ver" to "v2", "hadal_info_v2" to j(
        "brief" to j("score" to 150000,"max_score" to 150000)))) == null)

    // 강습전 이전 회차의 9별을 현재 회차에 재사용하지 않음
    check(EndgameRecords.parse(zzz,"deadly",j("has_data" to false,"total_star" to 0))==null)
    val d = EndgameRecords.parse(zzz,"deadly",j("has_data" to true,"total_star" to 9,
        "start_time" to now-900000,"end_time" to now-1000))!!
    check(!EndgameRecords.currentPeriod(d,now * 1000))
    println("Endgame v0.10.0 test passed")
}
