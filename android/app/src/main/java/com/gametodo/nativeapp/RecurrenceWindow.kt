package com.gametodo.nativeapp

import java.time.Instant
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId

/**
 * Todoist 자동 완료용 반복 일정 판정기 + 플로팅의 이전 회차 표시 판정기.
 *
 * Todoist `due.date`는 최초 등록일이 아니라 *현재 반복 회차*의 예정일이다.
 * `due.string`과 `due.is_recurring`으로 회차 길이를 확인하고 다음 회차의 시작 전까지만 보여준다.
 * 자동 완료에서는 오래된 회차를 숨기되 플로팅은 미완료 회차를 계속 표시한다.
 *
 * `every!`는 완료 시점을 기준으로 반복하는 Todoist 규칙이다. 이 경우에도 due.date는
 * 현재 회차의 확정된 시작일이므로 그 날짜를 기준으로 표시 범위만 계산한다.
 * 인식할 수 없는 복잡한 반복 규칙은 유추하지 않고 숨긴다.
 */
object RecurrenceWindow {
    enum class Kind { DAILY, WEEKLY, MONTHLY, INTERVAL, OTHER }
    private val kst = ZoneId.of("Asia/Seoul")

    fun sectionKind(raw: String): Kind {
        val name = raw.trim().replace(Regex("\\s+"), "").lowercase()
        return when {
            name == "매일" || name == "일일" || name == "daily" -> Kind.DAILY
            name == "매주" || name == "주간" || name == "weekly" -> Kind.WEEKLY
            name == "매달" || name == "매월" || name == "월간" || name == "monthly" -> Kind.MONTHLY
            name == "n일" || name == "n일주기" || name.contains("일주기") ||
                name.contains("일간격") || name == "interval" -> Kind.INTERVAL
            else -> Kind.OTHER
        }
    }

    // Todoist의 시간대가 정해진 시각은 한국 시간으로 변환. '떠다니는 시간'은 로컬 날짜를 사용.
    fun dateKst(raw: String?): LocalDate? {
        if (raw.isNullOrBlank()) return null
        return try {
            when {
                raw.endsWith("Z") || Regex("[+-]\\d{2}:\\d{2}$").containsMatchIn(raw) ->
                    OffsetDateTime.parse(raw).atZoneSameInstant(kst).toLocalDate()
                else -> LocalDate.parse(raw.take(10))
            }
        } catch (_: Exception) { null }
    }

    private enum class Unit { DAY, WEEK, MONTH }
    private data class Interval(val count: Int, val unit: Unit) {
        fun end(start: LocalDate): LocalDate = when(unit) {
            Unit.DAY -> start.plusDays(count.toLong())
            Unit.WEEK -> start.plusWeeks(count.toLong())
            Unit.MONTH -> start.plusMonths(count.toLong())
        }
    }

