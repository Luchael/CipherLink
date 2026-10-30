import com.gametodo.nativeapp.*
import java.time.ZonedDateTime
private fun at(text:String)=ZonedDateTime.parse(text+"+09:00[Asia/Seoul]").toInstant().toEpochMilli()
fun main() {
    check(GamePeriods.parseResetTime("05:30")==330)
    check(GamePeriods.parseResetTime("00:00")==0)
    for(bad in listOf("24:00","05:60","5:30","bad"," 05:00")) check(GamePeriods.parseResetTime(bad)==null)
    val before=at("2026-10-30T05:29:00");val after=at("2026-10-30T05:30:00")
    fun show(now:Long)=OverlayTaskPolicy.canDisplay("할 일","2026-10-30","daily",emptySet(),
        "label_custom",now,resetMinutes=330)
    check(!show(before));check(show(after))
    check(GamePeriods.currentCycle("label_custom","daily",at("2026-10-30T05:49:00"),resetMinutes=330)==null)
    check(GamePeriods.currentCycle("label_custom","daily",at("2026-10-30T05:50:00"),resetMinutes=330)=="2026-10-30")
    check(!OverlayTaskPolicy.canDisplay("할 일","2026-10-30","daily",emptySet(),"label_unknown",after))
    check(OverlayTaskPolicy.canDisplay("이전 미완료","2026-10-29","daily",emptySet(),"label_unknown",before))
    val draft=FloatingTaskDraft("할 일","2026-10-30","매 49일","p","s","게임")
    draft.validate();check(draft.copy().requestId==draft.requestId)
    for(invalid in listOf(draft.copy(title=" "),draft.copy(date="2026-02-30"),draft.copy(section=""),draft.copy(requestId="bad"))) {
        check(runCatching {invalid.validate()}.isFailure)
    }
    println("분 단위 초기화 설정·플로팅/자동 완료 공통 경계·미설정 차단·추가 요청 입력 검사 통과")
}
