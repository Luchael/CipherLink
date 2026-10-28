package com.gametodo.nativeapp

import org.json.JSONObject
import org.json.JSONArray
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.security.MessageDigest
import java.security.SecureRandom
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec
import java.time.Instant

/**
 * 게임 계정 읽기 전용 연동.
 * 화면 캡처 없이 게임사의 계정 사이트에서 공개/인증된 상태를 읽는다.
 * 데이터 구조가 바뀌면 완료로 추측하지 말고 null을 반환할 것.
 * 이 모듈은 출석 보상 수령/게임 상태 변경 API를 절대 호출하지 않는다.
 */
data class AccountGauge(
    val game: String, val account: String, val metric: String,
    val current: Int, val maximum: Int, val observedAtMs: Long = System.currentTimeMillis(),
    // 엔드 콘텐츠는 일자 초기화가 아닌 게임 서버가 제공한 시즌/회차 기준으로 판단한다.
    val periodKey: String? = null,
    val periodStartMs: Long? = null,
    val periodEndMs: Long? = null
) {
    val filled: Boolean get() = maximum > 0 && current >= maximum && current >= 0
}

data class GameRole(val game: String, val uid: String, val server: String, val nickname: String)

object GameNet {
    fun json(url: String, method: String = "GET", payload: JSONObject? = null,
             headers: Map<String,String> = emptyMap()): JSONObject {
        require(url.startsWith("https://"))
        val conn = URL(url).openConnection() as HttpURLConnection
        try {
            conn.connectTimeout = 12000
            conn.readTimeout = 15000
            conn.requestMethod = method
            conn.setRequestProperty("Accept", "application/json")
            headers.forEach { (k, v) -> conn.setRequestProperty(k, v) }
            if (payload != null) {
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                conn.outputStream.use { it.write(payload.toString().toByteArray(Charsets.UTF_8)) }
            }
            if (conn.responseCode !in 200..299) {
                // 원문 오류에는 쿠키나 계정 정보가 포함될 수 있으므로 상태 코드만 기록.
                throw IllegalStateException("${URL(url).host}: HTTP ${conn.responseCode}")
            }
            val answer = JSONObject(conn.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() })
            // HTTP 200이어도 게임사 JSON code 필드에 실패 코드가 포함될 수 있다.
            val code = answer.opt("code")
            if (URL(url).host.endsWith("skport.com") && code is Number && code.toInt() != 0) {
                throw IllegalStateException("${URL(url).host}: SKPORT code=${code.toInt()}")
            }
            return answer
        } finally { conn.disconnect() }
    }
    fun encode(s: String): String = URLEncoder.encode(s, "UTF-8")
}

object HoyoProvider {
    // 글로벌 HoYoLAB용 API. 중국 본토 API를 사용하지 않는다.
    // genshin.py가 사용하는 글로벌 게임 계정 API를 우선 시도한다.
    // 기존 CookieToken 전용 경로만 사용하면 ltoken_v2 계정에서 실패할 수 있다.
    private val ROLE_ENDPOINTS = listOf(
        "https://api-os-takumi.mihoyo.com/binding/api/getUserGameRolesByCookie",
        "https://api-os-takumi.hoyoverse.com/binding/api/getUserGameRolesByCookie",
        "https://api-account-os.hoyolab.com/account/binding/api/getUserGameRolesByCookieToken"
    )
    private val biz = mapOf("genshin" to "hk4e_global", "hsr" to "hkrpg_global", "zzz" to "nap_global")

    // 각 게임의 글로벌 실시간 메모는 같은 URL 접두사를 사용하지 않는다.
    // 원신: 기존 정상 동작 경로를 보존한다.
    // 스타레일: 공식 글로벌 게임 기록 API 경로 및 호스트 대체 경로.
    // 젠존제: sg-public-api의 event/game_record_zzz API이며 /game_record/zzz/api/index가 아니다.
    // 출처: michos-api / node-hoyolab / 2024 KWGT HoYoLAB 실시간 메모 사례.
    private val noteEndpoints = mapOf(
        "genshin" to listOf("https://bbs-api-os.hoyolab.com/game_record/genshin/api/dailyNote"),
        "hsr" to listOf(
            "https://bbs-api-os.hoyolab.com/game_record/hkrpg/api/note",
            "https://bbs-api-os.hoyoverse.com/game_record/hkrpg/api/note"
        ),
        "zzz" to listOf("https://sg-public-api.hoyolab.com/event/game_record_zzz/api/zzz/note")
    )

