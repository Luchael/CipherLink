package com.gametodo.nativeapp

import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter

/**
 * HoYoLAB 전적 읽기 전용 조회. 실시간 메모와 별개의 API이며 실계정 응답은
 * Android 빌드/로그인 기기에서 다시 확인해야 한다.
 *
 * 안전 규칙: 유효한 현재 시즌 + 분명한 점수 단위가 모두 있을 때만 자동완료 후보를 생성한다.
 * API 실패/없는 기록/별 수가 아닌 포인트는 절대로 0점 또는 완료로 단정하지 않는다.
 */
object EndgameRecords {
    private const val BBS = "https://bbs-api-os.hoyolab.com"
    private const val SG = "https://sg-public-api.hoyolab.com"
    private const val SG_ACT = "https://sg-act-public-api.hoyolab.com"

    private data class Source(val mode: String, val path: String, val extra: String = "", val experimental: Boolean = false)

    /** 최신 genshin.py v1.7.31의 글로벌 읽기 전용 경로와 동일한 게임별 API. */
    private fun sources(game: String): List<Source> = when (game) {
        "genshin" -> listOf(
            Source("spiral", "$SG/event/game_record/genshin/api/spiralAbyss", "schedule_type=1"),
            // role_combat는 schedule_type 요청과 무관하게 이전 회차도 돌려줄 수 있다.
            Source("theater", "$SG/event/game_record/genshin/api/role_combat", "need_detail=true")
        )
        "hsr" -> listOf(
            Source("moc", "$BBS/game_record/hkrpg/api/challenge", "schedule_type=1&need_all=true"),
            Source("pure_fiction", "$BBS/game_record/hkrpg/api/challenge_story", "schedule_type=1&need_all=true"),
            Source("apocalyptic", "$BBS/game_record/hkrpg/api/challenge_boss", "schedule_type=1&need_all=true"),
            Source("arbitration", "$BBS/game_record/hkrpg/api/challenge_peak", "schedule_type=3")
        )
        "zzz" -> listOf(
            Source("shiyu", "$SG_ACT/event/game_record_zzz/api/zzz/hadal_info_v2", "schedule_type=1"),
            // 2026 genshin.py ZZZ 데들리 기록은 uid/region 이며 role_id/server 가 아님.
            Source("deadly", "$SG_ACT/event/game_record_zzz/api/zzz/hadal_mem_detail_v2", "schedule_type=1")
        )
        else -> emptyList()
    }

    /** 정확한 키 계약. 정규화하지 않은 서버값은 호출 전 캐릭터 목록에서 검증한다. */
    fun queryFor(role: GameRole, mode: String, extra: String = "schedule_type=1"): String {
        val idName = if (role.game == "zzz" && mode == "deadly") "uid" else "role_id"
        val serverName = if (role.game == "zzz" && mode == "deadly") "region" else "server"
        return "$idName=${GameNet.encode(role.uid)}&$serverName=${GameNet.encode(role.server)}&$extra"
    }

    private fun experiments(game: String): List<Source> = when (game) {
        "genshin" -> listOf(Source("stygian_test", "$SG/event/game_record/genshin/api/hard_challenge", "schedule_type=1", true))
        "hsr" -> listOf(Source("arbitration_test", "$BBS/game_record/hkrpg/api/challenge", "type=arbitration&schedule_type=1&need_all=true", true))
        "zzz" -> listOf(Source("shiyu_detail_test", "$SG/event/game_record_zzz/api/zzz/mem_detail", "schedule_type=1", true))
        else -> emptyList()
    }

    /** 수동 진단 전용. 시즌 이전 조회는 API 지원 여부를 관찰하기 위한 시험 요청이다.
     * 모든 요청은 GET이며, 결과로 게임 상태나 Todoist를 변경하지 않는다. */
    data class DiagnosticRequest(val mode: String, val period: String, val url: String)

