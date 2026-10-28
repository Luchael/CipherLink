package com.gametodo.nativeapp

import android.content.Context
import android.content.Intent
import android.net.Uri
import org.json.JSONObject
import java.net.InetAddress
import java.net.ServerSocket
import java.net.SocketTimeoutException
import java.net.URLEncoder
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64

/**
 * Todoist 공식 OAuth 동적 클라이언트 등록 + PKCE.
 * - 개발자 API 키를 사용자가 복사하지 않는다.
 * - 앱은 비밀번호/이메일 OTP를 받지 않는다 (외부 기본 브라우저에서 진행).
 * - 앱 내부 127.0.0.1 콜백 서버는 로그인할 때 잠시만 열린다.
 * - 주의: localhost 개발용 리디렉션의 배포 정책은 별도 실기기 검증이 필요하다.
 */
class TodoistAuth(private val context: Context) {
    // PC/모바일 동시 실행은 별도 로그인 세션이므로 갱신 토큰 충돌 없음.
    // 단일 Android 프로세스 내 worker/플로팅 간 갱신 경쟁만 방지한다.
    companion object { private val refreshLock = Any() }
    private val store = SecureTokens(context)
    private val callback = "http://localhost:18766/callback"

    private fun randomString(): String = ByteArray(32).also { SecureRandom().nextBytes(it) }
        .let { Base64.getUrlEncoder().withoutPadding().encodeToString(it) }

    private fun encode(value: String): String = URLEncoder.encode(value, "UTF-8")

    private fun form(vararg values: Pair<String, String>): String = values.joinToString("&") {
        encode(it.first) + "=" + encode(it.second)
    }

    fun accessToken(): String {
        return synchronized(refreshLock) {
        val session = JSONObject(store.load() ?: throw IllegalStateException("Todoist 로그인이 필요합니다"))
        val old = session.optString("access_token")
        if (old.isBlank()) throw IllegalStateException("Todoist 로그인이 필요합니다")
        if (System.currentTimeMillis() < session.optLong("expires_at_ms") - 120000L) return@synchronized old
        val refresh = session.optString("refresh_token")
        if (refresh.isBlank()) throw IllegalStateException("토큰 갱신 불가: 다시 로그인해 주세요")
        val response = JSONObject(HttpApi.tokenForm(mapOf(
            "client_id" to session.getString("client_id"),
            "grant_type" to "refresh_token", "refresh_token" to refresh)))
        session.put("access_token", response.getString("access_token"))
        session.put("refresh_token", response.optString("refresh_token", refresh))
        session.put("expires_at_ms", System.currentTimeMillis() +
            response.optLong("expires_in", 3600L) * 1000L)
        store.save(session.toString())
        session.getString("access_token")
        }
    }

    fun isConnected(): Boolean = try { accessToken().isNotBlank() } catch (_: Exception) { false }

    fun logout() = store.clear()

    fun login(onStatus: (String) -> Unit) {
        // 호출자는 별도 스레드에서 실행해야 함. 인증을 위해 최대 180초 기다린다.
        onStatus("[1/4] Todoist OAuth 앱 등록")
        val existing = store.load()?.let { JSONObject(it) }
        val client = existing?.optString("client_id")?.takeIf { it.isNotBlank() }
            ?: JSONObject(HttpApi.request("https://api.todoist.com/oauth/register", "POST",
                JSONObject().put("client_name", "QuestLink Android")
                    .put("redirect_uris", org.json.JSONArray().put(callback))
                    .put("scope", "data:read_write")
                    .put("grant_types", org.json.JSONArray().put("authorization_code").put("refresh_token"))
                    .put("response_types", org.json.JSONArray().put("code"))
                    .put("token_endpoint_auth_method", "none")))
                .getString("client_id")
        // 새로고침/로그인 취소 시에도 OAuth 클라이언트 ID 재등록을 피한다.
        if (existing?.optString("client_id") != client)
            store.save(JSONObject().put("client_id", client).toString())
        val state = randomString()
        val verifier = randomString()
        val challenge = Base64.getUrlEncoder().withoutPadding().encodeToString(
            MessageDigest.getInstance("SHA-256").digest(verifier.toByteArray(Charsets.US_ASCII)))
        // 임의의 외부 클라이언트가 인증 코드를 수신하지 않도록 127.0.0.1에만 바인딩.
        ServerSocket(18766, 1, InetAddress.getByName("127.0.0.1")).use { server ->
            server.soTimeout = 180000
            val params = form("client_id" to client, "scope" to "data:read_write",
                "state" to state, "response_type" to "code", "redirect_uri" to callback,
                "code_challenge" to challenge, "code_challenge_method" to "S256")
            onStatus("[2/4] 공식 브라우저에서 로그인과 인증 완료")
            context.startActivity(Intent(Intent.ACTION_VIEW,
                Uri.parse("https://app.todoist.com/oauth/authorize?$params"))
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
            val code = try {
                server.accept().use { socket ->
                    socket.soTimeout = 10000
                    val input = socket.getInputStream().bufferedReader()
                    val request = input.readLine() ?: ""
                    // 헤더까지 읽고 난 뒤 처리 (keep-alive 응답 방지).
                    while (true) { val line = input.readLine(); if (line.isNullOrEmpty()) break }
                    val path = request.split(' ').getOrNull(1) ?: ""
                    val uri = Uri.parse("http://localhost$path")
                    val valid = uri.path == "/callback" && uri.getQueryParameter("state") == state
                    val code = if (valid) uri.getQueryParameter("code") else null
                    val ok = code != null
                    val body = if (ok) "인증 정보를 받았습니다. 사이퍼링크로 돌아가세요." else "인증에 실패했습니다."
                    val bytes = body.toByteArray(Charsets.UTF_8)
                    socket.getOutputStream().write(("HTTP/1.1 ${if (ok) 200 else 403} ${if (ok) "OK" else "Forbidden"}\r\n" +
                        "Content-Type: text/plain; charset=utf-8\r\nContent-Length: ${bytes.size}\r\nConnection: close\r\n\r\n")
                        .toByteArray(Charsets.US_ASCII) + bytes)
                    code ?: throw IllegalStateException("OAuth state 확인 실패 또는 로그인 취소")
                }
            } catch (_: SocketTimeoutException) {
                throw IllegalStateException("로그인 시간 초과. 다시 연결해 주세요")
            }
            onStatus("[3/4] 승인 코드 교환 및 API 연결 시험")
            val response = JSONObject(HttpApi.tokenForm(mapOf(
                "client_id" to client, "code" to code, "grant_type" to "authorization_code",
                "code_verifier" to verifier, "redirect_uri" to callback)))
            val access = response.getString("access_token")
            // API 검증 전에는 저장하지 않는다.
            HttpApi.request("https://api.todoist.com/api/v1/tasks?limit=1", token = access)
            val session = JSONObject().put("client_id", client)
                .put("access_token", access)
                .put("refresh_token", response.optString("refresh_token"))
                .put("expires_at_ms", System.currentTimeMillis() + response.optLong("expires_in", 3600L) * 1000L)
            store.save(session.toString())
            onStatus("[4/4] Todoist 연결 완료")
        }
    }
}
