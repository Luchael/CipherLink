import com.gametodo.nativeapp.TaskSupport
import com.gametodo.nativeapp.SafeFailure
import java.net.SocketTimeoutException

private fun entry(title: String, cadence: String, metric: String = "", status: String = "auto",
                  game: String = "genshin", note: String = "") =
    TaskSupport.Entry(game, title, cadence, metric, status, note)

fun main() {
    val daily = entry("[원신] 일퀘", "daily", "daily")
    val weekly = entry("[열차] 주간퀘스트", "weekly", "weekly", game = "hsr")
    val theater = entry("[원신] 환상극", "endgame", "theater")
    val spiral = entry("[원신] 나선", "endgame", "spiral")
    val moc = entry("[열차] 혼돈", "endgame", "moc", game = "hsr")
    val manual = entry("[스소] 연합토벌", "monthly", status = "manual", game = "stella", note = "개인 완료 기록 API 미확인")
    val ark = entry("[명방] 일퀘", "daily", "daily", "conditional", "arknights")
    val wuwa = entry("[명조] 탑", "rotation", "tower", "conditional", "wuthering", "글로벌 개인 전적 API 미확인")
    val colors = entry("[색지뢰] 일퀘", "daily", status = "manual", game = "colorsweeper", note = "개인 진행도 API 미확인")
    val entries = listOf(daily, weekly, theater, spiral, moc, manual, ark, wuwa, colors)
    val before = entries.toList()
    check(TaskSupport.group(daily) == "일일")
    check(TaskSupport.group(weekly) == "주간")
    check(TaskSupport.group(theater) == "월간" && TaskSupport.group(spiral) == "월간")
    check(TaskSupport.group(manual) == "월간")
    check(TaskSupport.group(moc) == "N일 주기" && TaskSupport.group(wuwa) == "N일 주기")
    for (item in entries.filter { it.status == "auto" }) {
        check(TaskSupport.description(item).contains(TaskSupport.autoDescription))
    }
    for (item in listOf(manual, ark, wuwa, colors)) check(TaskSupport.description(item).startsWith("수동 확인"))
    check(TaskSupport.description(ark).contains("23:59 KST 하루 1회"))
    check(TaskSupport.description(ark).contains("종료될 수"))
    check(TaskSupport.description(manual).contains(manual.note))
    val report = TaskSupport.report(entries)
    check(entries == before)
    for (item in entries) check(report.contains(item.title))
    check(report.contains("한국 서버가 있으면 한국 서버") && report.contains("없으면 글로벌 Asia"))
    check(report.contains("PC를 계속 켜둘 필요는 없습니다"))
    check(report.contains("정확한 시각을 보장하지 않습니다"))
    check(report.contains("실제 일정 응답은 아직 미검증"))
    check(report.contains("자동 등록은 보류"))
    check(report.contains("설치된 게임 앱 선택해서 연결"))
    check(TaskSupport.report(listOf(manual.copy(title = "새 공유 매핑 작업"))).contains("새 공유 매핑 작업"))

    val privateValue = "SYNTHETIC_PRIVATE_TOKEN"
    val error = IllegalStateException("https://example.invalid/?auth=$privateValue HTTP 403 HoYoLAB retcode=-100")
    val safe = SafeFailure.describe(error)
    check(safe.contains("HTTP 403") && safe.contains("retcode=-100"))
    check(!safe.contains(privateValue) && !safe.contains("https://"))
    val strange = object : Exception(privateValue) {}
    check(SafeFailure.describe(strange) == "조회 오류")
    check(SafeFailure.describe(SocketTimeoutException(privateValue)) == "시간 초과")
    check(!SafeFailure.describe(IllegalStateException("HTTP 999 retcode=123456789012345")).contains("999"))
    println("한국어 지원 현황·4주기·수동 경계·모바일 안내·비식별 오류 테스트 통과")
}