    fun diagnosticRequests(role: GameRole, includePrevious: Boolean = true): List<DiagnosticRequest> {
        val result = mutableListOf<DiagnosticRequest>()
        for (s in sources(role.game)) {
            result.add(DiagnosticRequest(s.mode, "default", "${s.path}?${queryFor(role, s.mode, s.extra)}"))
            // API별 previous=true가 확실하지 않다. schedule_type=2는 별도 *실험*으로만 조회.
            if (includePrevious && s.extra.contains("schedule_type=1")) {
                val extra = s.extra.replace("schedule_type=1", "schedule_type=2")
                result.add(DiagnosticRequest(s.mode, "previous_probe_unverified",
                    "${s.path}?${queryFor(role, s.mode, extra)}"))
            }
        }
        return result
    }

    data class Probe(val gauges: List<AccountGauge>, val diagnostics: List<String>)

    fun probe(cookie: String, role: GameRole, includeExperimental: Boolean = false): Probe {
        val gauges = linkedMapOf<String, AccountGauge>()
        val problems = linkedMapOf<String, MutableList<String>>()
        val candidates = sources(role.game) + if (includeExperimental) experiments(role.game) else emptyList()
        for (s in candidates) {
            if (!s.experimental && s.mode in gauges) continue
            try {
                val query = queryFor(role, s.mode, s.extra)
                val body = HoyoProvider.data(GameNet.json("${s.path}?$query", headers = HoyoProvider.recordHeaders(cookie)))
                if (s.experimental) {
                    problems.getOrPut(s.mode) { mutableListOf() }.add("실험 조회 성공(완료 판정에 사용 안 함), ${shape(body)}")
                    continue
                }
                if (s.mode == "deadly") problems.getOrPut("deadly_summary") { mutableListOf() }
                    .add(deadlyDiagnostic(body))
                val got = parse(role, s.mode, body)
                if (got == null) {
                    problems.getOrPut(s.mode) { mutableListOf() }.add("응답 성공·점수/회차 확인 불가(${shape(body)})")
                } else {
                    gauges[s.mode] = got
                    if (got.periodKey == null) problems.getOrPut(s.mode) { mutableListOf() }
                        .add("점수 ${got.current}/${got.maximum}, 시즌 시작/종료 미확인 → 자동 완료 보류")
                }
            } catch (e: Exception) {
                val error = when {
                    e.message?.contains("HTTP 404") == true -> "API 경로 404"
                    e.message?.contains("HTTP 401") == true -> "인증 만료/거부 401"
                    e.message?.contains("retcode") == true ->
                        "게임 기록 retcode=${Regex("retcode=(-?\\d+)").find(e.message ?: "")?.groupValues?.get(1) ?: "불명"} (DS·헤더·인증 쿠키·공개 설정을 구분 확인)"
                    else -> e.javaClass.simpleName
                }
                problems.getOrPut(s.mode) { mutableListOf() }.add(error)
            }
        }
        val diagnostics = problems.mapNotNull { (mode, messages) ->
            // 충분한 게이지가 있으면 이전 fallback 경로의 404는 보여주지 않는다.
            if (mode in gauges && gauges[mode]?.periodKey != null) null
            else "$mode: ${messages.distinct().joinToString(" / ").take(220)}"
        }.toMutableList()
        if (role.game == "hsr" && "arbitration" !in gauges)
            diagnostics.add("arbitration: challenge_peak 데이터/기간 검증 전 자동 완료 보류")
        return Probe(gauges.values.toList(), diagnostics)
    }

    fun fetch(cookie: String, role: GameRole): List<AccountGauge> = probe(cookie, role).gauges

