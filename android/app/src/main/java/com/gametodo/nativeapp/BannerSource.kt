package com.gametodo.nativeapp

import org.jsoup.Jsoup
import java.net.URL
import java.net.HttpURLConnection
import java.nio.charset.StandardCharsets
import java.text.Normalizer
import java.security.MessageDigest
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter

/**
 * 한국 서버(KST)가 명시된 공개 페이지에서 캐릭터 픽업만 수집.
 * 기존 일반 이벤트, 무기/광추/음동기 픽업, 서버 출처가 불명확한 항목은 등록하지 않는다.
 * 동일한 게임·캐릭터·시작 시각이면 PC와 모바일에서 같은 키를 만든다.
 */
data class BannerRecord(val game: String, val key: String, val title: String,
                        val label: String, val startDate: String, val endMillis: Long, val description: String,
                        val sourceUrl: String)

object BannerSource {
    private val games = setOf("genshin", "hsr", "zzz", "wuthering", "limbus", "endfield")
    private val dates = Regex("(\\d{4}-\\d{2}-\\d{2}\\s+\\d{2}:\\d{2})")
    private val primary = Regex("시작\\s*(\\d{4}-\\d{2}-\\d{2}\\s+\\d{2}:\\d{2})\\s*[·ㆍ]?\\s*종료\\s*(\\d{4}-\\d{2}-\\d{2}\\s+\\d{2}:\\d{2})")
    private val alternative = Regex("기간\\s*[·ㆍ]\\s*한국\\s*시간\\s*:\\s*(\\d{4}-\\d{2}-\\d{2}\\s+\\d{2}:\\d{2})\\s*~\\s*(\\d{4}-\\d{2}-\\d{2}\\s+\\d{2}:\\d{2})")
    private val kst = ZoneId.of("Asia/Seoul")
    private val fmt = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm")
    private val iso = DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssXXX")
    private fun normalize(s: String): String = Normalizer.normalize(s,Normalizer.Form.NFKC)
        .lowercase().filter { it.isLetterOrDigit() }
    private fun hash(s: String) = MessageDigest.getInstance("SHA-256").digest(s.toByteArray(StandardCharsets.UTF_8))
        .take(16).joinToString("") { "%02x".format(it.toInt() and 255) }

    private fun character(label: String, gameName: String): String? {
        var s = label.replace(Regex("^\\s*\\[(픽업|복각)]\\s*"),"").trim()
        if (s.startsWith(gameName)) s = s.removePrefix(gameName).trimStart(' ','-',':')
        if (listOf("무기 기원", "무기 픽업", "광추 이벤트", "광추 픽업", "음동기 픽업", "전용 무기", "전용 광추", "전용 음동기")
            .any { s.contains(it) }) return null
        val quotes = Regex("[「『]([^」』]+)[」』]").findAll(s).map { it.groupValues[1] }.toList()
        var result = if (quotes.isNotEmpty()) {
            val tail = s.substringAfterLast('」').substringAfterLast('』').trim(' ','-',':','·')
            if (tail.isNotBlank() && tail.length <= 35) tail else quotes.last().substringAfterLast('·')
        } else {
            if (" - " in s) s.substringAfterLast(" - ") else ""
        }
        result = result.replace(Regex("\\([^()]{1,14}\\)$"),"").trim(' ','-',':','·')
        return result.takeIf { it.isNotBlank() && it.length <= 40 && it != "픽업" && it != "복각" }
    }

    fun parse(html: String, game: GameRules.Game, base: String, nowMs: Long): List<BannerRecord> {
        if (!html.contains("KST") || !html.contains("한국")) return emptyList()
        val doc = Jsoup.parse(html,base)
        val found = linkedMapOf<String,BannerRecord>()
        for (li in doc.select("li")) {
            val text = li.text()
            if (!text.contains("한국 서버") && !text.contains("한국 시간")) continue
            val a = li.select("a[href]").firstOrNull {
                (it.text().startsWith("[픽업]") || it.text().startsWith("[복각]")) && it.text().contains(game.name)
            } ?: continue
            val range = primary.find(text) ?: alternative.find(text) ?: continue
            val start = runCatching { LocalDateTime.parse(range.groupValues[1],fmt).atZone(kst) }.getOrNull() ?: continue
            val end = runCatching { LocalDateTime.parse(range.groupValues[2],fmt).atZone(kst) }.getOrNull() ?: continue
            if (nowMs < start.toInstant().toEpochMilli() || nowMs >= end.toInstant().toEpochMilli()) continue
            val name = character(a.text(),game.name) ?: continue
            val startIso = start.format(iso)
            val key = hash("banner:v1:KR:${game.key}:${normalize(name)}:$startIso")
            // 버전이 실제 일정 카드에 표시된 경우에만 부가 표기. PC와 제목 규칙을 맞춘다.
            val version = Regex("(?:버전|Ver\\.?|v)\\s*(\\d+(?:\\.\\d+){1,2})", RegexOption.IGNORE_CASE)
                .find(text)?.groupValues?.getOrNull(1)
            val displayed = name + (version?.let { " ($it)" } ?: "")
            val title = "[${game.prefix}] $displayed"
            val source = a.absUrl("href")
            // 사용자 요구: 설명에는 출처만. 시작일은 Todoist 날짜, 종료 시각은 로컬 기록.
            if (!source.startsWith("https://")) continue
            val desc = "출처: $source"
            found[key] = BannerRecord(game.key, key, title, game.label,
                start.format(DateTimeFormatter.ISO_LOCAL_DATE), end.toInstant().toEpochMilli(), desc, source)
        }
        return found.values.toList()
    }

