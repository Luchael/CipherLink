import com.gametodo.nativeapp.StellaBanners
import org.json.JSONObject
import java.io.File
import java.time.OffsetDateTime

fun main() {
    val raw = File("tests/fixtures/stella_kr_20261028.json").readText()
    val now = OffsetDateTime.parse("2026-10-28T12:00:00+09:00").toInstant().toEpochMilli()
    val rows = StellaBanners.parse(JSONObject(raw), now)
    check(rows.map { it.title }.toSet() == setOf("[스소] 세이나(기원)", "[스소] 호타루"))
    check(rows.map { it.key }.toSet() == setOf("2f3266e95c13d06d9517dfc6c8a58d53", "36a135446f4c068d79962e39afa6854a"))
    val row = JSONObject(raw).getJSONArray("current").getJSONObject(1)
    for (bad in listOf("2026-11-10", "", "2026-10-20T12:00:00+08:00")) {
        val broken = JSONObject(row.toString()).put("endTime", bad)
        check(StellaBanners.parse(JSONObject().put("current", org.json.JSONArray().put(broken)), now).isEmpty())
    }
    check(StellaBanners.parse(JSONObject(raw), OffsetDateTime.parse("2026-12-01T12:00:00+09:00").toInstant().toEpochMilli()).isEmpty())
    println("Actual KR fixture: 2 characters, PC/Android keys match, invalid/expired records excluded")
}
