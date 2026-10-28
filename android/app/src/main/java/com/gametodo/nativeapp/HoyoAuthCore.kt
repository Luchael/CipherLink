package com.gametodo.nativeapp

/**
 * HoYoLAB 계정 인증용 쿠키 처리.
 *
 * 중요: HoYoLAB에서 로그인했을 때 우리 앱의 WebView가 받은 쿠키만 사용한다.
 * 다른 앱/브라우저의 보안 저장소는 건드리지 않는다.
 * DEVICEFP, UUID, 추적 동의/언어 쿠키는 로그인 인증에 불필요하므로 저장하지 않는다.
 */
object HoyoAuthCore {
    private val authNames = setOf(
        "ltuid", "ltoken", "ltmid", "ltuid_v2", "ltoken_v2", "ltmid_v2",
        "account_id", "account_id_v2", "account_mid_v2",
        "cookie_token", "cookie_token_v2", "stoken", "stoken_v2"
    )

    // 사용자가 알려준 목록: 진단에서만 이름을 보여주고 실제 값은 절대로 출력하지 않는다.
    val diagnosticNames = setOf(
        "mi18nLang", "_HYVUUID", "HYV_LOGIN_PLATFORM_OPTIONAL_AGREEMENT",
        "DEVICEFP_SEED_ID", "DEVICEFP_SEED_TIME", "_MHYUUID", "DEVICEFP",
        "HYV_LOGIN_PLATFORM_TRACKING_MAP", "HYV_LOGIN_PLATFORM_LOAD_TIMEOUT",
        "cookie_token_v2", "account_mid_v2", "account_id_v2",
        "ltoken_v2", "ltmid_v2", "ltuid_v2", "ma_passport_region", "age_gate_country"
    )

    /** 도메인별 Cookie: HTTP 헤더들을 병합하되, 실제로 필요한 인증 쿠키만 반환. */
    fun merge(cookieHeaders: List<String?>): LinkedHashMap<String, String> {
        val cookies = linkedMapOf<String, String>()
        for (raw in cookieHeaders) {
            if (raw.isNullOrBlank()) continue
            raw.split(';').forEach { pair ->
                val eq = pair.indexOf('=')
                if (eq <= 0) return@forEach
                val name = pair.substring(0, eq).trim()
                val value = pair.substring(eq + 1).trim()
                if (name in authNames && value.isNotEmpty() && name !in cookies) cookies[name] = value
            }
        }
        return cookies
    }

    /** 쿠키가 어느 사이트에 설정되었는지 확인하기 위한 '이름만' 반환. */
    fun seenNames(cookieHeaders: List<String?>): Set<String> = buildSet {
        cookieHeaders.forEach { raw ->
            raw?.split(';')?.forEach { pair ->
                val eq = pair.indexOf('=')
                if (eq > 0) add(pair.substring(0, eq).trim())
            }
        }
    }

    /** v2 인증의 주요 조합. ID는 ltuid 대신 account_mid/account_id로 설정되기도 한다. */
    fun hasSession(cookies: Map<String, String>): Boolean =
        (cookies.containsKey("ltoken_v2") && listOf("ltuid_v2", "account_mid_v2", "account_id_v2").any(cookies::containsKey)) ||
        (cookies.containsKey("cookie_token_v2") && listOf("account_id_v2", "ltuid_v2").any(cookies::containsKey)) ||
        (cookies.containsKey("ltoken") && cookies.containsKey("ltuid")) ||
        (cookies.containsKey("cookie_token") && cookies.containsKey("account_id"))

    fun asHeader(cookies: Map<String, String>): String =
        cookies.entries.joinToString("; ") { (name, value) -> "$name=$value" }

    /** 단순 상태 안내: 민감한 토큰 값이나 길이도 표시하지 않는다. */
    fun diagnostics(cookies: Map<String, String>, seen: Set<String> = cookies.keys): String {
        val names = seen.filter { it in diagnosticNames || it in authNames }.sorted().joinToString(", ").ifBlank { "없음" }
        val missing = listOf("ltoken_v2", "ltuid_v2", "cookie_token_v2", "account_id_v2")
            .filterNot(cookies::containsKey).joinToString(", ").ifBlank { "없음" }
        return "확인된 쿠키 이름: $names\n" +
            "API 인증 쿠키: ${if (hasSession(cookies)) "기본 조합 확인" else "부족함"}\n" +
            "미확인 대표 쿠키: $missing\n" +
            "참고: 모든 쿠키가 있어야 하는 것은 아닙니다. 로그인 후 실제 캐릭터 API로 최종 확인합니다."
    }
}