    /** 필드명+배열 길이만 보여주는 안전한 응답 구조 진단. 개인정보·실제 필드값은 노출하지 않는다. */
    private fun shape(root: JSONObject): String {
        fun names(o: JSONObject): String {
            val all = mutableListOf<String>()
            val keys = o.keys()
            while (keys.hasNext() && all.size < 14) {
                val k = keys.next()
                if (listOf("token", "cookie", "name", "icon", "uid", "avatar").none { k.contains(it, true) }) {
                    val a = o.optJSONArray(k)
                    all.add(if (a != null) "$k[${a.length()}]" else k)
                }
            }
            return all.joinToString(",")
        }
        val inner = root.optJSONObject("hadal_info_v2") ?: root.optJSONObject("hadal_info_v1")
            ?: root.optJSONObject("data") ?: root.optJSONObject("detail")
        val seq = root.optJSONArray("data") ?: root.optJSONArray("list") ?: root.optJSONArray("records")
        val first = if (seq != null && seq.length() > 0) seq.optJSONObject(0) else null
        val nested = inner?.optJSONObject("brief_info") ?: inner?.optJSONObject("stat")
            ?: first?.optJSONObject("stat") ?: first?.optJSONObject("stats")
        return "필드 ${names(root)}" +
            (if (inner != null) " / 내부 ${names(inner)}" else "") +
            (if (first != null) " / 기록 ${names(first)}" else "") +
            (if (nested != null) " / 기록상세 ${names(nested)}" else "")
    }

    fun parse(role: GameRole, mode: String, payload: JSONObject): AccountGauge? {
        val root = currentRecord(payload, mode)
        // challenge_peak_records는 3개 회차가 한 번에 반환될 수 있다.
        // 현재 날짜에 해당하는 단일 회차만 채택한다. 일치하지 않으면 최신 과거 기록은
        // 표시용으로 읽되 currentPeriod에서 자동 완료되지 않게 한다.
        val record = if (mode == "arbitration") pickPeakSeason(root) ?: return null else root
        // 강습전: API가 정상 응답하고 회차 시작/종료를 주면서 has_data=false이면
        // '조회 실패'가 아닌 '해당 회차 미도전(0/9)'이다. 다른 모드는 보수적으로 보류.
        if (record.opt("has_data") == false && mode != "deadly") return null
        val (current, max) = when (mode) {
            "spiral" -> abyssStars(record)
            "theater" -> theaterStellas(record)
            "moc", "pure_fiction", "apocalyptic" -> explicitStars(record)
            "arbitration" -> arbitrationStars(record)
            "shiyu" -> shiyuStars(record)
            "deadly" -> deadlyStars(record)
            else -> return null
        }
        val goal = when (mode) {
            "shiyu" -> max // 최신 시유 보상 단위가 명시적으로 확인된 경우만 사용.
            else -> listOfNotNull(EndgameGoals.target(mode), max).maxOrNull()
        }
        if (current == null || goal == null || goal <= 0 || current < 0 || current > 500) return null
        val period = periodRange(record).let { (start, end) ->
            if (start != null && end != null && end > start) start to end else periodRange(payload).let { fallback ->
                if (fallback.first != null && fallback.second != null) fallback
                else periodFromGroups(record)
            }
        }
        val start = period.first
        val end = period.second
        val key = if (start != null && end != null && end > start) "$mode:$start:$end" else null
        return AccountGauge(role.game, role.uid, mode, current, goal,
            periodKey = key, periodStartMs = start, periodEndMs = end, displayDetail = scoreDetail(mode,payload))
    }

