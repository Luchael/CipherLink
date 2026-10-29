package com.gametodo.nativeapp

import org.json.JSONObject
import org.json.JSONArray
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/** User-confirmed Monday score binding plus optional display-only boss periods. */
object EndfieldNotes {
    fun gauges(role: GameRole, payload: JSONObject, nowMillis: Long = System.currentTimeMillis()): List<AccountGauge> {
        val detail=(payload.opt("detail") as? JSONObject) ?: payload
        val result=mutableListOf<AccountGauge>()
        fun add(metric:String,current:String,maximum:String) {
            val cur=readNumber(detail,current);val max=readNumber(detail,maximum)
            if(cur!=null && cur>=0 && max!=null && max>0)
                result+=AccountGauge("endfield",role.uid,metric,cur,max)
        }
        add("daily","dailyMission.dailyActivation","dailyMission.maxDailyActivation")
        add("weekly_mission","weeklyMission.score","weeklyMission.total")
        val groups=(detail.opt("indieHard") as? JSONObject)?.opt("indieHardGroups") as? JSONArray ?: return result
        val format=DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm").withZone(ZoneId.of("Asia/Seoul"))
        fun epoch(o:JSONObject,key:String):Long? {
            val value=o.opt(key)?.toString()?.toLongOrNull() ?: return null
            return value.takeIf {it in 1_500_000_000L..5_000_000_000L}?.times(1000L)
        }
        val candidates=(0 until groups.length()).mapNotNull {i->groups.optJSONObject(i)?.let {g->epoch(g,"activityStartTs")?.takeIf {it<=nowMillis}?.let {Triple(i,g,it)}}}
        val latest=candidates.maxOfOrNull {it.third}
        for((index,group,start) in candidates) {
            if(start!=latest) continue
            val end=epoch(group,"activityEndTs")
            val rows=group.opt("dungeonGroups") as? JSONArray ?: continue
            if(rows.length()==0) continue
            val opened=format.format(Instant.ofEpochMilli(start))
            val bonus=if(end!=null && end>start) format.format(Instant.ofEpochMilli(end))+" KST"+(if(nowMillis>=end) " (종료)" else "") else "정보 없음"
            for((field,name) in listOf("normalDungeon" to "일반","hardDungeon" to "고난도")) {
                val flags=(0 until rows.length()).map {i->
                    (rows.optJSONObject(i)?.opt(field) as? JSONObject)?.opt("isPass")
                }
                if(flags.any {it !is Boolean}) continue
                result+=AccountGauge("endfield",role.uid,"umbral_${index}_$field",flags.count {it==true},flags.size,
                    displayTitle="그림자 이정표 · $name",
                    displayDetail="최신 시리즈 개방 $opened KST · 부가 이벤트 종료 $bonus · 본체 클리어 기록")
            }
        }
        return result
    }
}
