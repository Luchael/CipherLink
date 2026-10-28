import com.gametodo.nativeapp.RecurrenceWindow
import java.time.LocalDate
import java.time.ZoneId

private fun kst(day: String) = LocalDate.parse(day).atTime(12,0)
    .atZone(ZoneId.of("Asia/Seoul")).toInstant().toEpochMilli()

fun main() {
    val weekly = RecurrenceWindow.Kind.WEEKLY
    // 자동 완료에서는 완료된 지난 시즌의 점수로 밀린 과거 회차를 체크하면 안 된다.
    check(!RecurrenceWindow.isCurrentOccurrence("2026-10-19","every monday",true,weekly,kst("2026-10-28")))
    check(RecurrenceWindow.isCurrentOccurrence("2026-10-26","every monday",true,weekly,kst("2026-10-28")))
    // 플로팅은 이전 회차도 보여준다. 서로 독립된 정책이어야 한다.
    check(RecurrenceWindow.isVisibleOutstanding("2026-10-19",kst("2026-10-28")))
    println("자동 완료 과거 회차 차단 / 플로팅 이전 회차 표시 분리 테스트 통과")
}
