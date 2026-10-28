package com.gametodo.nativeapp

import android.content.Context
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.security.MessageDigest

/** 네트워크 요청은 반드시 백그라운드 스레드에서 호출한다. */
object HttpApi {
    fun request(url: String, method: String = "GET", body: JSONObject? = null,
                token: String? = null): String {
        require(url.startsWith("https://")) { "HTTPS 연결만 허용합니다" }
        val conn = URL(url).openConnection() as HttpURLConnection
        try {
            conn.requestMethod = method
            conn.connectTimeout = 12000
            conn.readTimeout = 20000
            conn.setRequestProperty("Accept", "application/json")
            if (token != null) conn.setRequestProperty("Authorization", "Bearer $token")
            if (body != null) {
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json; charset=utf-8")
                conn.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
            }
            val status = conn.responseCode
            val raw = (if (status in 200..299) conn.inputStream else conn.errorStream)
                ?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: ""
            if (status !in 200..299) {
                // 서버 원문에는 개인정보가 들어 있을 수 있으므로 그대로 화면에 노출하지 않음.
                throw IllegalStateException("HTTP $status (${URL(url).host})")
            }
            return raw
        } finally { conn.disconnect() }
    }
    /** OAuth 토큰 발급 API는 JSON 대신 application/x-www-form-urlencoded 전송을 사용한다. */
    fun tokenForm(params: Map<String, String>): String {
        val conn = URL(TodoistOAuthPolicy.TOKEN).openConnection() as HttpURLConnection
        try {
            conn.requestMethod = "POST"
            conn.connectTimeout = 12000
            conn.readTimeout = 20000
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/x-www-form-urlencoded")
            val payload = params.entries.joinToString("&") {
                URLEncoder.encode(it.key, "UTF-8") + "=" + URLEncoder.encode(it.value, "UTF-8")
            }
            conn.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
            val status = conn.responseCode
            if (status !in 200..299) throw IllegalStateException("Todoist 토큰 인증 HTTP $status")
            return conn.inputStream.bufferedReader(Charsets.UTF_8).use { it.readText() }
        } finally { conn.disconnect() }
    }
}

/** 공식 Todoist API v1 연동. Termux·로컬 브리지·PC 서버가 필요 없다. */
class TodoistApi(private val context: Context) {
    private val auth = TodoistAuth(context)
    fun tasks(): List<TodoTask> {
        val token = auth.accessToken()
        val output = mutableListOf<TodoTask>()
        var cursor: String? = null
        // 50페이지 제한: 오류로 무한 반복하거나 배터리를 소모하지 않도록 함.
        repeat(50) {
            val url = "https://api.todoist.com/api/v1/tasks?limit=200" +
                (cursor?.let { "&cursor=" + URLEncoder.encode(it, "UTF-8") } ?: "")
            val result = JSONObject(HttpApi.request(url, token = token))
            val items = result.optJSONArray("results") ?: JSONArray()
            for (i in 0 until items.length()) {
                val task = items.getJSONObject(i)
                if (task.optBoolean("checked") || task.optBoolean("is_completed")) continue
                val labels = task.optJSONArray("labels") ?: JSONArray()
                output += TodoTask(task.getString("id"), task.optString("content"),
                    (0 until labels.length()).map { labels.getString(it) },
                    task.optString("description"), task.optJSONObject("due")?.optString("date"),
                    task.optString("section_id"),task.optString("project_id"),
                    task.optJSONObject("due")?.optString("string"),
                    task.optJSONObject("due")?.let { it.optBoolean("is_recurring", it.optBoolean("recurring", false)) } ?: false,
                    task.optString("parent_id").takeUnless { it.isBlank() || it == "null" })
            }
            cursor = result.optString("next_cursor").takeIf { it.isNotBlank() && it != "null" }
            if (cursor == null) return output
        }
        throw IllegalStateException("Todoist 작업이 너무 많아 전체 목록을 확인하지 못했습니다")
    }

