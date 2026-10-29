package com.gametodo.nativeapp

import java.time.Instant
import java.time.ZoneId

/** User-fixed recurrence; neither Todoist dates nor recurrence strings are rewritten. */
object FixedIntervals {
    private val kst=ZoneId.of("Asia/Seoul")
    fun occurrence(due:String?,recurring:Boolean,days:Int?,begin:Long?,end:Long?,mode:String,now:Long,rule:String?):String? {
        if(mode !in setOf("goal","goal_or_expiry","series_goal")) return null
        if(!recurring || days==null || days !in 1..366 || begin==null) return null
        if(begin !in 1_500_000_000_000L..5_000_000_000_000L) return null
        if(mode!="series_goal" && (end==null || begin>=end || end>5_000_000_000_000L)) return null
        if(RecurrenceWindow.fixedDays(rule)!=days) return null
        val date=RecurrenceWindow.dateKst(due) ?: return null
        val today=Instant.ofEpochMilli(now).atZone(kst).toLocalDate()
        if(today<date || !today.isBefore(date.plusDays(days.toLong()))) return null
        val a=date.atStartOfDay(kst).toInstant().toEpochMilli()
        val b=date.plusDays(days.toLong()).atStartOfDay(kst).toInstant().toEpochMilli()
        if(begin<a || begin>=b || (mode!="series_goal" && end!!<=a)) return null
        if(mode=="series_goal") return if(now>=begin+1_200_000L) "interval:$days:series:${begin/1000}" else null
        if(mode=="goal" && (now<begin+1_200_000L || now>=end!!)) return null
        if(mode=="goal_or_expiry" && now<begin+1_200_000L) return null
        return "interval:$days:${begin/1000}:${end!!/1000}"
    }
}