    internal fun headers(cookie: String) = mapOf(
        "Cookie" to cookie,
        "Referer" to "https://www.hoyolab.com/",
        "Origin" to "https://www.hoyolab.com",
        "x-rpc-language" to "ko-kr",
        // HoYoLAB 앱/웹에 사용되는 글로벌 클라이언트 구분 헤더.
        "x-rpc-client_type" to "5",
        "x-rpc-app_version" to "1.5.0",
        "User-Agent" to "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    )
    /** 전적 API는 일일 노트와 달리 호출 지점에서 DS가 누락되지 않게 강제한다.
     * genshin.py get_ds_headers(OVERSEAS)와 동일한 구성. */
    internal fun recordHeaders(cookie: String): Map<String, String> = headers(cookie) + mapOf(
        "DS" to dsOs(),
        "x-rpc-lang" to "ko-kr"
    )

    internal fun data(j: JSONObject): JSONObject {
        if (j.optInt("retcode", -999) != 0) {
            val code = j.optInt("retcode")
            val hint = if (code == -10001) "전적 요청의 DS 서명·헤더·인증 쿠키·전적 공개 설정을 점검해 주세요" else "게임사 응답 코드를 확인해 주세요"
            throw IllegalStateException("HoYoLAB retcode=$code ($hint)")
        }
        return j.optJSONObject("data") ?: throw IllegalStateException("HoYoLAB data 없음")
    }

    /**
     * 글로벌 HoYoLAB에 연결된 전체 캐릭터를 받아온다.
     * 같은 게임에 여러 서버 계정이 있어도 임의로 버리지 않는다.
     * 게임 계정 목록 API는 변경될 수 있으므로 실패 원인을 보존한다.
     */
    fun roles(cookie: String): List<GameRole> {
        // getUserGameRolesByCookie는 통합 조회보다 game_biz를 명시하는 조회가
        // 더 안정적일 수 있다. 세 게임을 각각 시도하되, 성공한 목록을 병합한다.
        // HTTP 성공만으로 로그인 성공이라 판단하지 않고 retcode와 data를 확인한다.
        val found = linkedMapOf<String, GameRole>()
        val failures = mutableListOf<String>()
        var validCalls = 0
        for ((game, gameBiz) in biz) {
            var answered = false
            for (base in ROLE_ENDPOINTS) {
                try {
                    val endpoint = "$base?game_biz=${GameNet.encode(gameBiz)}"
                    val payload = data(GameNet.json(endpoint, headers = headers(cookie)))
                    val rows = payload.optJSONArray("list") ?: JSONArray()
                    validCalls++
                    answered = true
                    for (index in 0 until rows.length()) {
                        val item = rows.optJSONObject(index) ?: continue
                        val returnedBiz = item.optString("game_biz")
                        // 요청한 게임과 다른 게임 데이터가 반환되면 저장하지 않는다.
                        if (returnedBiz.isNotBlank() && returnedBiz != gameBiz) continue
                        val uid = item.optString("game_uid").ifBlank { item.optString("uid") }
                        val server = item.optString("region").ifBlank { item.optString("server") }
                        if (uid.isBlank() || server.isBlank()) continue
                        val role = GameRole(game, uid, server, item.optString("nickname"))
                        found["${role.game}:${role.uid}:${role.server}"] = role
                    }
                    // 해당 게임의 API가 정상 응답하면 다른 호스트를 또 호출하지 않는다.
                    break
                } catch (error: Exception) {
                    // 쿠키·UID는 기록하지 않고 도메인 및 오류 종류만 기억한다.
                    failures.add("$game: ${error.message ?: error.javaClass.simpleName}")
                }
            }
            if (!answered) failures.add("$game: 게임 목록 API 확인 실패")
        }
        if (found.isNotEmpty()) return found.values.toList()
        if (validCalls > 0) return emptyList() // API는 성공했지만 연결 캐릭터가 없음
        throw IllegalStateException("HoYoLAB 캐릭터 조회 실패: " + failures.distinct().take(3).joinToString(" / "))
    }

    /** 아시아 서버인지 게임별 서버 코드를 기준으로 판단한다. */
    fun isAsiaRole(role: GameRole): Boolean {
        if (role.game == "endfield") return true // SKPORT 조회 단계에서 이미 서버를 제한함
        val value = role.server.lowercase()
        return when (role.game) {
            "genshin" -> value == "os_asia" || value.contains("asia")
            "hsr" -> value == "prod_official_asia" || value.contains("asia")
            "zzz" -> value == "prod_gf_jp" || value == "prod_gf_sg" || value.contains("asia")
            else -> false
        }
    }

    /**
     * OS 게임 기록 API가 일부 요청에 요구하는 DS 동적 서명.
     * 이 값은 비밀번호가 아니라 요청 시각과 랜덤 값으로 만드는 일회성 요청 헤더다.
     * 라이브러리 michos-api 의 글로벌 DS 방식(2026-10 확인)을 참고했다.
     * 게임사가 salt를 교체하면 별도 업데이트가 필요하다.
     */
    private fun dsOs(): String {
        val t = Instant.now().epochSecond
        val alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        val rnd = SecureRandom()
        val r = (1..6).map { alphabet[rnd.nextInt(alphabet.length)] }.joinToString("")
        val raw = "salt=6s25p5ox5y14umn1p61aqyyvbvvl3lrt&t=$t&r=$r"
        val sum = MessageDigest.getInstance("MD5").digest(raw.toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it.toInt() and 255) }
        return "$t,$r,$sum"
    }