    /** 공개 페이지는 최소 15분 주기로만 가져온다. URL은 고정되어 요청 주입이 불가능하다. */
    fun fetch(game: GameRules.Game, nowMs: Long): List<BannerRecord> {
        if (game.key == "stella") {
            return StellaBanners.parse(org.json.JSONObject(HttpApi.request(StellaBanners.SOURCE)),nowMs)
        }
        if (game.key !in games) return emptyList()
        // 사용자가 명조 글로벌/CN 공통 가챠 일정을 허용했다. 개인 CN 계정 API와는 별개다.
        // 기존 한국어/KST·현재 캐릭터 픽업 파서와 PC 공통 키를 그대로 사용한다.
        val url = "https://www.pickupcal.com/games/${game.key}/"
        val conn = URL(url).openConnection() as HttpURLConnection
        try {
            conn.connectTimeout=10000; conn.readTimeout=12000
            conn.setRequestProperty("Accept","text/html")
            if (conn.responseCode != 200) return emptyList()
            val text = conn.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
            return parse(text,game,url,nowMs)
        } finally { conn.disconnect() }
    }
}

/** 새 가챠 등록과 기간 만료 완료. 두 기기가 같은 Todoist라면 결정적 UUID로 중복 방지. */
/**
 * 새 픽업 작업은 서버의 시작 날짜에 등록한다. 종료 시각은 SharedPreferences에 별도 보관한다.
 * 기존 자동 생성 작업(구버전 설명의 ID 표시)은 새 양식으로 안전하게 이전할 수 있다.
 */
class MobileBannerSync(private val context: android.content.Context) {
    private val prefs = context.getSharedPreferences("banner_fetch", android.content.Context.MODE_PRIVATE)
    private val ledger = BannerLedger(context)

    /** 가능하면 최신 일정 수집 후 종료 확인. 실패한 게임의 과거 종료시각은 로컬에 보존된다. */
    fun run(api: TodoistApi, nowMs: Long = System.currentTimeMillis(), force: Boolean = false): Int {
        val tasks = api.tasks()
        val section = api.bannerSection()
        val shouldFetch = force || nowMs - prefs.getLong("last_fetch",0L) >= 15 * 60 * 1000L
        var created = 0
        if (shouldFetch && section != null) {
            // 수집을 시작하기 전에 기록: API 장애 시 무한 재시도로 배터리를 소모하지 않음.
            prefs.edit().putLong("last_fetch",nowMs).apply()
            val existing = tasks.filter { it.sectionId == section.second }
            for (game in GameRules.all(context)) {
                val banners = try { BannerSource.fetch(game, nowMs) } catch (_: Exception) { emptyList() }
                for (banner in banners) {
                    val item = existing.firstOrNull { BannerLedger.legacyKey(it.description) == banner.key }
                        ?: existing.firstOrNull { it.title == banner.title &&
                            it.dueDate?.take(10) == banner.startDate &&
                            BannerLedger.source(it.description) == banner.sourceUrl }
                    if (item != null) {
                        // 이전 자동 등록 작업만 설명과 날짜를 수정한다. 수동 작업은 건드리지 않는다.
                        if (BannerLedger.legacyKey(item.description) == banner.key &&
                            (item.description != banner.description || item.dueDate != banner.startDate ||
                             item.title != banner.title)) {
                            api.updateBanner(item.id,banner)
                        }
                        ledger.remember(banner,item.id)
                        continue
                    }
                    // 이름만 같은 수동 작업이 있으면 중복 추가하지 않되, 임의 완료하지 않는다.
                    if (existing.any { it.title.equals(banner.title,ignoreCase=true) }) continue
                    val newId = api.createBanner(section.first,section.second,banner)
                    // Sync API가 ID 매핑을 주면 추가적인 HTTP 요청 없이 로컬 기록에 연결.
                    // 매핑이 없으면 다음 실행에서 제목+시작일+출처로 다시 연결한다.
                    if (newId != null) ledger.remember(banner,newId)
                    created++
                }
            }
        }
        // 별도 Todoist 데드라인이 아니라 로컬 종료시각을 기반으로 완료한다.
        // 재조회가 완료된 경우 최신 서버 데이터를 우선해 연장된 가챠의 조기 완료를 방지한다.
        ledger.closeExpired(api, tasks, nowMs)
        // v0.8.0 이전에 생성되어 설명에 내부 ID/종료시각이 남아 있는 작업도
        // 이전 형식 그대로 만료를 처리한다. 새 작업에는 이런 메타데이터를 적지 않는다.
        for (old in tasks) {
            if (BannerExpiry.expired(old, nowMs)) {
                BannerExpiry.occurrence(old)?.let { api.completeForCycle(old.id,it) }
            }
        }
        return created
    }
}