    /** 체크 버튼을 누르기 직전에 서버의 최신 작업 상태를 한 건만 다시 확인한다. */
    fun taskById(id: String): TodoTask? {
        require(id.matches(Regex("[A-Za-z0-9]+")))
        val raw = try {
            JSONObject(HttpApi.request("https://api.todoist.com/api/v1/tasks/$id", token = auth.accessToken()))
        } catch (ex: IllegalStateException) {
            // 삭제되거나 이미 완료되어 단건 조회에서 404가 반환되는 경우 표시를 제거한다.
            if (ex.message?.startsWith("HTTP 404") == true) return null
            throw ex
        }
        if (raw.optBoolean("checked") || raw.optBoolean("is_completed")) return null
        val labels = raw.optJSONArray("labels") ?: JSONArray()
        return TodoTask(raw.getString("id"), raw.optString("content"),
            (0 until labels.length()).map { labels.getString(it) },
            raw.optString("description"), raw.optJSONObject("due")?.optString("date"),
            raw.optString("section_id"), raw.optString("project_id"),
            raw.optJSONObject("due")?.optString("string"),
            raw.optJSONObject("due")?.let { it.optBoolean("is_recurring", it.optBoolean("recurring", false)) } ?: false,
            raw.optString("parent_id").takeUnless { it.isBlank() || it == "null" })
    }

    /** 이벤트 제외와 주기 섹션 정보는 한 번의 요청으로 가져와 캐시에 함께 저장한다. */
    data class FloatingSections(
        val excludedIds: Set<String>,
        val kinds: Map<String, RecurrenceWindow.Kind>
    )

    fun floatingSections(nowMillis: Long = System.currentTimeMillis()): FloatingSections {
        val preferences = context.getSharedPreferences("overlay_section_cache", Context.MODE_PRIVATE)
        val token = auth.accessToken()
        val fingerprint = MessageDigest.getInstance("SHA-256")
            .digest(token.toByteArray(Charsets.UTF_8)).take(8)
            .joinToString("") { "%02x".format(it.toInt() and 0xff) }
        val sameAccount = preferences.getString("account_fingerprint", "") == fingerprint
        val cachedIds = if (sameAccount) preferences.getStringSet("ids", null) else null
        val cachedKinds = if (sameAccount) preferences.getString("period_kinds", null) else null
        val lastFetch = preferences.getLong("updated_at", 0L)
        // 예전 v0.9.1의 섹션 캐시에는 종류가 없기 때문에 자동으로 갱신한다.
        if (cachedIds != null && cachedKinds != null && nowMillis >= lastFetch &&
            nowMillis - lastFetch < 12L * 60 * 60 * 1000) {
            // 캐시 JSON이 손상된 경우에도 앱이 멈추지 않고 API에서 다시 받는다.
            val restored = runCatching {
                val kindJson = JSONObject(cachedKinds)
                val kinds = mutableMapOf<String, RecurrenceWindow.Kind>()
                for (key in kindJson.keys()) {
                    val parsed = runCatching {
                        RecurrenceWindow.Kind.valueOf(kindJson.getString(key))
                    }.getOrNull()
                    if (parsed != null) kinds[key] = parsed
                }
                FloatingSections(cachedIds.toSet(), kinds)
            }.getOrNull()
            if (restored != null) return restored
        }
        try {
            val excluded = mutableSetOf<String>()
            val kinds = mutableMapOf<String, RecurrenceWindow.Kind>()
            var cursor: String? = null
            repeat(50) {
                val url = "https://api.todoist.com/api/v1/sections?limit=200" +
                    (cursor?.let { "&cursor=" + URLEncoder.encode(it, "UTF-8") } ?: "")
                val result = JSONObject(HttpApi.request(url, token = token))
                val sections = result.optJSONArray("results") ?: JSONArray()
                for (i in 0 until sections.length()) {
                    val section = sections.getJSONObject(i)
                    val id = section.getString("id")
                    val name = section.optString("name")
                    if (OverlayTaskPolicy.isEventSectionName(name)) excluded += id
                    kinds[id] = RecurrenceWindow.sectionKind(name)
                }
                cursor = result.optString("next_cursor").takeIf { it.isNotBlank() && it != "null" }
                if (cursor == null) {
                    val kindJson = JSONObject()
                    kinds.forEach { (id, kind) -> kindJson.put(id, kind.name) }
                    preferences.edit().putStringSet("ids", excluded)
                        .putString("period_kinds", kindJson.toString())
                        .putString("account_fingerprint", fingerprint)
                        .putLong("updated_at", nowMillis).apply()
                    return FloatingSections(excluded, kinds)
                }
            }
            error("Todoist 섹션 페이지 제한에 도달했습니다")
        } catch (ex: Exception) {
            throw IllegalStateException("Todoist 섹션/반복 종류 조회 실패. 목록을 표시하지 않습니다.", ex)
        }
    }