    /**
     * 글로벌 게임별 실시간 메모 원본의 data를 조회한다.
     * HTTP 200 + retcode=0만 성공으로 판단한다.
     * 스타레일은 호스트와 x-rpc-client_type 5/4를 필요할 때만 각각 시도한다.
     */
    fun note(cookie: String, role: GameRole): JSONObject {
        val endpoints = noteEndpoints[role.game] ?: throw IllegalArgumentException("지원하지 않는 HoYoLAB 게임")
        val query = "server=${GameNet.encode(role.server)}&role_id=${GameNet.encode(role.uid)}"
        val problems = mutableListOf<String>()
        for (base in endpoints) {
            // 스타레일 -10001은 게임 기록 공개 설정 외에 헤더/DS 불일치에서도 나타난다.
            // 원신의 성공 경로는 그대로 한 번만 호출한다.
            val profiles = if (role.game == "hsr") listOf("5", "4") else listOf("5")
            for (profile in profiles) {
                try {
                    val h = headers(cookie).toMutableMap()
                    h["x-rpc-client_type"] = profile
                    if (profile == "5" && role.game == "hsr") {
                        h["Referer"] = "https://webstatic-sea.hoyolab.com/"
                        h["DS"] = dsOs()
                    } else h["Referer"] = "https://www.hoyolab.com/"
                    return data(GameNet.json("$base?$query", headers=h))
                } catch (error: Exception) {
                    // URL 쿼리에는 UID가 포함되므로 사용자 보고문에는 호스트/프로필만 포함한다.
                    problems.add("${URL(base).host} / profile=$profile: ${error.message ?: error.javaClass.simpleName}")
                }
            }
        }
        val hint = when (role.game) {
            "hsr" -> "스타레일 게임 기록의 실시간 메모 공개 설정, UID·서버, HoYoLAB 쿠키를 확인하세요."
            "zzz" -> "젠존제 기록 공개 설정과 HoYoLAB 인증 쿠키를 확인하세요."
            else -> "HoYoLAB 인증 상태를 확인하세요."
        }
        throw IllegalStateException("${role.game} 데이터 조회 실패: ${problems.take(3).joinToString(" / ")} ($hint)")
    }

    /**
     * 실제 기록 API에 존재하는 점수형 필드만 Todoist 자동 완료 판정에 사용한다.
     * 배터리/레진/개척력은 자원 수치이지 '일퀘 완료'가 아니므로 Gauge에 넣지 않는다.
     */
    fun progress(cookie: String, role: GameRole): List<AccountGauge> = progressFromNote(role, note(cookie, role))

    fun progressFromNote(role: GameRole, note: JSONObject): List<AccountGauge> {
        val gauges = mutableListOf<AccountGauge>()
        fun add(metric: String, current: Int?, max: Int?) {
            if (current != null && max != null && max > 0 && current >= 0)
                gauges.add(AccountGauge(role.game, role.uid, metric, current, max))
        }
        when (role.game) {
            "genshin" -> {
                add("daily", readNumber(note,"finished_task_num"),
                    readNumber(note,"total_task_num") ?: 4)
                WeeklyProgress.genshin(note,role)?.let { gauges.add(it) }
            }
            "hsr" -> {
                // 500은 게임 규칙상 일일 훈련 최대 점수. 실제 현재 점수 필드가 있어야 한다.
                add("daily", readNumber(note, "current_train_score"),
                    readNumber(note, "max_train_score") ?: 500)
                WeeklyProgress.hsr(note,role)?.let { gauges.add(it) }
            }
            "zzz" -> {
                // 글로벌 ZZZ note에서 확인된 필드: vitality, weekly_task.
                add("daily", readNumber(note, "vitality.current", "engagement.current"),
                    readNumber(note, "vitality.max", "engagement.max"))
                add("weekly_task", readNumber(note, "weekly_task.cur_point"),
                    readNumber(note, "weekly_task.max_point"))
                WeeklyProgress.zzz(note,role)?.let { gauges.add(it) }
            }
        }
        return gauges
    }

