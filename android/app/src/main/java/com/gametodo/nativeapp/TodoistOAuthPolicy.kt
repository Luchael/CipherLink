package com.gametodo.nativeapp

object TodoistOAuthPolicy {
    const val REGISTER = "https://todoist.com/oauth/register"
    const val AUTHORIZE = "https://todoist.com/oauth/authorize"
    const val TOKEN = "https://todoist.com/oauth/access_token"
    const val CALLBACK = "http://127.0.0.1:18766/callback"
    fun expiry(seconds: Long?, nowMs: Long): Long =
        if (seconds == null || seconds <= 0 || seconds > (Long.MAX_VALUE - nowMs) / 1000) 0L else nowMs + seconds * 1000
    fun needsRefresh(expiryMs: Long, nowMs: Long) = expiryMs > 0 && nowMs >= expiryMs - 120000L
    fun validCallback(path: String?, state: String?, expected: String, code: String?) =
        path == "/callback" && state == expected && !code.isNullOrBlank()
}