    /** 다른 코드 호환용. 새 플로팅은 floatingSections()를 사용한다. */
    fun excludedFloatingSectionIds(nowMillis: Long = System.currentTimeMillis()): Set<String> =
        floatingSections(nowMillis).excludedIds

    /** Todoist에서 대상 섹션 이름이 정확히 하나일 때만 등록. */
    fun bannerSection(): Pair<String,String>? {
        val root = JSONObject(HttpApi.request("https://api.todoist.com/api/v1/sections?limit=200",token=auth.accessToken()))
        val sections = root.optJSONArray("results") ?: JSONArray()
        val found = (0 until sections.length()).map { sections.getJSONObject(it) }
            .filter { it.optString("name") == "이벤트 / 기간 한정" }
        if (found.size != 1 || root.optString("next_cursor").let { it.isNotBlank() && it != "null" }) return null
        return found[0].getString("project_id") to found[0].getString("id")
    }

    /** PC의 banner_sync.py와 동일한 item_add UUIDv5로 재실행/기기간 중복 등록 방지. */
    fun createBanner(projectId: String, sectionId: String, banner: BannerRecord): String? {
        val stable = "banner:$projectId:$sectionId:${banner.key}"
        val uuid = SharedCommandIds.uuid5("item_add", stable)
        val temp = SharedCommandIds.uuid5("banner-temp", stable)
        val args = JSONObject().put("content",banner.title).put("description",banner.description)
            .put("labels",JSONArray().put(banner.label)).put("project_id",projectId).put("section_id",sectionId)
            // 일반 날짜는 무료 플랜에서도 사용 가능. deadline_date는 설정하지 않는다.
            .put("due", JSONObject().put("date",banner.startDate))
        val command = JSONArray().put(JSONObject().put("type","item_add").put("uuid",uuid)
            .put("temp_id",temp).put("args",args))
        val conn = URL("https://api.todoist.com/api/v1/sync").openConnection() as HttpURLConnection
        try {
            conn.requestMethod = "POST"; conn.doOutput = true
            conn.connectTimeout = 12000; conn.readTimeout = 20000
            conn.setRequestProperty("Content-Type","application/x-www-form-urlencoded")
            conn.setRequestProperty("Authorization", "Bearer ${auth.accessToken()}")
            conn.outputStream.use { it.write(("commands="+URLEncoder.encode(command.toString(),"UTF-8")).toByteArray(Charsets.UTF_8)) }
            if (conn.responseCode !in 200..299) throw IllegalStateException("Todoist 생성 HTTP ${conn.responseCode}")
            val response = JSONObject(conn.inputStream.bufferedReader().use { it.readText() })
            if (response.optJSONObject("sync_status")?.optString(uuid) != "ok")
                throw IllegalStateException("Todoist 가챠 생성 승인 실패")
            // 생성 후 전체 목록 재요청을 피하고 서버의 temp_id_mapping을 재사용한다.
            return response.optJSONObject("temp_id_mapping")?.optString(temp)?.takeIf { it.isNotBlank() }
        } finally { conn.disconnect() }
    }