    /**
     * 위젯처럼 화면에서 확인 가능한 기록들을 텍스트로 표시한다.
     * 없는 필드를 0이나 '완료'로 대체하지 않고 해당 줄을 숨긴다.
     * 게임 화면 OCR을 전혀 사용하지 않는다.
     */
    fun detailLines(role: GameRole, note: JSONObject): List<String> {
        val lines = mutableListOf<String>()
        fun gauge(title: String, cur: Int?, max: Int?) {
            if (cur != null && max != null && max > 0) lines.add("$title  $cur/$max")
        }
        fun value(title: String, field: String, suffix: String = "") {
            val got = readNumber(note,field)
            if (got != null) lines.add("$title  $got$suffix")
        }
        fun status(title: String, field: String, done: String) {
            val got = readString(note,field)
            if (!got.isNullOrBlank()) lines.add("$title  ${if(got==done) "완료" else got}")
        }
        when(role.game) {
            "genshin" -> {
                gauge("레진",readNumber(note,"current_resin"),readNumber(note,"max_resin"))
                gauge("일일 의뢰",readNumber(note,"finished_task_num"),4)
                value("주간 보스 할인 남음", "remain_resin_discount_num","회")
            }
            "hsr" -> {
                gauge("개척력",readNumber(note,"current_stamina"),readNumber(note,"max_stamina"))
                value("예비 개척력", "current_reserve_stamina")
                gauge("일일 훈련",readNumber(note,"current_train_score"),
                    readNumber(note,"max_train_score") ?: 500)
                gauge("시뮬레이션 우주·화폐 전쟁 통합 포인트",
                    readNumber(note,"current_rogue_score", "rogue_score"),
                    readNumber(note,"max_rogue_score", "rogue_max_score"))
                readNumber(note, "remaining_weekly_discounts", "weekly_cocoon_cnt")?.let { remaining ->
                    lines.add("역전의 여운 주간 할인 보상 남음  ${remaining}회")
                }
                value("탐사 파견 완료", "accepted_expedition_num")
            }
            "zzz" -> {
                gauge("배터리",readNumber(note,"energy.progress.current"),readNumber(note,"energy.progress.max"))
                gauge("일일 활약도",readNumber(note,"vitality.current"),readNumber(note,"vitality.max"))
                gauge("주간 활약도",readNumber(note,"weekly_task.cur_point"),readNumber(note,"weekly_task.max_point"))
                gauge("현상금 의뢰",readNumber(note,"bounty_commission.num"),readNumber(note,"bounty_commission.total"))
                status("비디오 가게", "vhs_sale.sale_state", "SaleStateDone")
                status("일일 보상", "card_sign", "CardSignDone")
            }
        }
        lines.addAll(WeeklyProgress.diagnostic(note,role.game))
        // HoYoLAB 실시간 메모의 부가 상태를 별도 화면 구역으로 보여준다.
        // 보조 필드가 있다고 자동 완료 판정에 임의로 추가하지 않는다.
        val memo = RealTimeMemo.detailLines(role.game, note)
            .filterNot { it in lines }
        if (memo.isNotEmpty()) {
            lines.add("— 실시간 메모 부가 정보 —")
            lines.addAll(memo)
        }
        return lines
    }
}

/** 문자열/부울 값을 의미 그대로 읽는다. 없는 값을 완료로 간주하지 않는다. */
fun readString(root: JSONObject, path: String): String? {
    var at: Any? = root
    for (piece in path.split('.')) at = (at as? JSONObject)?.opt(piece)
    return at?.toString()?.takeIf { it != "null" && it.isNotBlank() }
}


/** 특정 JSON 필드가 실제 정수일 때만 채택한다. 없는 필드를 0으로 간주하면 오판한다. */
fun readNumber(root: JSONObject, vararg paths: String): Int? {
    for (path in paths) {
        var at: Any? = root
        for (part in path.split('.')) {
            at = (at as? JSONObject)?.opt(part)
        }
        when (at) {
            is Int -> return at
            is Long -> if (at in Int.MIN_VALUE..Int.MAX_VALUE) return at.toInt()
            is String -> at.toIntOrNull()?.let { return it }
        }
    }
    return null
}