    /** 환상극 data 배열에서 schedule_type=1 회차, 아니면 명확하게 가장 최신 회차를 채택. */
    private fun currentRecord(payload: JSONObject, mode: String): JSONObject {
        var root = payload
        repeat(3) {
            val wrapped = root.optJSONObject("data") ?: root.optJSONObject("detail")
                ?: root.optJSONObject("record")
            if (wrapped != null) root = wrapped
        }
        // 위험한 강습전은 최상위 total_star/total_score와 list(보스 전적)를 함께 가진다.
        // list[0]으로 들어가면 총 별점·시즌 정보가 유실된다.
        if (mode == "deadly" && readNumber(root, "total_star", "total_stars") != null)
            return root
        val arrays = if (mode == "theater")
            listOf("data", "datas", "list", "records", "schedules", "schedule_list")
            else listOf("list", "records", "schedules", "schedule_list", "challenge_data", "all", "data")
        for (field in arrays) {
            val a = root.optJSONArray(field) ?: continue
            val records = (0 until a.length()).mapNotNull { a.optJSONObject(it) }
            if (records.isEmpty()) return JSONObject()
            val current = records.filter { readNumber(it, "schedule.schedule_type", "schedule_type") == 1 }
            if (current.size == 1) return current.first()
            if (records.size == 1) return records.first()
            val sorted = records.mapNotNull { obj -> periodRange(obj).first?.let { it to obj } }
                .sortedByDescending { it.first }
            if (sorted.size == records.size && sorted[0].first > sorted[1].first)
                return sorted[0].second
            return JSONObject() // 둘 이상의 회차를 구분하지 못하면 판정 보류
        }
        return root
    }

    private fun explicitStars(o: JSONObject): Pair<Int?, Int?> =
        readNumber(o, "total_star", "total_stars", "star_num", "total_star_num", "stat.total_star", "basic.total_star") to
        readNumber(o, "max_star_num", "max_stars", "max_star", "max_star_count", "total_max_stars")

    /** medal_num은 스텔라와 다르다. stats.star_challenge_stellas는 공연별 bool 배열. */
    private fun theaterStellas(o: JSONObject): Pair<Int?, Int?> {
        val array = o.optJSONObject("stat")?.optJSONArray("star_challenge_stellas")
            ?: o.optJSONObject("stats")?.optJSONArray("star_challenge_stellas")
            ?: o.optJSONArray("star_challenge_stellas")
            ?: o.optJSONObject("stat")?.optJSONArray("get_medal_round_list")
            ?: o.optJSONArray("get_medal_round_list")
        if (array != null && array.length() > 0) {
            val vals = (0 until array.length()).map { array.opt(it) }
            if (vals.all { it is Boolean })
                return vals.count { it == true } to EndgameGoals.THEATER_STELLA
            // 일부 버전의 원본 JSON은 참/거짓 대신 정수 0, 1로 부호화될 수 있다.
            // 2 이상인 단계 번호 배열을 스텔라로 잘못 계산하면 안 된다.
            if (vals.all { it is Number && it.toInt() in 0..1 })
                return vals.count { (it as Number).toInt() == 1 } to EndgameGoals.THEATER_STELLA
        }
        return readNumber(o, "stella_num", "stella_count", "total_stella", "stella_cnt",
            "stat.stella_num", "stat.stella_count", "stats.stella_num", "stat.total_stella",
            "summary.stella_count") to EndgameGoals.THEATER_STELLA
    }

    private fun abyssStars(o: JSONObject): Pair<Int?, Int?> {
        val known = explicitStars(o)
        if (known.first != null) return known
        val a = o.optJSONArray("floors") ?: return known
        val floors = mutableMapOf<Int, Int>()
        for (i in 0 until a.length()) {
            val obj = a.optJSONObject(i) ?: continue
            val id = readNumber(obj, "index", "floor") ?: continue
            val stars = readNumber(obj, "star", "stars") ?: continue
            floors[id] = stars
        }
        return if (floors.keys.containsAll(listOf(9,10,11,12)))
            listOf(9,10,11,12).sumOf { floors[it] ?: 0 } to 36 else known
    }

