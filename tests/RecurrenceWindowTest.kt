import com.gametodo.nativeapp.RecurrenceWindow
import com.gametodo.nativeapp.RecurrenceWindow.Kind
import com.gametodo.nativeapp.OverlayTaskPolicy
import com.gametodo.nativeapp.GamePeriods
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId

private fun whenKst(day: String, hour: Int = 12, minute: Int = 0): Long =
    LocalDate.parse(day).atTime(LocalTime.of(hour,minute))
        .atZone(ZoneId.of("Asia/Seoul")).toInstant().toEpochMilli()

private fun show(due: String, repeat: String, kind: Kind, on: String,
                 game: String="genshin", hour: Int=12): Boolean =
    OverlayTaskPolicy.canDisplay("[원신] 테스트",due,"section",emptySet(),game,
        whenKst(on,hour),repeat,true,kind)

fun main() {
    // 과거의 반복 회차가 Todoist에서 미완료라면 기간이 지나도 반드시 남겨둔다.
    check(show("2026-10-19", "매주 월요일",Kind.WEEKLY,"2026-10-28"))
    check(show("2026-10-26", "매주 월요일",Kind.WEEKLY,"2026-11-02"))
    check(show("2026-10-26", "every monday",Kind.WEEKLY,"2026-11-16"))
    check(show("2026-10-26", "every 3 days",Kind.INTERVAL,"2026-11-20"))
    check(show("2026-10-26", "every! 3 days",Kind.INTERVAL,"2026-11-20"))
    check(show("2026-09-16", "매월 16일",Kind.MONTHLY,"2026-10-28"))
    check(show("2026-10-16", "every month",Kind.MONTHLY,"2026-12-31"))
    check(show("2026-10-16", "every 2 months",Kind.MONTHLY,"2027-01-01"))
    check(show("2026-10-16", "unknown complex rule",Kind.INTERVAL,"2026-10-28"))

    // 시작일이 미래면 숨긴다. 반복문구가 없더라도 과거의 미완료 할 일은 보여준다.
    check(!show("2026-11-02","every monday",Kind.WEEKLY,"2026-10-28"))
    check(!show("2026-11-16","매월 16일",Kind.MONTHLY,"2026-10-28"))
    check(!OverlayTaskPolicy.canDisplay("[원신] 주간퀘","2026-11-02","s",emptySet(),
        "genshin",whenKst("2026-10-28"),null,false,Kind.WEEKLY))
    check(OverlayTaskPolicy.canDisplay("[원신] 주간퀘","2026-10-26","s",emptySet(),
        "genshin",whenKst("2026-10-28"),null,false,Kind.WEEKLY))

    // 바로 '그 회차의 시작 날짜'에 게임 초기화 전이라면 숨기고, 초기화 후 표시한다.
    check(!show("2026-10-26","every monday",Kind.WEEKLY,"2026-10-26",hour=4))
    check(show("2026-10-26","every monday",Kind.WEEKLY,"2026-10-26",hour=5))
    check(!show("2026-10-28","every 4 days",Kind.INTERVAL,"2026-10-28",hour=4))
    check(show("2026-10-28","every 4 days",Kind.INTERVAL,"2026-10-28",hour=5))
    check(!show("2026-10-28","매월 28일",Kind.MONTHLY,"2026-10-28",hour=4))
    check(show("2026-10-28","매월 28일",Kind.MONTHLY,"2026-10-28",hour=5))
    // 주간 회차 시작 전 04시에도 '지난주'의 미완료 작업을 보여준다.
    check(show("2026-10-19","every monday",Kind.WEEKLY,"2026-10-26",hour=4))
    // 어제 작업은 오늘 게임 초기화 이전이어도 표시한다.
    check(show("2026-10-27","every day",Kind.DAILY,"2026-10-28",hour=2))
    check(!show("2026-10-28","every day",Kind.DAILY,"2026-10-28",hour=2))
    check(show("2026-10-28","every day",Kind.DAILY,"2026-10-28",hour=5))

    // 초기화 시각 미설정 게임은 오늘 회차를 보류하고 사용자 설정을 요구한다.
    check(!show("2026-10-28","every day",Kind.DAILY,"2026-10-28",game="arknights",hour=1))
    check(GamePeriods.currentCycle("hsr","weekly",whenKst("2026-10-28",2)) == null)

    check(!OverlayTaskPolicy.canDisplay("[원신] 가챠","2026-10-26","event",setOf("event"),
        "genshin",whenKst("2026-10-28"),null,true,Kind.INTERVAL))
    check(RecurrenceWindow.sectionKind("매달") == Kind.MONTHLY)
    check(RecurrenceWindow.sectionKind("N일") == Kind.INTERVAL)
    check(RecurrenceWindow.dateKst("2026-10-27T20:30:00Z") == LocalDate.parse("2026-10-28"))
    println("과거 미완료·당일 초기화 전 제외·반복 날짜·이벤트 섹션 테스트 통과")
}