object EndfieldProvider {
    private const val CODE_APP = "6eb76d4e13aa36e6"
    private fun value(root: JSONObject, name: String): String {
        val nested = root.optJSONObject("data")
        return nested?.optString(name)?.takeIf { it.isNotBlank() }
            ?: root.optString(name).takeIf { it.isNotBlank() && it != "0" } ?: ""
    }
    /** 공식 페이지 로그인으로 얻은 ACCOUNT_TOKEN 유효성만 확인한다. */
    fun verify(token: String) {
        val j = GameNet.json("https://as.gryphline.com/user/info/v1/basic",
            headers = mapOf("Authorization" to "Bearer $token", "x-language" to "ko-kr"))
        if (j.optJSONObject("data")?.optJSONObject("basicUser") == null)
            throw IllegalStateException("SKPORT 계정 정보 검증 실패")
    }
    data class Session(val cred: String, val salt: String)
    /**
     * 공식 SKPORT 페이지의 WebView에서 가져온 인증 정보를 해석한다.
     * 종류 1: ACCOUNT_TOKEN (쿠키) -> OAuth 코드 -> cred
     * 종류 2: SK_OAUTH_CRED_KEY (쿠키) -> cred -> refresh
     * SK_TOKEN_CACHE_KEY는 WebView localStorage에 있을 수 있는 서명용 캐시다.
     * 비밀번호/캡차 우회나 다른 앱의 비공개 저장소 읽기는 하지 않는다.
     */
    fun session(auth: String): Session {
        val credential = try { JSONObject(auth) } catch (_: Exception) { null }
        val cred = credential?.optString("cred").orEmpty()
        val cachedSalt = credential?.optString("salt").orEmpty()
        if (cred.isNotBlank()) {
            // 캐시된 키보다 서버에서 갱신한 서명 키를 우선한다.
            // 일시적인 네트워크 장애일 때만 기존 캐시를 사용한다.
            val fresh = try { refreshSalt(cred) } catch (_: Exception) { cachedSalt }
            if (fresh.isBlank()) throw IllegalStateException("SKPORT 서명 키를 갱신하지 못했습니다")
            return Session(cred, fresh)
        }
        val token = credential?.optString("accountToken")?.takeIf { it.isNotBlank() } ?: auth
        if (token.isBlank() || token.trimStart().startsWith("SK_") || token.contains(";"))
            throw IllegalStateException("SKPORT 인증 정보 없음: ACCOUNT_TOKEN 또는 SK_OAUTH_CRED_KEY 확인 필요")
        val oauth = GameNet.json("https://as.gryphline.com/user/oauth2/v2/grant", "POST",
            JSONObject().put("token", token).put("appCode", CODE_APP).put("type", 0))
        val code = oauth.optJSONObject("data")?.optString("code").orEmpty()
        if (code.isBlank() || code == "0") throw IllegalStateException("SKPORT OAuth 승인 코드 없음")
        val credJ = GameNet.json("https://zonai.skport.com/web/v1/user/auth/generate_cred_by_code",
            "POST", JSONObject().put("kind", 1).put("code", code))
        val issuedCred = value(credJ, "cred")
        if (issuedCred.isBlank()) throw IllegalStateException("SKPORT cred 없음")
        return Session(issuedCred, refreshSalt(issuedCred))
    }

    private fun refreshSalt(cred: String): String {
        val response = GameNet.json("https://zonai.skport.com/web/v1/auth/refresh",
            headers = mapOf("cred" to cred, "Origin" to "https://game.skport.com"))
        return value(response, "token").ifBlank { value(response, "salt") }
            .ifBlank { throw IllegalStateException("SKPORT 서명 키 갱신 실패") }
    }

