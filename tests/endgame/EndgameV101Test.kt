package com.gametodo.nativeapp
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
private fun j101(vararg args: Pair<String,Any?>) = JSONObject(mapOf(*args))
fun main() {
 val role=GameRole("zzz","redacted","prod_gf_sg","")
 val now=Instant.now().epochSecond
 fun make(scores: List<Int>, fourth: String="S", pass: Boolean=true): JSONObject =
    j101("hadal_ver" to "v2", "hadal_info_v2" to j101(
      "begin_time" to now-3600,"end_time" to now+3600,"pass_fifth_floor" to pass,
      "fourth_layer_detail" to j101("rating" to fourth),
      "fitfh_layer_detail" to j101("layer_challenge_info_list" to
          JSONArray(scores.map { j101("score" to it) }))))
 val yes=EndgameRecords.parse(role,"shiyu",make(listOf(26390,48516,45724)))!!
 check(yes.current==4 && yes.maximum==4)
 check(EndgameRecords.currentPeriod(yes,System.currentTimeMillis()))
 check(EndgameRecords.parse(role,"shiyu",make(listOf(50000,20000,20000)))!!.current==2)
 check(EndgameRecords.parse(role,"shiyu",make(listOf(26390,48516,45724),"A"))!!.current==3)
 check(EndgameRecords.parse(role,"shiyu",make(listOf(26390,48516,45724),pass=false))!!.current==3)
 check(EndgameRecords.parse(role,"shiyu",make(listOf(26390,48516,45724),"?"))==null)
 println("Shiyu S grade (4th+3 fifth rooms) tests OK")
}
