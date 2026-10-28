import com.gametodo.nativeapp.BannerSource
import com.gametodo.nativeapp.GameRules
import java.io.ByteArrayInputStream
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLConnection
import java.net.URLStreamHandler
import java.time.ZonedDateTime

/** Actual fetch + Jsoup parser with an in-memory HTTPS response; no game login. */
fun main() {
    val game = GameRules.Game("wuthering", "명조: 워더링 웨이브", "명조", "명조", 5, emptyList())
    val now = ZonedDateTime.parse("2026-10-28T12:00:00+09:00").toInstant().toEpochMilli()
    var body = ""
    var requestCount = 0
    URL.setURLStreamHandlerFactory { protocol ->
        if (protocol != "https") null else object : URLStreamHandler() {
            override fun openConnection(url: URL): URLConnection {
                check(url.toString() == "https://www.pickupcal.com/games/wuthering/")
                requestCount++
                return object : HttpURLConnection(url) {
                    override fun connect() = Unit
                    override fun disconnect() = Unit
                    override fun usingProxy() = false
                    override fun getResponseCode() = 200
                    override fun getInputStream() = ByteArrayInputStream(body.toByteArray(Charsets.UTF_8))
                }
            }
        }
    }
    fun card(label: String = "[픽업] ${game.name} - 「소집 이름」 - 금희",
             start: String = "2026-10-20 11:00", end: String = "2026-11-10 10:59",
             region: String = "한국 서버") =
        "<li><a href='/banners/fixture'>$label</a>$region 시작 $start · 종료 $end</li>"
    fun fetch(html: String, header: String = "한국 서버 일정 KST") = run {
        body = "<h1>$header</h1>$html"
        BannerSource.fetch(game, now)
    }
    val found = fetch(card())
    check(requestCount == 1) // catches an early wuthering-specific return before fetch
    check(found.size == 1)
    val banner = found.single()
    check(banner.title == "[명조] 금희")
    check(banner.startDate == "2026-10-20")
    check(banner.sourceUrl == "https://www.pickupcal.com/banners/fixture")
    check(banner.key == "0928a4a1d4e56d0a09d7a2382ae3f6cf") // shared PC fixture
    check(banner.endMillis == ZonedDateTime.parse("2026-11-10T10:59:00+09:00").toInstant().toEpochMilli())

    val rejected = listOf(
        card("[픽업] ${game.name} - 무기 픽업 - 무기"),
        card("[이벤트] ${game.name} - 「축제」 - 캐릭터"),
        card(end = "2026-10-28 12:00"),
        card(start = "2026-11-01 11:00"),
        card(start = "2026-10-20", end = "2026-11-10"),
        card(region = "서버 미상"),
        card("[픽업] 다른 게임 - 「소집」 - 캐릭터"),
        "<div>새 구조: 일정 미확인</div>"
    )
    rejected.forEach { check(fetch(it).isEmpty()) }
    check(fetch(card(), "한국 서버 CST").isEmpty())
    check(fetch(card(region = "Asia"), "Global Asia UTC+8").isEmpty())
    check(fetch("").isEmpty())
    println("BannerSourcePolicyTest: 1 accepted and ${rejected.size + 3} rejected in-memory fetch/parser cases passed; no live API verified")
}