    private fun signed(path: String, s: Session, query: String = "", role: String? = null): JSONObject {
        val timestamp = Instant.now().epochSecond.toString()
        // 정해진 JSON 직렬화 순서/공백도 서명 검증에 영향을 미친다.
        val headerJson = "{\"platform\":\"3\",\"timestamp\":\"$timestamp\",\"dId\":\"\",\"vName\":\"1.0.0\"}"
        val mac = Mac.getInstance("HmacSHA256")
        mac.init(SecretKeySpec(s.salt.toByteArray(Charsets.UTF_8), "HmacSHA256"))
        val digest = mac.doFinal((path + query + timestamp + headerJson).toByteArray(Charsets.UTF_8))
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }
        val sign = MessageDigest.getInstance("MD5").digest(digest.toByteArray(Charsets.US_ASCII))
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }
        val headers = mutableMapOf("cred" to s.cred, "sign" to sign, "platform" to "3",
            "timestamp" to timestamp, "dId" to "", "vName" to "1.0.0", "Origin" to "https://game.skport.com",
            "Referer" to "https://game.skport.com/", "sk-language" to "ko-kr")
        if (role != null) headers["sk-game-role"] = role
        return GameNet.json("https://zonai.skport.com$path" + if (query.isBlank()) "" else "?$query", headers = headers)
    }
    fun roles(token: String): List<GameRole> {
        val s = session(token)
        val binding = signed("/api/v1/game/player/binding", s)
        val rows = binding.optJSONObject("data")?.optJSONArray("list")
            ?: throw IllegalStateException("SKPORT 캐릭터 바인딩 목록 형식 변경(data.list 없음)")
        val found = mutableListOf<GameRole>()
        for (i in 0 until rows.length()) {
            val group = rows.getJSONObject(i)
            if (group.optString("appCode") != "endfield") continue
            val bindings = group.optJSONArray("bindingList") ?: JSONArray()
            for (j in 0 until bindings.length()) {
                val item = bindings.getJSONObject(j)
                val list = JSONArray().put(item.optJSONObject("defaultRole"))
                val other = item.optJSONArray("roles") ?: JSONArray()
                for (k in 0 until other.length()) list.put(other.getJSONObject(k))
                for (k in 0 until list.length()) {
                    val role = list.optJSONObject(k) ?: continue
                    val server = role.optString("serverName")
                    val id = role.optString("roleId")
                    val serverId = role.optString("serverId")
                    // 글로벌 엔드필드의 Asia 서버 ID는 2. 화면 언어에 따른 서버명 변형도 지원.
                    val asia = serverId == "2" || listOf("asia", "아시아", "亞洲", "亚洲", "アジア")
                        .any { server.contains(it, ignoreCase = true) }
                    if (id.isNotBlank() && serverId.isNotBlank() && asia)
                        found.add(GameRole("endfield", id, serverId, role.optString("nickname")))
                }
            }
        }
        return found.distinctBy { it.uid + it.server }
    }
    fun progress(token: String, role: GameRole): List<AccountGauge> {
        val s = session(token)
        val query = "roleId=${GameNet.encode(role.uid)}&serverId=${GameNet.encode(role.server)}"
        val detail = signed("/api/v1/game/endfield/card/detail", s, query,
            "3_${role.uid}_${role.server}").optJSONObject("data")
                ?: throw IllegalStateException("SKPORT 캐릭터 상세 data 없음")
        val daily = detail.optJSONObject("detail")?.optJSONObject("dailyMission")
            ?: detail.optJSONObject("dailyMission") ?: return emptyList()
        val cur = readNumber(daily,"dailyActivation")
        val max = readNumber(daily,"maxDailyActivation")
        return if (cur != null && max != null && max > 0)
            listOf(AccountGauge("endfield",role.uid,"daily",cur,max)) else emptyList()
    }
}

/** 지원 여부는 '로그인 페이지가 존재'가 아니라 '검증된 계정 상태 API' 기준이다. */
object ProviderCapabilities {
    val statuses = linkedMapOf(
        "genshin" to "HoYoLAB 계정 조회 및 일퀘 점수 (실계정 확인 필요)",
        "hsr" to "HoYoLAB 실시간 메모: 개척력·일일 훈련, 요청 헤더 DS 지원 (실계정 확인 필요)",
        "zzz" to "HoYoLAB 글로벌 sg-public API: 배터리·일퀘·주간 점수 (실계정 확인 필요)",
        "endfield" to "SKPORT 아시아 캐릭터 조회 및 일퀘 점수 (실계정 확인 필요)",
        "wuthering" to "글로벌: 신뢰할 수 있는 개인 일일 진행도 API 미확인, 자동 완료 안 함",
        "arknights" to "한국: ArkPRTS Python 연동 존재, Android 직접 로그인 미구현",
        "limbus" to "개인 진행도 외부 API 미확인, 플로팅 수동 체크만",
        "reverse1999" to "개인 진행도 외부 API 미확인, 플로팅 수동 체크만",
        "stella" to "개인 진행도 외부 API 미확인, 플로팅 수동 체크만"
    )
}
