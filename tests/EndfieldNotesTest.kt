package com.gametodo.nativeapp
import org.json.JSONObject
class GameRole(val game:String,val uid:String)
class AccountGauge(val game:String,val uid:String,val metric:String,val current:Int,val maximum:Int,
    val periodKey:String?=null,val periodStartMs:Long?=null,val periodEndMs:Long?=null,
    val displayTitle:String="",val displayDetail:String="")
fun readNumber(root:JSONObject,vararg paths:String):Int? {
    for(path in paths) {
        var value:Any?=root
        for(part in path.split('.')) value=(value as? JSONObject)?.opt(part)
        if(value is Int)return value
    }
    return null
}
fun main() {
    fun obj(vararg p:Pair<String,Any?>)=JSONObject(mapOf(*p))
    val role=GameRole("endfield","fixture")
    val data=obj("dailyMission" to obj("dailyActivation" to 100,"maxDailyActivation" to 100),
        "weeklyMission" to obj("score" to 50,"total" to 100))
    check(EndfieldNotes.gauges(role,obj("detail" to data)).map {it.metric}==listOf("daily","weekly_mission"))
    check(EndfieldNotes.gauges(role,data).last().current==50)
    check(EndfieldNotes.gauges(role,obj("weeklyMission" to obj("score" to 10))).isEmpty())
    check(EndfieldNotes.gauges(role,obj("weeklyMission" to obj("score" to 0,"total" to 0))).isEmpty())
    check(EndfieldNotes.gauges(role,obj("weeklyMission" to obj("score" to -1,"total" to 100))).isEmpty())
    val now=1800000000000L
    fun boss(end:Long=1800003600,flag:Any=true)=obj("indieHard" to obj("indieHardGroups" to org.json.JSONArray(listOf(obj(
        "activityStartTs" to "1799996400","activityEndTs" to end.toString(),
        "dungeonGroups" to org.json.JSONArray(listOf(obj("normalDungeon" to obj("isPass" to flag),"hardDungeon" to obj("isPass" to false)))))))))
    val bossRows=EndfieldNotes.gauges(role,boss(),now)
    check(bossRows.size==2 && bossRows.first().current==1 && bossRows.last().current==0)
    check(bossRows.first().displayTitle=="그림자 이정표 · 일반")
    check(bossRows.first().displayDetail.contains("본체 클리어 기록"))
    check(EndfieldNotes.gauges(role,boss(end=1800000000),now).size==2)
    check(EndfieldNotes.gauges(role,boss(flag="true"),now).size==1) // string is not proven clear
    fun kst(value:String)=java.time.ZonedDateTime.parse(value+"+09:00[Asia/Seoul]").toInstant().toEpochMilli()
    check(GamePeriods.currentCycle("endfield","weekly",kst("2026-11-02T05:19:00"))==null)
    check(GamePeriods.currentCycle("endfield","weekly",kst("2026-11-02T05:20:00"))=="weekly:2026-11-02")
    println("Endfield weekly score is optional and separate from daily progress")
}
