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
        for(index in 0 until groups.length()) {
            val group=groups.optJSONObject(index) ?: continue
            if(group.opt("isInActivity")==false) continue
            val start=epoch(group,"activityStartTs") ?: continue
            val end=epoch(group,"activityEndTs") ?: continue
            if(nowMillis<start || nowMillis>=end) continue
            val rows=group.opt("dungeonGroups") as? JSONArray ?: continue
            if(rows.length()==0) continue
            val span=(end-start)/1000
            val length=if(span%86400==0L) "${span/86400}일" else "${span/86400}일 ${span%86400/3600}시간"
            val period="${format.format(Instant.ofEpochMilli(start))} ~ ${format.format(Instant.ofEpochMilli(end))} KST"
            for((field,name) in listOf("normalDungeon" to "일반","hardDungeon" to "고난도")) {
                val flags=(0 until rows.length()).map {i->
                    (rows.optJSONObject(i)?.opt(field) as? JSONObject)?.opt("isPass")
                }
                if(flags.any {it !is Boolean}) continue
                result+=AccountGauge("endfield",role.uid,"umbral_${index}_$field",flags.count {it==true},flags.size,
                    periodKey="umbral:$start:$end",periodStartMs=start,periodEndMs=end,
                    displayTitle="그림자 이정표 · $name",
                    displayDetail="이번 운영 기간 $period ($length) · 반복 주기 미확인 · 읽기 전용")
            }
        }
        return result
    }
}