    /** 위험한 강습전: '합계 점수'를 9성으로 간주하면 안 된다. */
    private fun deadlyStars(o: JSONObject): Pair<Int?, Int?> {
        val total = readNumber(o,"total_star","total_stars")
        if (o.opt("has_data") == false) {
            val emptyNormal = o.optJSONArray("list")?.length() == 0
            val emptyHard = o.optJSONArray("hard_list")?.length() == 0
            // 회차 기간 없으면 상위 parse에서 자동 완료를 보류한다.
            return if (total == 0 && emptyNormal && emptyHard) 0 to 9 else null to 9
        }
        // 절망 hard_list는 추가 보상이며 9별 판정에서 제외한다.
        val rows = o.optJSONArray("list") ?: o.optJSONArray("challenges")
            ?: o.optJSONArray("challenge_list")
        if (total != null && total in 0..9) return total to 9
        if (rows == null) return null to 9
        if (rows.length() != 3) return null to 9
        val records = (0 until rows.length()).mapNotNull { rows.optJSONObject(it) }
        if (records.size != 3) return null to 9
        val direct = records.map { readNumber(it,"total_star","star") }
        if (direct.all { it != null && it in 0..3 }) return direct.sumOf { it ?: 0 } to 9
        val scores = records.map { readNumber(it,"score") }
        if (scores.any { it == null || it < 0 }) return null to 9
        val result: Int = scores.map { p -> when {
            p!! >= 20000 -> 3
            p >= 14000 -> 2
            p >= 6000 -> 1
            else -> 0
        } }.sum()
        return result to 9
    }

    /** Supplementary raw points only. Completion still uses verified grades/stars. */
    fun scoreDetail(mode: String, payload: JSONObject): String {
        val root=currentRecord(payload,mode)
        val record=root.optJSONObject("hadal_info_v2") ?: root.optJSONObject("hadal_info_v1") ?: root
        fun points(rows: JSONArray?, suffix: String): String {
            if(rows==null) return ""
            return (0 until rows.length()).mapNotNull {i->
                val value=rows.optJSONObject(i)?.let {readNumber(it,"score")}
                if(value==null || value<0) null else "${i+1}$suffix ${String.format(java.util.Locale.KOREA,"%,d",value)}점"
            }.joinToString(" · ")
        }
        return when(mode) {
            "shiyu" -> points((record.optJSONObject("fitfh_layer_detail") ?: record.optJSONObject("fifth_layer_detail"))
                ?.optJSONArray("layer_challenge_info_list"),"번 방")
            "deadly" -> listOf("일반" to "list","절망" to "hard_list").mapNotNull { (name,key)->
                points(record.optJSONArray(key),"번").takeIf {it.isNotBlank()}?.let {"$name $it"}
            }.joinToString(" · ")
            else -> ""
        }
    }

    /** normal list / hard_list를 분리해서 보여준다. 절망 기록은 보상 완료 조건에 넣지 않는다. */
    fun deadlyDiagnostic(payload: JSONObject): String {
        val record = currentRecord(payload, "deadly")
        val (begin, end) = periodRange(record)
        if (begin == null || end == null || begin >= end) return "deadly: 회차 기간 확인 불가 · 자동 완료 보류"
        val hasData = record.opt("has_data")
        val normal = record.optJSONArray("list")
        val hard = record.optJSONArray("hard_list")
        if (hasData == false && normal?.length() == 0 && hard?.length() == 0) {
            return "deadly: 현재 회차 미도전 · 일반 0/9별 (0점) · 절망 기록 없음"
        }
        fun detail(list: JSONArray?): String {
            if (list == null || list.length() == 0) return "기록 없음"
            val scores = (0 until list.length()).map { i ->
                val obj = list.optJSONObject(i)
                val points = obj?.let { readNumber(it, "score") }
                val stars = obj?.let { readNumber(it, "total_star", "star") }
                if (points == null && stars == null) "?" else "${points ?: "?"}점/${stars ?: "?"}별"
            }
            return scores.joinToString(" · ")
        }
        val stars = readNumber(record, "total_star")
        val normalText = if (stars != null) "일반 ${stars}/9별 · ${detail(normal)}" else "일반 ${detail(normal)}"
        return "deadly: $normalText / 절망 ${detail(hard)} (추가 보상, 완료 판정 제외)"
    }

