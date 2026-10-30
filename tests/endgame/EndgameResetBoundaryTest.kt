import com.gametodo.nativeapp.*
import java.time.ZonedDateTime

private fun kst(text:String) = ZonedDateTime.parse(text+"+09:00[Asia/Seoul]").toInstant().toEpochMilli()
fun main() {
    val reset=kst("2026-10-30T05:00:00")
    val old=AccountGauge("zzz","synthetic","shiyu",4,4,periodKey="old",
        periodStartMs=kst("2026-10-16T05:00:00"),periodEndMs=reset)
    check(!EndgameRecords.currentPeriod(old,kst("2026-10-30T04:59:00"))) {
        "초기화 당일 05시 전의 이전 시유 기록을 자동 완료 근거로 허용함"
    }
    check(!EndgameRecords.currentPeriod(old,kst("2026-10-30T05:21:00")))
    val fresh=AccountGauge("zzz","synthetic","shiyu",4,4,periodKey="new",
        periodStartMs=reset,periodEndMs=kst("2026-11-13T05:00:00"))
    check(!EndgameRecords.currentPeriod(fresh,kst("2026-10-30T05:19:00")))
    check(EndgameRecords.currentPeriod(fresh,kst("2026-10-30T05:20:00")))
    check(!GamePeriods.seasonMatchesTask("zzz","2026-10-30",old.periodStartMs,
        kst("2026-10-31T05:00:00"),kst("2026-10-30T06:00:00")))
    check(GamePeriods.seasonMatchesTask("zzz","2026-10-30",fresh.periodStartMs,
        fresh.periodEndMs,kst("2026-10-30T06:00:00")))
    println("시유 초기화 전 이전 회차 차단 / 초기화 후 만료 기록 차단 / 새 회차 1회 확인 통과")
}
