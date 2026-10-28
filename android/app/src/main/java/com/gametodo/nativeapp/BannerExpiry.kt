package com.gametodo.nativeapp

import java.time.LocalDateTime
import java.time.ZoneId

/**
 * PC가 만들었던 가챠 작업을 휴대폰에서도 종료시킬 때 사용하는 공통 규칙.
 * 다른 작업이나 수동 가챠 작업은 절대 자동 완료하지 않는다.
 */
object BannerExpiry {
    private val marker = Regex("(?m)^GameTodo-Banner-ID: ([a-f0-9]{32})\\s*$")
    private val end = Regex("(?m)^가챠 종료\\(KST\\): (\\d{4}-\\d{2}-\\d{2} \\d{2}:\\d{2})\\s*$")

    /** PC와 동일한 배너 종료 회차 문자열 생성(초 및 한국시간 오프셋 포함). */
    fun occurrence(task: TodoTask): String? {
        val id = marker.find(task.description)?.groupValues?.getOrNull(1) ?: return null
        val whenText = end.find(task.description)?.groupValues?.getOrNull(1) ?: return null
        return try {
            val endTime = LocalDateTime.parse(whenText.replace(' ', 'T'))
                .atZone(ZoneId.of("Asia/Seoul"))
                .format(java.time.format.DateTimeFormatter.ofPattern("yyyy-MM-dd'T'HH:mm:ssXXX"))
            "banner:$id:$endTime"
        } catch (_: Exception) { null }
    }
    fun expired(task: TodoTask, nowEpochMillis: Long): Boolean {
        if (!marker.containsMatchIn(task.description)) return false
        val whenText = end.find(task.description)?.groupValues?.getOrNull(1) ?: return false
        return try {
            val endAt = LocalDateTime.parse(whenText.replace(' ', 'T'))
                .atZone(ZoneId.of("Asia/Seoul")).toInstant().toEpochMilli()
            // 표시된 종료 분이 끝난 뒤에만 완료 처리한다.
            nowEpochMillis >= endAt + 60000L
        } catch (_: Exception) { false }
    }
}
