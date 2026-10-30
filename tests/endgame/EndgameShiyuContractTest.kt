package com.gametodo.nativeapp

import org.json.JSONArray
import org.json.JSONObject

private fun shiyuObject(vararg pairs: Pair<String, Any?>) = JSONObject(mapOf(*pairs))

fun main() {
    val role = GameRole("zzz", "redacted", "prod_gf_sg", "")
    val partial = shiyuObject("hadal_ver" to "v2", "hadal_info_v2" to shiyuObject(
        "hadal_begin_time" to 1791000000L, "hadal_end_time" to 1801000000L,
        "pass_fifth_floor" to false, "fourth_layer_detail" to shiyuObject("rating" to "S")))
    val fourth = EndgameRecords.parse(role, "shiyu", partial)
    check(fourth != null && fourth.current == 1 && fourth.maximum == 4) {
        "Known fourth-frontier S was discarded because fifth-frontier record is absent"
    }
    val v1 = shiyuObject("hadal_ver" to "v1", "hadal_info_v1" to shiyuObject(
        "all_floor_detail" to JSONArray((1..7).map {
            shiyuObject("layer_id" to it, "layer_index" to it, "rating" to "S") })))
    val old = EndgameRecords.parse(role, "shiyu", v1)
    check(old != null && old.current == 7 && old.maximum == 7)
    check(EndgameRecords.parse(role, "shiyu", shiyuObject("hadal_ver" to "v2",
        "hadal_info_v2" to shiyuObject("total_star" to 5, "max_star" to 5))) == null)
    fun full(passed: Boolean, duplicate: Boolean = false, fourth: Boolean = true): JSONObject {
        val record = mutableMapOf<String,Any?>(
            "pass_fifth_floor" to passed,
            "hadal_begin_time" to 1791000000L, "hadal_end_time" to 1801000000L,
            "fitfh_layer_detail" to shiyuObject("layer_challenge_info_list" to JSONArray((0..2).map {
                // A low score cannot override an explicit server S rating.
                shiyuObject("layer_id" to (if (duplicate) 0 else it), "rating" to "S", "score" to 100)
            })))
        if (fourth) record["fourth_layer_detail"] = shiyuObject("rating" to "S")
        return JSONObject(record) // SDK-unwrapped form must work on Android too.
    }
    val complete = EndgameRecords.parse(role,"shiyu",full(true))!!
    check(complete.current == 4 && complete.maximum == 4 && complete.filled)
    val hold = EndgameRecords.parse(role,"shiyu",full(false))!!
    check(hold.current == 4 && !hold.filled && hold.displayDetail.contains("자동 완료 보류"))
    val fifthOnly = EndgameRecords.parse(role,"shiyu",full(true, fourth=false))!!
    check(fifthOnly.current == 3 && !fifthOnly.filled)
    check(EndgameRecords.parse(role,"shiyu",full(true, duplicate=true)) == null)
    val counts = EndgameRecords.parse(role,"shiyu",shiyuObject("rating_list" to JSONArray(listOf(
        shiyuObject("rating" to "S","times" to 6),shiyuObject("rating" to "A","times" to 1)))))!!
    check(counts.current == 6 && counts.maximum == 7 && !counts.filled)
    val unsafe = shiyuObject("hadal_ver" to "DO_NOT_ECHO", "nick_name" to "DO_NOT_ECHO")
    check(!EndgameRecords.shiyuDiagnostic(unsafe).contains("DO_NOT_ECHO"))
    val unattempted = shiyuObject("hadal_ver" to "v2", "hadal_info_v2" to shiyuObject(
        "zone_id" to 1, "has_data" to false, "pass_fifth_floor" to false,
        "hadal_begin_time" to 1791000000L, "hadal_end_time" to 1801000000L))
    val zero = EndgameRecords.parse(role,"shiyu",unattempted)!!
    check(zero.current == 0 && zero.maximum == 4 && !zero.filled && !zero.hasRecord && zero.displayDetail.contains("미도전"))
    check(EndgameRecords.parse(role,"shiyu",shiyuObject("zone_id" to 1, "pass_fifth_floor" to false)) == null)
    check(EndgameRecords.parse(role,"shiyu",shiyuObject("hadal_ver" to "v2", "hadal_info_v2" to shiyuObject(
        "pass_fifth_floor" to false, "brief" to shiyuObject("score" to 30000),
        "hadal_begin_time" to 1791000000L, "hadal_end_time" to 1801000000L))) == null)
    println("Shiyu raw API contract checks OK")
}