    /** Todaist는 한글/영문 문자열을 모두 반환할 수 있다. 모르는 규칙은 null을 반환한다. */
    private fun parseRule(raw: String): Interval? {
        val rule = raw.trim().lowercase()
            .replace(Regex("\\s+"), " ")
            .removePrefix("every! ")
            .removePrefix("every ")
        // '매월 16일'의 16은 간격이 아니라 월의 날짜다. 숫자 간격으로 잘못 읽지 않는다.
        if (rule.startsWith("매월") || rule.startsWith("매달")) return Interval(1, Unit.MONTH)
        // 숫자가 있는 규칙은 먼저 처리한다. 매 N일, N일마다, every N days 등.
        val number = Regex("(?:^|\\s)(\\d{1,3})\\s*(days?|weeks?|months?|일|주|개월)(?=$|\\s|마다|간격|째|일)")
            .find(rule)
            ?: Regex("^매\\s*(\\d{1,3})\\s*(일|주|개월)").find(rule)
        if (number != null) {
            val count = number.groupValues[1].toIntOrNull() ?: return null
            if (count !in 1..366) return null
            val unit = when(number.groupValues[2]) {
                "day", "days", "일" -> Unit.DAY
                "week", "weeks", "주" -> Unit.WEEK
                "month", "months", "개월" -> Unit.MONTH
                else -> return null
            }
            return Interval(count, unit)
        }
        // '매월 16일' 등의 일 숫자는 간격 숫자가 아니다. 아래에서 MONTH로 처리한다.
        return when {
            rule.startsWith("매일") || rule == "daily" || rule == "day" ||
                rule == "every day" -> Interval(1, Unit.DAY)
            rule.startsWith("격주") || rule.startsWith("every other week") -> Interval(2, Unit.WEEK)
            rule.startsWith("매주") || rule == "weekly" || rule == "week" ||
                rule.matches(Regex("(mon|tue|wed|thu|fri|sat|sun)(day)?(s)?")) -> Interval(1, Unit.WEEK)
            rule.startsWith("매달") || rule.startsWith("매월") ||
                rule == "monthly" || rule == "month" -> Interval(1, Unit.MONTH)
            // Todoist 영문: 'every monday', 'every 1st', 'every month on 16' 등.
            rule.startsWith("mon") || rule.startsWith("tue") || rule.startsWith("wed") ||
                rule.startsWith("thu") || rule.startsWith("fri") || rule.startsWith("sat") ||
                rule.startsWith("sun") -> Interval(1, Unit.WEEK)
            rule.startsWith("month") || rule.matches(Regex("(\\d{1,2}(st|nd|rd|th)?)")) ->
                Interval(1, Unit.MONTH)
            else -> null
        }
    }

    /**
     * @return 표시 여부. sectionKind는 Todoist의 실제 섹션 명칭에서 얻어야 한다.
     * dueDate: 현재 할 일의 반복 예정일. dueString: Todoist due.string.
     */
    fun isCurrentOccurrence(dueDate: String?, dueString: String?, isRecurring: Boolean,
                            sectionKind: Kind, nowMillis: Long): Boolean {
        val start = dateKst(dueDate) ?: return false
        val today = Instant.ofEpochMilli(nowMillis).atZone(kst).toLocalDate()
        if (start.isAfter(today)) return false

        // 주간/월간/N일 섹션은 반복 설정이 누락된 작업을 잘못 체크하지 않도록 제외한다.
        if (sectionKind in setOf(Kind.DAILY, Kind.WEEKLY, Kind.MONTHLY, Kind.INTERVAL) && !isRecurring)
            return false
        if (!isRecurring) return true // 나선·혼돈 등 단발성 회차 작업은 날짜만 판단.

        val parsed = dueString?.let(::parseRule)
        val interval = parsed ?: when (sectionKind) {
            Kind.DAILY -> Interval(1, Unit.DAY)
            Kind.WEEKLY -> Interval(1, Unit.WEEK)
            Kind.MONTHLY -> Interval(1, Unit.MONTH)
            // N일 주기의 숫자를 모르는 상태로는 임의의 회차를 계산하면 안 된다.
            Kind.INTERVAL, Kind.OTHER -> return false
        }
        // 실제 반복문구와 섹션 분류가 불일치하면 섹션 이름이 아닌 Todoist 반복문구를 우선한다.
        return today.isBefore(interval.end(start))
    }

    /**
     * 플로팅 전용: 이전 반복 회차가 미완료라면 주기가 끝났어도 계속 보여준다.
     * 자동 완료 엔진의 isCurrentOccurrence()와 반드시 구분한다.
     * 초기화 전 여부는 OverlayTaskPolicy.startedForDate()에서 별도로 판단한다.
     */
    fun isVisibleOutstanding(dueDate: String?, nowMillis: Long): Boolean {
        val due = dateKst(dueDate) ?: return false
        val today = Instant.ofEpochMilli(nowMillis).atZone(kst).toLocalDate()
        return !due.isAfter(today)
    }
}
