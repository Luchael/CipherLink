package com.gametodo.nativeapp
import org.json.JSONArray
import java.time.Instant
import org.json.JSONObject

private fun obj(vararg pairs: Pair<String, Any?>) = JSONObject(mapOf(*pairs))

fun main() {
    val gen=GameRole("genshin","masked","os_asia","")
    val hsr=GameRole("hsr","masked","prod_official_asia","")
    val zzz=GameRole("zzz","masked","prod_gf_sg","")
    val s=1791000000L; val e=1801000000L
    val theater=obj("data" to JSONArray(listOf(
        obj("schedule" to obj("schedule_type" to 2,"start_time" to s-2000000,"end_time" to s-1000000),
            "stat" to obj("star_challenge_stellas" to JSONArray(List(12){true}))),
        obj("schedule" to obj("schedule_type" to 1,"start_time" to s,"end_time" to e),
            "stat" to obj("star_challenge_stellas" to JSONArray(List(11){true}+false)))
    )),"is_unlock" to true,"links" to JSONArray(),"tarot_card_state" to obj())
    val t=EndgameRecords.parse(gen,"theater",theater)!!
    check(t.current==11 && t.maximum==12 && t.periodKey!=null)
    check(EndgameRecords.parse(gen,"theater",obj("medal_num" to 12))==null)
    val scores=obj("start_time" to s,"end_time" to e,"challenges" to JSONArray(listOf(
        obj("score" to 20000),obj("score" to 24000),obj("score" to 45000))))
    val d=EndgameRecords.parse(zzz,"deadly",scores)!!
    check(d.current==9 && d.maximum==9 && d.periodKey!=null)
    val bad=EndgameRecords.parse(zzz,"deadly",obj("challenges" to JSONArray(listOf(
        obj("score" to 40000),obj("score" to 10000),obj("score" to 10000)))))!!
    check(bad.current==5)
    check(EndgameRecords.parse(zzz,"deadly",obj("total_score" to 90000))==null)
    // 시유에는 별 개수를 S 등급으로 치환하는 경로가 없어야 한다.
    check(EndgameRecords.parse(zzz,"shiyu",obj("hadal_ver" to "v2",
        "hadal_info_v2" to obj("brief_info" to obj("total_star" to 5,"max_star" to 5)))) == null)
    val nested=EndgameRecords.parse(zzz,"shiyu",obj("hadal_ver" to "v2",
        "hadal_info_v2" to obj("begin_time" to s,"end_time" to e,
        "fourth_layer_detail" to obj("rating" to "S"))))!!
    check(nested.periodKey!=null && nested.current==1)
    val extended=EndgameRecords.parse(hsr,"moc",obj("begin_time" to s,"end_time" to e,
        "total_star" to 36,"max_star" to 48))!!
    check(extended.current==36 && extended.maximum==48)
    val arbitration=EndgameRecords.parse(hsr,"arbitration",obj("begin_time" to s,"end_time" to e,
        "summary" to obj("mini_boss_stars" to 9,"boss_stars" to 3)))!!
    check(arbitration.current==12 && arbitration.periodKey!=null)
    val realTheater=obj("data" to JSONArray(listOf(obj(
        "schedule" to obj("schedule_type" to 1,"start_time" to s,"end_time" to e),
        "stat" to obj("get_medal_round_list" to JSONArray(List(12){true}))))))
    check(EndgameRecords.parse(gen,"theater",realTheater)?.current == 12)
    // v0.9.8: 응답 list의 첫 요소로 진입하면 total_star가 사라지는 회귀를 방지.
    val actualDeadly=obj("start_time" to s,"end_time" to e,"total_star" to 9,
        "total_score" to 80000,"list" to JSONArray(listOf(obj("score" to 30000))))
    check(EndgameRecords.parse(zzz,"deadly",actualDeadly)?.current == 9)
    val theaterInts=obj("data" to JSONArray(listOf(obj(
        "schedule" to obj("schedule_type" to 1,"start_time" to s,"end_time" to e),
        "stat" to obj("get_medal_round_list" to JSONArray(List(11){1}+0))))))
    check(EndgameRecords.parse(gen,"theater",theaterInts)?.current == 11)
    val theaterRoundIds=obj("data" to JSONArray(listOf(obj(
        "schedule" to obj("schedule_type" to 1,"start_time" to s,"end_time" to e),
        "stat" to obj("get_medal_round_list" to JSONArray((1..12).toList()))))))
    check(EndgameRecords.parse(gen,"theater",theaterRoundIds) == null)
    val deadlyParams=EndgameRecords.queryFor(zzz,"deadly")
    check(deadlyParams.startsWith("uid="))
    check("&region=" in deadlyParams && "role_id=" !in deadlyParams)
    check(EndgameRecords.queryFor(zzz,"shiyu").startsWith("role_id="))
    val newNested=EndgameRecords.parse(zzz,"shiyu",obj("hadal_ver" to "v2",
        "hadal_info_v2" to obj("hadal_begin_time" to s,"hadal_end_time" to e,
        "fourth_layer_detail" to obj("rating" to "S"))))!!
    check(newNested.periodKey != null)
    val noSeason=EndgameRecords.parse(hsr,"moc",obj("total_star" to 36))!!
    check(noSeason.periodKey==null)
    check(!EndgameRecords.currentPeriod(noSeason,Instant.now().toEpochMilli()))
    println("Endgame v0.9.8 regression assertions OK")
}
