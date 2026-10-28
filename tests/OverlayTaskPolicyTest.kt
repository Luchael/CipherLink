import com.gametodo.nativeapp.OverlayTaskPolicy
import com.gametodo.nativeapp.OverlayEventPolicy
import java.time.ZoneId
import java.time.ZonedDateTime

fun main() {
    fun epoch(day: String, h: Int, m: Int=0): Long =
        ZonedDateTime.of(java.time.LocalDate.parse(day),java.time.LocalTime.of(h,m),ZoneId.of("Asia/Seoul"))
            .toInstant().toEpochMilli()
    fun visible(name:String,due:String?,section:String="daily",excluded:Set<String> = setOf("event"),
                game:String="genshin",now:Long=epoch("2026-10-28",6)):Boolean =
        OverlayTaskPolicy.canDisplay(name,due,section,excluded,game,now)

    check(OverlayTaskPolicy.isEventSectionName("이벤트 / 기간 한정"))
    check(OverlayTaskPolicy.isEventSectionName("한정/이벤트"))
    check(OverlayTaskPolicy.isEventSectionName("가챠"))
    check(!OverlayTaskPolicy.isEventSectionName("매일"))
    check(!visible("[원신] 일퀘", "2026-10-28", "event"))
    check(!visible("[원신] 일퀘", "2026-10-29"))
    check(!visible("[원신] 일퀘", null))
    check(!visible("[원신] 일퀘", "2026-10-28", now=epoch("2026-10-28",4)))
    check(visible("[원신] 일퀘", "2026-10-28", now=epoch("2026-10-28",5,10)))
    check(visible("[원신] 일퀘", "2026-10-28", now=epoch("2026-10-28",5,30)))
    check(visible("[원신] 일퀘", "2026-10-27"))
    check(!visible("[원신] 환상극", "2026-10-28", now=epoch("2026-10-28",4)))
    check(!visible("[원신] 환상극", "2026-10-30", now=epoch("2026-10-28",4)))
    check(!visible("[열차] 주간퀘스트", "2026-10-26", game="hsr", now=epoch("2026-10-26",4)))
    check(visible("[열차] 주간퀘스트", "2026-10-26",game="hsr",now=epoch("2026-10-26",5,30)))
    check(!visible("[원신] 일퀘", "not-a-date"))
    check(!visible("[원신] 일퀘", "2026-10-29T02:00:00+09:00"))
    check(visible("[원신] 환상극", "2026-10-27T20:30:00Z")) // KST 28일 오전 5:30

    val other=OverlayEventPolicy.evaluate("com.example.browser","com.gametodo.nativeapp", "com.example.browser.MainActivity", false,true)
    check(other.kind == OverlayEventPolicy.Kind.HIDE_LATER && other.delayMs < 1000)
    check(OverlayEventPolicy.evaluate("com.sec.android.app.launcher","own",null,false,true).kind==OverlayEventPolicy.Kind.HIDE_LATER)
    check(OverlayEventPolicy.evaluate("com.samsung.android.game.gametools","own","PopupWindow",false,false).kind==OverlayEventPolicy.Kind.IGNORE)
    check(OverlayEventPolicy.evaluate("com.samsung.android.game.gamehome","own","com.samsung.android.game.gamehome.MainActivity",false,true).kind==OverlayEventPolicy.Kind.HIDE_LATER)
    check(OverlayEventPolicy.evaluate("com.discord","own","com.discord.MainActivity",false,false).kind==OverlayEventPolicy.Kind.HIDE_LATER)
    check(OverlayEventPolicy.evaluate("com.gametodo.nativeapp","com.gametodo.nativeapp","com.gametodo.nativeapp.MainActivity",false,true).kind==OverlayEventPolicy.Kind.HIDE_LATER)
    check(OverlayEventPolicy.evaluate("com.miHoYo.GI.samsung","own","MainActivity",true,false).kind==OverlayEventPolicy.Kind.GAME)
    println("플로팅 날짜·이벤트 제외·전경 앱 변경 테스트 통과")
}
