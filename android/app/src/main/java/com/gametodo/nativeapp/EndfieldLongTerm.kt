package com.gametodo.nativeapp

import org.json.JSONObject
import org.json.JSONArray
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/** Optional read-only API contracts. Missing evidence is never a completed goal. */
object EndfieldLongTerm {
    private fun body(payload:JSONObject?):JSONObject? {
        if(payload==null) return null
        for(key in listOf("code","status")) {
            val value=payload.opt(key) ?: continue
            val zero=when(value) {is Int->value==0;is Long->value==0L;is String->value=="0";else->false}
            if(!zero) return null
        }
        return payload.optJSONObject("data") ?: payload
    }
    fun verifiedResponse(payload:JSONObject):Boolean = body(payload)!=null && (payload.opt("code")!=null || payload.opt("status")!=null)
    private fun epoch(o:JSONObject,key:String):Long? {
        val n=o.opt(key)?.toString()?.toLongOrNull() ?: return null
        val seconds=if(n>1_000_000_000_000L) n/1000 else n
        return seconds.takeIf {it in 1_500_000_000L..5_000_000_000L}?.times(1000)
    }
    fun umbral(role:GameRole,payload:JSONObject,now:Long):AccountGauge? {
        val detail=payload.optJSONObject("detail") ?: payload
        val groups=detail.optJSONObject("indieHard")?.optJSONArray("indieHardGroups") ?: return null
        val candidates=(0 until groups.length()).mapNotNull {i->
            groups.optJSONObject(i)?.let {g->epoch(g,"activityStartTs")?.takeIf {it<=now}?.let {it to g}}
        }
        val latest=candidates.maxOfOrNull {it.first} ?: return null
        val flags=mutableListOf<Boolean>()
        for((start,group) in candidates) {
            if(start!=latest) continue
            val rows=group.optJSONArray("dungeonGroups") ?: return null
            if(rows.length()==0) return null
            for(j in 0 until rows.length()) for(key in listOf("normalDungeon","hardDungeon")) {
                val pass=rows.optJSONObject(j)?.optJSONObject(key)?.opt("isPass")
                if(pass !is Boolean) return null
                flags+=pass
            }
        }
        if(flags.isEmpty()) return null
        return AccountGauge("endfield",role.uid,"umbral_complete",flags.count {it},flags.size,
            periodKey="umbral:$latest:open",periodStartMs=latest)
    }
    fun crisis(role:GameRole,payload:JSONObject?,now:Long):List<AccountGauge> {
        val root=body(payload)
        val status=root?.optJSONObject("crisisContract")?.optJSONObject("status")
        val start=status?.let {epoch(it,"startAtTs")};val overallEnd=status?.let {epoch(it,"endAtTs")}
        val gameplayEnd=status?.let {epoch(it,"gameplayEndAtTs")}
        val end=gameplayEnd ?: overallEnd
        if(status==null || start==null || end==null || start>=end || overallEnd==null || end>overallEnd || status.optString("id") in setOf("","0","null"))
            return listOf(AccountGauge("endfield",role.uid,"crisis_status",0,0,displayTitle="위기 협약",displayOnly=true,
                displayDetail="글로벌 API 기록 미확인 · 자동 완료 보류"))
        val result=mutableListOf<AccountGauge>();val checks=mutableListOf<Boolean>()
        for((key,title) in listOf("weeklyMission" to "주간 임무","indicatorMission" to "지표 임무","stageMission" to "스테이지 임무")) {
            val cur=readNumber(status,"$key.count");val total=readNumber(status,"$key.total")
            val valid=cur!=null && cur>=0 && total!=null && total>0
            checks+=valid && cur!!>=total!!
            if(valid) result+=AccountGauge("endfield",role.uid,"crisis_$key",cur!!,total!!,displayTitle="위기 협약 · $title",periodKey="crisis:$start:$end",periodStartMs=start,periodEndMs=end)
        }
        val plated=status.optJSONObject("achieve")?.opt("isPlated")
        val goals=checks.all {it} && plated==true
        result+=AccountGauge("endfield",role.uid,"crisis_complete",if(now>=end || (now>=start && goals)) 1 else 0,1,
            periodKey="crisis:$start:$end",periodStartMs=start,periodEndMs=end)
        val format=DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm").withZone(ZoneId.of("Asia/Seoul"))
        result+=AccountGauge("endfield",role.uid,"crisis_status",0,0,displayTitle="위기 협약 기간",displayOnly=true,
            displayDetail="${format.format(Instant.ofEpochMilli(start))} ~ ${format.format(Instant.ofEpochMilli(end))} KST · 21주 반복 유지 · "+
                (if(goals) "모든 목표 확인됨" else "목표·보상 확인 또는 종료 시 완료")+" · 도금 훈장 "+when(plated) {true->"예";false->"아니오";else->"미확인"})
        return result
    }
    fun war(role:GameRole,payload:JSONObject?,now:Long):List<AccountGauge> {
        val root=body(payload)
        val seasons=root?.optJSONObject("warEchoes")?.optJSONArray("seasons")
        val active=mutableListOf<Triple<JSONObject,Long,Long>>()
        if(seasons!=null) for(i in 0 until seasons.length()) {
            val weeks=seasons.optJSONObject(i)?.optJSONArray("weeks") ?: continue
            for(j in 0 until weeks.length()) {
                val week=weeks.optJSONObject(j) ?: continue
                val start=epoch(week,"startTs") ?: continue;val end=epoch(week,"endTs") ?: continue
                if(now>=start && now<end) active+=Triple(week,start,end)
            }
        }
        if(active.size!=1) return listOf(AccountGauge("endfield",role.uid,"war_status",0,0,displayTitle="전쟁의 메아리",displayOnly=true,
            displayDetail="글로벌 API 현재 주차 기록 미확인 · 자동 완료 보류"))
        val (week,start,end)=active.single();val rows=week.optJSONArray("dungeonGroups")
        if(rows==null || rows.length()==0) return emptyList()
        val result=mutableListOf<AccountGauge>();val flags=mutableListOf<Boolean>()
        for((key,title) in listOf("normalDungeon" to "일반","hardDungeon" to "고난도","cruelDungeon" to "극난도")) {
            val values=(0 until rows.length()).map {i->rows.optJSONObject(i)?.optJSONObject(key)?.opt("isPass")}
            if(values.all {it is Boolean}) {
                result+=AccountGauge("endfield",role.uid,"war_$key",values.count {it==true},values.size,displayTitle="전쟁의 메아리 · $title",periodKey="war:$start:$end",periodStartMs=start,periodEndMs=end)
                flags+=values.map {it==true}
            } else flags+=false
        }
        val plus=week.opt("allPlusTasks");flags+=plus==true
        result+=AccountGauge("endfield",role.uid,"war_complete",flags.count {it},flags.size,
            periodKey="war:$start:$end",periodStartMs=start,periodEndMs=end)
        val format=DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm").withZone(ZoneId.of("Asia/Seoul"))
        val points=readNumber(week,"stars")?.toString() ?: "미확인"
        result+=AccountGauge("endfield",role.uid,"war_status",0,0,displayTitle="전쟁의 메아리",displayOnly=true,
            displayDetail="${format.format(Instant.ofEpochMilli(start))} ~ ${format.format(Instant.ofEpochMilli(end))} KST · 매주 반복 · 별 ${points}개 · 추가 목표 "+
                when(plus) {true->"완료";false->"미완료";else->"미확인"})
        return result
    }

}
