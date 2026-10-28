package com.gametodo.nativeapp

/**
 * 사이퍼링크 플로팅 목록의 순수 판정 규칙.
 *
 * - Todoist API의 미완료 목록에 있는 일감만 후보로 삼는다. (이미 완료된 작업은 API 파서가 제거)
 * - 한국 시간으로 예정일이 미래이거나 일정이 없는 항목은 숨긴다.
 * - 매일/매주 반복 작업은 서버 초기화 시각 + 캐시 유예(20분) 전에는 숨긴다.
 * - 가챠/이벤트 섹션에 들어 있는 작업은 제목에 상관없이 숨긴다.
 * 이 정책은 게임 종류별 자동 '완료'를 호출하지 않는다. 플로팅에 보여줄지에만 관여한다.
 */
object OverlayTaskPolicy {
    fun isEventSectionName(raw: String): Boolean {
        val normalized = raw.replace(Regex("\\s+"), "").lowercase()
        // 구 버전 '이벤트 / 기간 한정', 사용자가 지정한 '한정/이벤트' 등 이름을 모두 인식한다.
        return normalized == "이벤트" || normalized == "가챠" || normalized == "한정/이벤트" ||
            normalized == "이벤트/한정" || normalized == "이벤트/기간한정" ||
            normalized == "기간한정/이벤트" ||
            (normalized.contains("이벤트") && normalized.contains("한정")) ||
            (normalized.contains("가챠") && normalized.contains("이벤트"))
    }

    /** PC/Android 자동 완료와 같은 한국 날짜 판정 함수를 재사용한다. */
    fun eligibleDate(dueDate: String?, nowMillis: Long): Boolean =
        GamePeriods.dueEligible(dueDate, nowMillis)

    @Suppress("UNUSED_PARAMETER")
    fun canDisplay(title: String, dueDate: String?, sectionId: String, excludedSectionIds: Set<String>,
                   gameKey: String, nowMillis: Long, dueString: String? = null,
                   isRecurring: Boolean = false,
                   sectionKind: RecurrenceWindow.Kind = RecurrenceWindow.Kind.OTHER): Boolean {
        if (sectionId in excludedSectionIds) return false
        // 미완료 상태의 오래된 회차는 계속 표시한다. 반복 주기의 끝이 지났다고 숨기지 않는다.
        if (!RecurrenceWindow.isVisibleOutstanding(dueDate, nowMillis))
            return false
        val start = RecurrenceWindow.dateKst(dueDate) ?: return false
        // 해당 작업의 예정일(회차 시작일)이 오늘이면 초기화 시각 전에는 숨긴다.
        // 과거 예정일이면 지금이 새 회차의 초기화 전이어도 기존 미완료 작업을 표시한다.
        // 플로팅은 '수동 체크'이므로 자동 감지용 20분 캐시 유예를 적용하지 않는다.
        if (!GamePeriods.startedForDate(gameKey, start, nowMillis, graceMinutes = 0)) return false
        return true
    }
}
