import com.gametodo.nativeapp.*
import java.time.ZonedDateTime
fun main() {
    fun kst(s:String)=ZonedDateTime.parse(s+"+09:00[Asia/Seoul]").toInstant().toEpochMilli()
    val start=kst("2026-10-29T09:00:00");val end=start+7*86400000L;val now=kst("2026-10-29T12:00:00")
    fun key(due:String="2026-10-29",days:Int=49,mode:String="goal",time:Long=now,rule:String="every 49 days",begin:Long=start,finish:Long=end)=
        FixedIntervals.occurrence(due,true,days,begin,finish,mode,time,rule)
    check(key()=="interval:49:${start/1000}:${end/1000}")
    check(key(rule="every7weeks")==key())
    check(key(rule="매49일")==key())
    check(key(rule="every21days")==null)
    check(key(due="2026-10-30")==null)
    check(key(due="2026-08-01")==null)
    check(key(begin=start-7*86400000L,finish=start+8*3600000L)==null)
    check(key(days=7,rule="매주 목요일")!=null)
    check(key(days=7,rule="every 2 weeks")==null)
    check(key(days=147,mode="goal_or_expiry",time=end+86400000L,rule="every 21 weeks")!=null)
    check(key(time=end+86400000L)==null)
    check(FixedIntervals.occurrence("2026-10-29",false,49,start,end,"goal",now,"every49days")==null)
    check(FixedIntervals.occurrence("2026-10-29",true,49,start,null,"series_goal",now,"every 49 days")=="interval:49:series:${start/1000}")
    check(FixedIntervals.occurrence("2026-12-17",true,49,start,null,"series_goal",now+49*86400000L,"every 49 days")==null)
    println("Fixed Todoist intervals preserve recurrence and match verified source windows")
}