    /** 시유 신/구버전별 데이터의 점수 단위가 다른 경우 무리해서 환산하지 않는다. */
    private fun shiyuStars(payload: JSONObject): Pair<Int?, Int?> {
        val version = readString(payload,"hadal_ver")
        val o = when(version) {
            "v1" -> payload.optJSONObject("hadal_info_v1") ?: payload
            "v2" -> payload.optJSONObject("hadal_info_v2") ?: payload
            else -> payload
        }
        // v2: 명료한 S등급 항목 4개(제4전선 1 + 제5전선의 방 3개)를 센다.
        // 각 방의 rating이 있으면 그 등급을 우선 사용하고, 없으면 게임의 S 점수 기준
        // 25,000점을 사용한다. **합계 90,000점은 S 3개를 보증하지 않는다.**
        if (version == "v2") {
            val fourth = o.optJSONObject("fourth_layer_detail")
            val fifth = o.optJSONObject("fitfh_layer_detail")
                ?: o.optJSONObject("fifth_layer_detail")
            val rooms = fifth?.optJSONArray("layer_challenge_info_list")
            val rank = fourth?.optString("rating")?.uppercase()?.trim()
            if (rooms != null && rooms.length() == 3 && !rank.isNullOrBlank()) {
                val sGrades = setOf("S", "S+", "SS")
                val knownGrades = sGrades + setOf("A", "B", "C", "D", "F")
                if (rank in knownGrades) {
                    val roomS = (0 until 3).map { i ->
                        val room = rooms.optJSONObject(i)
                        if (room == null) null else {
                            val rating = room.optString("rating").uppercase().trim()
                            when {
                                rating in knownGrades -> rating in sGrades
                                readNumber(room, "score")?.let { it >= 0 } == true ->
                                    readNumber(room, "score")!! >= 25_000
                                else -> null
                            }
                        }
                    }
                    if (roomS.all { it != null }) {
                        val fourthS = if (rank in sGrades) 1 else 0
                        val fifthSCount = roomS.count { it == true }
                        // 전선 통과 여부까지 API가 거짓이라고 응답한다면 완료로 간주하지 않는다.
                        val verifiedFifth = if (o.opt("pass_fifth_floor") == true)
                            fifthSCount else minOf(fifthSCount, 2)
                        return (fourthS + verifiedFifth) to 4
                    }
                }
            }
        }
        val explicit = readNumber(o,"brief_info.total_star","total_star","total_stars")
        val maximum = readNumber(o,"brief_info.max_star","max_star_num","max_star")
        if (explicit != null && maximum != null) return explicit to maximum
        val floors = o.optJSONArray("floors")
        if (floors != null && floors.length() == 7) {
            val grades = (0 until floors.length()).map { floors.optJSONObject(it)?.optString("rating") }
            if (grades.all { it in listOf("S","A","B") }) return grades.count { it == "S" } to 7
        }
        return null to null
    }

    private fun arbitrationStars(o: JSONObject): Pair<Int?, Int?> {
        // 실제 challenge_peak_records[] 안에서 기사(mob_stars) 9 + 왕(boss_stars) 3.
        // 기록이 3개여도 서로 다른 시즌을 합산하면 안 된다.
        val mob = readNumber(o, "mob_stars", "summary.mini_boss_stars")
        val boss = readNumber(o, "boss_stars", "summary.boss_stars")
        if (mob != null && boss != null && mob in 0..9 && boss in 0..3)
            return mob + boss to 12
        return explicitStars(o)
    }

    private fun pickPeakSeason(o: JSONObject): JSONObject? {
        val all = o.optJSONArray("challenge_peak_records") ?: return o
        val rows = (0 until all.length()).mapNotNull { all.optJSONObject(it) }
        if (rows.isEmpty()) return null
        val dated = rows.mapNotNull { r ->
            val group = r.optJSONObject("group") ?: r
            val (s, e) = periodRange(group)
            if (s != null && e != null && e > s) Triple(s, e, r) else null
        }
        if (dated.size != rows.size) return null
        val now = System.currentTimeMillis()
        val active = dated.filter { now >= it.first && now < it.second }
        if (active.size == 1) return active.first().third
        if (active.size > 1) return null
        return dated.maxByOrNull { it.first }?.third // 과거 데이터: 자동 완료는 기간 검사로 차단
    }

