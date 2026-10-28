package com.gametodo.nativeapp

import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant

/**
 * 사용자가 누른 경우에만 실행되는 비식별 API 스키마 진단.
 * 절대 원본 API 응답/URL/UID/토큰/이름을 파일에 기록하지 않는다.
 * 숫자는 별·점수·회차·시간에 한해 보존한다. 문자열은 날짜·등급 외 삭제한다.
 * GET 요청만 사용한다. Todoist에는 어떤 변경도 보내지 않는다.
 */
object SafeApiDiagnostics {
    private val keyPattern = Regex("[A-Za-z][A-Za-z0-9_]{0,55}")
    private val sensitive = Regex("(?i)(cookie|token|secret|auth|passwd|password|session|signature|email|phone|device|nickname|name|avatar|icon|image|url|link|user|player|account|uid|role|id$|_id$|character|weapon|member|lineup|description|desc|title|text|key|hash|ip_address)")
    private val usefulNumber = Regex("(?i)(star|score|stella|medal|count|num|rank|progress|rate|floor|layer|round|start|end|begin|time|duration|current|maximum|total|schedule_type|difficulty|pass|clear|done|award|reward|percent|level|grade|status|stage|settle|finish)")
    private val dates = Regex("\\d{4}-\\d{2}-\\d{2}(?:[T ]\\d{2}:\\d{2}(?::\\d{2})?(?:Z|[+-]\\d{2}:?\\d{2})?)?")
    private val enums = setOf("S", "S+", "SS", "A", "B", "C", "D", "v1", "v2", "true", "false")
    private const val MAX_DEPTH = 7
    private const val MAX_KEYS = 36
    private const val MAX_SAMPLE = 3
    private const val MAX_REQUESTS = 24

    /** 단순 자료형 진단은 순수 함수이므로 테스트에서 모의 API 응답만 사용 가능. */
    fun sanitized(value: Any?, key: String = "", depth: Int = 0): Any {
        if (depth >= MAX_DEPTH) return "<depth_limit>"
        if (value == null || value == JSONObject.NULL) return JSONObject.NULL
        when (value) {
            is JSONObject -> {
                val out = JSONObject()
                val keys = mutableListOf<String>()
                val iter = value.keys()
                while (iter.hasNext()) keys.add(iter.next())
                // 순서를 일정하게 하여 PC 진단과 구조 비교가 쉽도록 함.
                var written = 0
                for (field in keys.sorted()) {
                    if (written >= MAX_KEYS) break
                    if (!keyPattern.matches(field) || sensitive.containsMatchIn(field)) continue
                    out.put(field, sanitized(value.opt(field), field, depth + 1))
                    written++
                }
                out.put("_schema_key_count", value.length())
                return out
            }
            is JSONArray -> {
                val out = JSONObject()
                out.put("_array_length", value.length())
                val samples = JSONArray()
                for (idx in 0 until minOf(MAX_SAMPLE, value.length())) {
                    samples.put(sanitized(value.opt(idx), key, depth + 1))
                }
                out.put("_first_samples", samples)
                if (key.contains("star", true) || key.contains("medal_round", true)) {
                    val vals = (0 until value.length()).map { value.opt(it) }
                    if (vals.all { it is Boolean }) out.put("_true_count", vals.count { it == true })
                    else if (vals.all { it is Number && it.toInt() in 0..1 })
                        out.put("_ones_count", vals.count { (it as Number).toInt() == 1 })
                }
                return out
            }
            is Boolean -> return value
            is Number -> return when {
                usefulNumber.containsMatchIn(key) -> value
                key == "year" && value.toInt() in 2020..2045 -> value
                key == "month" && value.toInt() in 1..12 -> value
                key == "day" && value.toInt() in 1..31 -> value
                key in setOf("hour", "minute", "second") && value.toInt() in 0..59 -> value
                else -> "<number>"
            }
            is String -> {
                if (dates.matches(value) && usefulNumber.containsMatchIn(key)) return value
                if (value in enums && (key.contains("rank", true) || key.contains("grade",true) || key.contains("rating",true) || key.contains("ver",true))) return value
                // 문자열 안에 토큰·ID가 포함돼도 길이까지 내보내지 않는다.
                return "<string_redacted>"
            }
            else -> return "<unknown>"
        }
    }

    fun fromResponse(mode: String, period: String, response: JSONObject): JSONObject {
        val code = response.opt("retcode")
        return JSONObject().apply {
            put("mode", mode)
            put("requested_period", period)
            put("http", "2xx")
            put("retcode", if (code is Number) code.toInt() else JSONObject.NULL)
            put("schema", sanitized(response.opt("data"), "data"))
        }
    }

    fun fromFailure(mode: String, period: String, error: Exception): JSONObject {
        // 예외 message 자체는 URL/UID/세션 값이 포함될 수 있으므로 절대로 출력 금지.
        val code = Regex("HTTP (\\d{3})").find(error.message.orEmpty())?.groupValues?.get(1)
        return JSONObject().apply {
            put("mode", mode)
            put("requested_period", period)
            put("status", "request_failed")
            put("http_code", code ?: "unknown")
            put("error_type", error.javaClass.simpleName.take(48))
        }
    }

    fun collect(vault: SecureTokens): JSONObject {
        val report = JSONObject().apply {
            put("format", "cipherlink_safe_schema_v2")
            put("created_utc", Instant.now().toString())
            put("sharing", "사용자가 저장한 뒤 검토하고 수동으로 업로드하는 파일")
            put("warning", "로그인 정보 미포함. 정확한 시즌 날짜/점수 등 일부 플레이 진행도는 포함됨. 공유 전 검토할 것")
        }
        val requests = JSONArray()
        val cookie = vault.loadNamed("hoyolab_cookie")
        val roles = loadRoles(vault, "hoyolab_roles")
        val gameCounts = mutableMapOf<String, Int>()
        if (!cookie.isNullOrBlank()) {
            loop@ for (role in roles) {
                if (role.game !in listOf("genshin", "hsr", "zzz")) continue
                val index = (gameCounts[role.game] ?: 0) + 1
                gameCounts[role.game] = index
                for (request in EndgameRecords.diagnosticRequests(role)) {
                    if (requests.length() >= MAX_REQUESTS) break@loop
                    val record = try {
                        val raw = GameNet.json(request.url, headers = HoyoProvider.recordHeaders(cookie))
                        fromResponse(request.mode, request.period, raw)
                    } catch (error: Exception) {
                        fromFailure(request.mode, request.period, error)
                    }
                    record.put("game", role.game)
                    record.put("local_account_index", index) // UID를 해시하거나 저장하지 않음
                    requests.put(record)
                    // 의도하지 않은 고빈도 요청을 피한다. 수동 실행 중 최대 24개.
                    try { Thread.sleep(250) } catch (_: InterruptedException) { Thread.currentThread().interrupt(); break@loop }
                }
            }
        }
        report.put("requests", requests)
        report.put("hoyolab_connected", !cookie.isNullOrBlank())
        report.put("unsupported", JSONArray().apply {
            put(JSONObject().put("game", "wuthering_global")
                .put("state", "개인 일일/엔드 진행도 API 미검증; 중국 KuroBBS 인증 사용 안 함"))
            put(JSONObject().put("game", "arknights_kr_en_jp")
                .put("state", "KR: PC ArkPRTS 옵트인 23:59 조회 가능; Android 단독 인증 어댑터 미연결"))
        })
        return report
    }
}