    /** 이전 버전에서 GameTodo가 만든 자동 가챠만 새 양식으로 이전한다. */
    fun updateBanner(taskId: String,banner: BannerRecord) {
        val args = JSONObject().put("id",taskId)
            .put("content",banner.title)
            .put("description",banner.description)
            .put("due",JSONObject().put("date",banner.startDate))
        val uuid = SharedCommandIds.uuid5("item_update","banner-migrate:$taskId:${banner.key}")
        val commands = JSONArray().put(JSONObject().put("type","item_update")
            .put("uuid",uuid).put("args",args))
        val conn = URL("https://api.todoist.com/api/v1/sync").openConnection() as HttpURLConnection
        try {
            conn.requestMethod="POST"; conn.doOutput=true
            conn.connectTimeout=12000;conn.readTimeout=20000
            conn.setRequestProperty("Authorization","Bearer ${auth.accessToken()}")
            conn.setRequestProperty("Content-Type","application/x-www-form-urlencoded")
            conn.outputStream.use { it.write(("commands="+URLEncoder.encode(commands.toString(),"UTF-8")).toByteArray(Charsets.UTF_8)) }
            if(conn.responseCode !in 200..299) throw IllegalStateException("Todoist 수정 HTTP ${conn.responseCode}")
            val reply=JSONObject(conn.inputStream.bufferedReader().use { it.readText() })
            if(reply.optJSONObject("sync_status")?.optString(uuid)!="ok")
                throw IllegalStateException("Todoist 가챠 수정 실패")
        } finally { conn.disconnect() }
    }

    /**
     * PC의 Python item_close 명령과 같은 UUIDv5를 사용한다.
     * Android/PC가 같은 Todoist 반복 작업을 동시에 완료하지 않게 만들기 위한 핵심.
     */
    fun completeForCycle(id: String, occurrence: String) {
        require(id.matches(Regex("[A-Za-z0-9]+")))
        val uid = SharedCommandIds.uuid5("item_close", "$id:$occurrence")
        val command = JSONArray().put(JSONObject()
            .put("type","item_close").put("uuid",uid)
            .put("args",JSONObject().put("id",id)))
        val endpoint = "https://api.todoist.com/api/v1/sync"
        val url = URL(endpoint)
        val conn = url.openConnection() as HttpURLConnection
        try {
            conn.requestMethod = "POST"
            conn.connectTimeout = 12000
            conn.readTimeout = 20000
            conn.doOutput = true
            conn.setRequestProperty("Authorization", "Bearer ${auth.accessToken()}")
            conn.setRequestProperty("Content-Type","application/x-www-form-urlencoded")
            val payload = "commands=" + URLEncoder.encode(command.toString(), "UTF-8")
            conn.outputStream.use { it.write(payload.toByteArray(Charsets.UTF_8)) }
            if (conn.responseCode !in 200..299)
                throw IllegalStateException("Todoist 완료 HTTP ${conn.responseCode}")
            val reply = JSONObject(conn.inputStream.bufferedReader().use { it.readText() })
            if (reply.optJSONObject("sync_status")?.optString(uid) != "ok")
                throw IllegalStateException("Todoist Sync 완료 응답을 확인하지 못했습니다")
        } finally { conn.disconnect() }
    }

    /** 게임 플로팅에서 사용자가 직접 완료할 때만 호출. */
    fun complete(id: String) {
        require(id.matches(Regex("[A-Za-z0-9]+"))) { "잘못된 작업 ID" }
        HttpApi.request("https://api.todoist.com/api/v1/tasks/$id/close", "POST",
            token = auth.accessToken())
    }
}