    private fun periodFromGroups(o: JSONObject): Pair<Long?, Long?> {
        val seq = o.optJSONArray("groups") ?: return null to null
        val windows = (0 until seq.length()).mapNotNull { i ->
            seq.optJSONObject(i)?.let { periodRange(it) }
                ?.takeIf { it.first != null && it.second != null && it.second!! > it.first!! }
        }
        val now = System.currentTimeMillis()
        val active = windows.filter { now >= it.first!! && now < it.second!! }
        return if (active.size == 1) active[0] else null to null
    }

    fun currentPeriod(g: AccountGauge, nowMs: Long, resetMinutes: Int? = GamePeriods.defaultResetMinutes(g.game)): Boolean =
        g.periodKey != null && g.periodStartMs != null && g.periodEndMs != null &&
        nowMs >= g.periodStartMs + 20 * 60_000L && nowMs < g.periodEndMs &&
        GamePeriods.currentCycle(g.game,"daily",nowMs,resetMinutes=resetMinutes)!=null

    /** UTC epoch/ISO/Asia UTC+8 time and nested schedule date_time support. */
    private fun periodRange(o: JSONObject): Pair<Long?, Long?> {
        fun parse(vararg paths: String): Long? {
            for (path in paths) {
                var value: Any? = o
                for (component in path.split('.')) value = (value as? JSONObject)?.opt(component)
                if (value is JSONObject) {
                    try {
                        val year = readNumber(value, "year") ?: continue
                        val month = readNumber(value, "month") ?: continue
                        val day = readNumber(value, "day") ?: continue
                        val hour = readNumber(value, "hour") ?: 0
                        val min = readNumber(value, "minute") ?: 0
                        val second = readNumber(value, "second") ?: 0
                        return LocalDateTime.of(year,month,day,hour,min,second)
                            .toInstant(ZoneOffset.ofHours(8)).toEpochMilli()
                    } catch (_: Exception) { continue }
                }
                val str = value?.toString() ?: continue
                str.toLongOrNull()?.let { n ->
                    val millis = if (n in 1_000_000_000L..99_999_999_999L) n * 1000 else n
                    if (millis in 1_500_000_000_000L..5_000_000_000_000L) return millis
                }
                try { return Instant.parse(str).toEpochMilli() } catch (_: Exception) {}
                try { return OffsetDateTime.parse(str).toInstant().toEpochMilli() } catch (_: Exception) {}
                for (fmt in listOf("yyyy-MM-dd HH:mm:ss","yyyy-MM-dd HH:mm","yyyy-MM-dd")) {
                    try {
                        val date = if (fmt == "yyyy-MM-dd")
                            java.time.LocalDate.parse(str,DateTimeFormatter.ofPattern(fmt)).atStartOfDay()
                            else LocalDateTime.parse(str,DateTimeFormatter.ofPattern(fmt))
                        return date.toInstant(ZoneOffset.ofHours(8)).toEpochMilli()
                    } catch (_: Exception) {}
                }
            }
            return null
        }
        return parse("start_time","begin_time","schedule_start_time","start_date_time","hadal_begin_time",
            "schedule.start_time","schedule.begin_time","schedule.start_datetime","season.begin_time",
            "hadal_info_v2.begin_time","hadal_info_v1.begin_time",
            "hadal_info_v2.hadal_begin_time","hadal_info_v1.hadal_begin_time", "group.begin_time") to
            parse("end_time","finish_time","schedule_end_time","end_date_time","hadal_end_time",
            "schedule.end_time","schedule.finish_time","schedule.end_datetime","season.end_time",
            "hadal_info_v2.end_time","hadal_info_v1.end_time",
            "hadal_info_v2.hadal_end_time","hadal_info_v1.hadal_end_time", "group.end_time")
    }
}
