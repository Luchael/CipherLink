package com.gametodo.nativeapp
import org.json.JSONObject
import org.json.JSONArray
import java.time.Instant
fun obj(vararg pairs: Pair<String,Any?>) = JSONObject(mapOf(*pairs))
fun main() {
    val role = GameRole("hsr", "masked", "prod_official_asia", "")
    val hsr = obj("begin_time" to "2026-07-06 04:00", "end_time" to "2026-08-17 04:00", "total_star" to 36)
    val moc = EndgameRecords.parse(role, "moc", hsr)!!
    check(moc.current == 36 && moc.maximum == 36 && moc.periodKey != null)
    check(EndgameRecords.currentPeriod(moc, Instant.parse("2026-07-06T03:00:00Z").toEpochMilli()))
    val wrongSeason = obj("list" to JSONArray(listOf(obj("total_star" to 36), obj("total_star" to 36))))
    check(EndgameRecords.parse(role, "moc", wrongSeason) == null)
    val chosen = obj("list" to JSONArray(listOf(
        obj("schedule_type" to 2, "total_star" to 36),
        obj("schedule_type" to 1,"total_star" to 20,
            "begin_time" to "2026-07-06 04:00", "end_time" to "2026-08-17 04:00"))))
    check(EndgameRecords.parse(role,"moc",chosen)!!.current == 20)
    val theaterRole = GameRole("genshin","masked","os_asia","")
    check(EndgameRecords.parse(theaterRole,"theater",obj("medal_num" to 12)) == null)
    check(EndgameRecords.parse(theaterRole,"theater",obj("data" to obj("stella_num" to 12)))!!.maximum == 12)
    check(EndgameRecords.parse(theaterRole,"theater",obj("stat" to obj("stella_count" to 12)))!!.current == 12)
    val deadlyRole = GameRole("zzz","masked","prod_gf_sg","")
    check(EndgameRecords.parse(deadlyRole,"deadly",obj("score" to 100000)) == null)
    check(EndgameRecords.parse(deadlyRole,"deadly",obj("total_star" to 9,"start_time" to 1700000000L,"end_time" to 1706000000L))!!.current == 9)
    check(EndgameRecords.parse(role,"apocalyptic",obj("star_num" to 12))!!.periodKey == null)
    println("Endgame v0.9.5 9 assertions OK")
}
