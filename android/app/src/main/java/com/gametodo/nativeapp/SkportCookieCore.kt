package com.gametodo.nativeapp

/**
 * SKPORT의 인증 쿠키만 화이트리스트로 추출한다.
 * 중요: HoYoLAB 쿠키 파서를 재사용하면 SKPORT 쿠키가 모두 제거된다.
 * 디버깅은 이름과 존재 여부로만 하며 실제 비밀 값은 로깅하지 않는다.
 */
object SkportCookieCore {
    private val allowed = setOf("ACCOUNT_TOKEN", "SK_OAUTH_CRED_KEY", "HG_INFO_KEY", "SK_COOKIES_INFO", "SK_TOKEN_CACHE_KEY")

    fun header(headers: List<String?>): String {
        val values = linkedMapOf<String,String>()
        headers.filterNotNull().forEach { raw ->
            raw.split(';').forEach { part ->
                val index=part.indexOf('=')
                if(index>0) {
                    val name=part.substring(0,index).trim()
                    val value=part.substring(index+1).trim()
                    if(name in allowed && value.isNotBlank() && name !in values) values[name]=value
                }
            }
        }
        return values.entries.joinToString("; ") { "${it.key}=${it.value}" }
    }

    /** 쿠키를 직접 입력할 필요 없이, 앱 WebView에서 얻은 값만 특정 이름으로 조회한다. */
    fun value(cookieHeader: String, name: String): String? = cookieHeader.split(';')
        .mapNotNull { item ->
            val idx = item.indexOf('=')
            if (idx <= 0) null else item.substring(0, idx).trim() to item.substring(idx + 1).trim()
        }.firstOrNull { it.first == name }?.second?.takeIf { it.isNotBlank() }

    fun names(headers: List<String?>): Set<String> = buildSet {
        headers.filterNotNull().forEach { raw ->
            raw.split(';').forEach { part ->
                val p=part.indexOf('=')
                if(p>0) add(part.substring(0,p).trim())
            }
        }
    }
}
