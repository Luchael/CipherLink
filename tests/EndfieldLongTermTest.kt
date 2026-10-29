package com.gametodo.nativeapp
import org.json.JSONObject
import org.json.JSONArray
private fun obj(vararg p:Pair<String,Any?>)=JSONObject(mapOf(*p))
fun main() {
    val role=GameRole("endfield","fixture","asia","")
    val begin=1793232000L;val end=begin+7*86400L;val now=(begin+3600)*1000
    fun dungeon(normal:Any=true,hard:Any=true)=obj("normalDungeon" to obj("isPass" to normal),"hardDungeon" to obj("isPass" to hard))
    fun umbral(hard:Any=true)=obj("indieHard" to obj("indieHardGroups" to JSONArray(listOf(obj(
        "activityStartTs" to begin.toString(),"activityEndTs" to end.toString(),"dungeonGroups" to JSONArray(listOf(dungeon(hard=hard))))))))
    check(EndfieldLongTerm.umbral(role,umbral(),now)!!.current==2)
    check(EndfieldLongTerm.umbral(role,umbral(false),now)!!.current==1)
    check(EndfieldLongTerm.umbral(role,umbral("true"),now)==null)
    fun crisis(done:Boolean=true,minimal:Boolean=false,gameplayEnd:Long?=null):JSONObject {
        val counts=if(minimal) emptyList() else listOf("weeklyMission" to obj("count" to 1,"total" to 1),
            "indicatorMission" to obj("count" to 1,"total" to 1),"stageMission" to obj("count" to if(done) 1 else 0,"total" to 1),
            "achieve" to obj("isPlated" to done))
        return obj("crisisContract" to JSONObject(mapOf("id" to "fixture","startAtTs" to begin.toString(),"endAtTs" to end.toString())+counts+(if(gameplayEnd==null) emptyList() else listOf("gameplayEndAtTs" to gameplayEnd.toString()))).let {obj("status" to it)})
    }
    fun ready(data:JSONObject,time:Long=now)=EndfieldLongTerm.crisis(role,data,time).first {it.metric=="crisis_complete"}.current
    check(ready(crisis())==1 && ready(crisis(false))==0)
    check(ready(crisis(minimal=true))==0 && ready(crisis(minimal=true),end*1000)==1)
    check(EndfieldLongTerm.crisis(role,obj("code" to 1001,"data" to crisis()),now).none {it.metric=="crisis_complete"})
    val gameplay=crisis(false,gameplayEnd=end-86400)
    check(ready(gameplay,(end-86400)*1000)==1)
    check(!EndfieldLongTerm.verifiedResponse(obj("code" to 1001)))
    check(EndfieldLongTerm.verifiedResponse(obj("code" to 0,"data" to crisis())))
    fun war(plus:Boolean)=obj("warEchoes" to obj("seasons" to JSONArray(listOf(obj("weeks" to JSONArray(listOf(obj(
        "startTs" to begin.toString(),"endTs" to end.toString(),"allPlusTasks" to plus,"stars" to 9,
        "dungeonGroups" to JSONArray(listOf(obj("normalDungeon" to obj("isPass" to true),
            "hardDungeon" to obj("isPass" to true),"cruelDungeon" to obj("isPass" to true))))))))))))
    check(EndfieldLongTerm.war(role,war(true),now).first {it.metric=="war_complete"}.current==4)
    check(EndfieldLongTerm.war(role,war(false),now).first {it.metric=="war_complete"}.current==3)
    check(EndfieldLongTerm.war(role,war(true),end*1000).none {it.metric=="war_complete"})
    println("Endfield goals require strict flags; crisis accepts verified expiry; war uses current week")
}
