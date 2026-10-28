package com.gametodo.nativeapp

import android.content.Context
import org.json.JSONObject
import java.time.Instant

/**
 * Todoist 설명에는 출처만 넣고, 종료시각/자동생성 여부는 이 기기의 로컬 기록으로 관리한다.
 * PC도 동일한 가챠 key / 시작일 / 종료시각을 사용한다. 토큰은 이곳에 저장하지 않는다.
 * 앱 데이터를 삭제하면 로컬 기록도 사라지므로, 이 경우 자동 완료 연결을 재구성해야 한다.
 */
class BannerLedger(context: Context) {
    private val prefs = context.getSharedPreferences("banner_ledger_v1", Context.MODE_PRIVATE)
    fun remember(banner: BannerRecord, taskId: String) {
        val old = prefs.getString(banner.key, null)?.let { runCatching { JSONObject(it) }.getOrNull() }
        val record = JSONObject()
            .put("id", taskId).put("title", banner.title)
            .put("start", banner.startDate).put("end", banner.endMillis)
            .put("source", banner.sourceUrl).put("closed", old?.optBoolean("closed") ?: false)
        prefs.edit().putString(banner.key, record.toString()).apply()
    }
    fun closeExpired(api: TodoistApi, tasks: List<TodoTask>, nowMs: Long) {
        for ((key, value) in prefs.all) {
            if (!key.matches(Regex("[0-9a-f]{32}"))) continue
            val saved = (value as? String)?.let { runCatching { JSONObject(it) }.getOrNull() } ?: continue
            if (saved.optBoolean("closed")) continue
            val end = saved.optLong("end",0L)
            // 시간은 KST 기반 소스의 UTC epoch. 분 단위 정밀도 보호를 위해 1분 늦게 닫는다.
            if (end <= 0 || nowMs < end + 60_000L) continue
            val id = saved.optString("id")
            val title = saved.optString("title")
            val start = saved.optString("start")
            val sourceUrl = saved.optString("source")
            val task = tasks.singleOrNull { it.id == id } ?: continue
            // PC나 사람이 Todoist 내용을 수정했다면 오작동을 막기 위해 자동 완료 보류.
            if (task.title != title || task.dueDate?.take(10) != start || source(task.description) != sourceUrl) continue
            val occurrence = "banner:$key:${Instant.ofEpochMilli(end)}"
            api.completeForCycle(id,occurrence)
            prefs.edit().putString(key,saved.put("closed",true).toString()).apply()
        }
    }
    companion object {
        private val legacy = Regex("(?m)^GameTodo-Banner-ID: ([a-f0-9]{32})\\s*$")
        fun legacyKey(description: String): String? = legacy.find(description)?.groupValues?.get(1)
        fun source(description: String): String? = Regex("(?m)^출처: (https://\\S+)\\s*$")
            .find(description)?.groupValues?.get(1)
    }
}
