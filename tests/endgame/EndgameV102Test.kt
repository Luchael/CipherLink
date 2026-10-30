package com.gametodo.nativeapp
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant

private fun j102(vararg pairs: Pair<String,Any?>) = JSONObject(mapOf(*pairs))
fun main() {
    val now = Instant.parse("2026-10-30T03:00:00Z").epochSecond
    val role = GameRole("zzz", "redacted", "prod_gf_sg", "")
    val noRecord = j102(
        "has_data" to false, "has_hard" to false,
        "total_score" to 0, "total_star" to 0,
        "list" to JSONArray(emptyList()), "hard_list" to JSONArray(emptyList()),
        "start_time" to now-86400, "end_time" to now+86400
    )
    val found=EndgameRecords.parse(role,"deadly",noRecord)!!
    check(found.current==0 && found.maximum==9)
    check(EndgameRecords.currentPeriod(found,now * 1000))
    check(EndgameRecords.deadlyDiagnostic(noRecord).contains("일반 0/9별 (0점)"))
    val prior=j102("has_data" to true, "total_star" to 9,
        "total_score" to 131358,
        "list" to JSONArray(listOf(j102("score" to 53174,"star" to 3),
            j102("score" to 48317,"star" to 3),j102("score" to 29867,"star" to 3))),
        "hard_list" to JSONArray(listOf(j102("score" to 33930,"star" to 3))),
        "start_time" to now-900000,"end_time" to now-1000)
    val p=EndgameRecords.parse(role,"deadly",prior)!!
    check(p.current==9 && !EndgameRecords.currentPeriod(p,now * 1000))
    check(p.displayDetail.contains("일반 1번 53,174점") && p.displayDetail.contains("절망 1번 33,930점"))
    check(EndgameRecords.deadlyDiagnostic(prior).contains("절망 33930점/3별"))
    println("Endgame v0.10.2 current unplayed / normal / adversity tests OK")
}
