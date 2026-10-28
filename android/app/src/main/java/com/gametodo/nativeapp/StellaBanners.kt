package com.gametodo.nativeapp

import org.json.JSONObject
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.text.Normalizer
import java.security.MessageDigest

/** Public, unofficial KR feed; the feed's current label is never sufficient. */
object StellaBanners {
    const val SOURCE = "https://api.ennead.cc/stella/banners?lang=KR"
    fun parse(payload: JSONObject, nowMs: Long): List<BannerRecord> {
        val rows = payload.optJSONArray("current") ?: error("스텔라 KR 배너 응답 구조 변경")
        val found = linkedMapOf<String, BannerRecord>()
        for (i in 0 until rows.length()) {
            val row = rows.optJSONObject(i) ?: continue
            if (row.optString("bannerType") != "여행가 기간 한정 모집") continue
            val start = runCatching { OffsetDateTime.parse(row.getString("startTime"))
                .atZoneSameInstant(ZoneId.of("Asia/Seoul")) }.getOrNull() ?: continue
            val end = runCatching { OffsetDateTime.parse(row.getString("endTime"))
                .atZoneSameInstant(ZoneId.of("Asia/Seoul")) }.getOrNull() ?: continue
            if (nowMs < start.toInstant().toEpochMilli() || nowMs >= end.toInstant().toEpochMilli()) continue
            val entries = row.optJSONObject("rateUp")?.optJSONObject("fiveStar")?.optJSONArray("entries") ?: continue
            for (j in 0 until entries.length()) {
                val name = entries.optJSONObject(j)?.optString("name")?.trim() ?: continue
                if (name.length !in 1..40 || !Regex("[가-힣]").containsMatchIn(name) ||
                    name.any { it.code < 32 || it in "/:[]" }) continue
                val normalized = Normalizer.normalize(name,Normalizer.Form.NFKC).lowercase()
                    .filter { it.isLetterOrDigit() }
                val iso = start.format(DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssXXX"))
                val key = MessageDigest.getInstance("SHA-256")
                    .digest("banner:v1:KR:stella:$normalized:$iso".toByteArray(Charsets.UTF_8))
                    .take(16).joinToString("") { "%02x".format(it.toInt() and 255) }
                found[key] = BannerRecord("stella",key,"[스소] $name","스텔라소라",
                    start.toLocalDate().toString(),end.toInstant().toEpochMilli(),"출처: $SOURCE",SOURCE)
            }
        }
        return found.values.toList()
    }
}
