package com.gametodo.nativeapp

import java.time.Instant
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.DayOfWeek
import java.time.temporal.TemporalAdjusters
import java.nio.ByteBuffer
import java.util.UUID
import java.security.MessageDigest

object SharedCommandIds {
    private val urlNamespace = UUID.fromString("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
    fun uuid5(action: String, target: String): String {
        val name = "https://gametodo.local/v1/$action/$target".toByteArray(Charsets.UTF_8)
        val ns = ByteBuffer.allocate(16).putLong(urlNamespace.mostSignificantBits).putLong(urlNamespace.leastSignificantBits).array()
        val bytes = MessageDigest.getInstance("SHA-1").digest(ns + name).copyOfRange(0,16)
        bytes[6] = ((bytes[6].toInt() and 0x0f) or 0x50).toByte()
        bytes[8] = ((bytes[8].toInt() and 0x3f) or 0x80).toByte()
        val bb = ByteBuffer.wrap(bytes)
        return UUID(bb.long, bb.long).toString()
    }
}

object GamePeriods {
    private val kst = ZoneId.of("Asia/Seoul")
    fun nowKst(nowMillis: Long): ZonedDateTime = Instant.ofEpochMilli(nowMillis).atZone(kst)

    /**
     * 오전 00:00~게임 초기화 전 사이에는 전날 점수를 당일 Todoist에 잘못 적용할 위험이 크다.
     * 사용자 요청에 따라 초기화 전에는 이전 회차도 자동 완료하지 않는다.
     * 서버 초기화 후 20분은 캐시 반영 지연을 피하기 위한 유예 시간이다.
     */
    fun currentCycle(game: String, kind: String, nowMillis: Long, graceMinutes: Long = 20): String? {
        val resetHour = when (game) {
            "genshin", "hsr", "zzz", "endfield" -> 5
            "limbus" -> 6
            // 검증되지 않은 게임의 초기화 시각은 절대 추정하지 않는다.
            else -> return null
        }
        val now = nowKst(nowMillis)
        val todayReset = now.toLocalDate().atTime(LocalTime.of(resetHour, 0)).atZone(kst)
        return when (kind) {
            "daily" -> if (now.isBefore(todayReset.plusMinutes(graceMinutes))) null
                else todayReset.toLocalDate().toString()
            "weekly" -> {
                val weekDay = if (game == "limbus") DayOfWeek.THURSDAY else DayOfWeek.MONDAY
                val startDay = now.toLocalDate().with(TemporalAdjusters.previousOrSame(weekDay))
                // 주간 초기화일의 초기화 전에는 기존 주간 정보를 사용하지 않는다.
                val cycleStart = startDay.atTime(resetHour, 0).atZone(kst)
                if (now.isBefore(cycleStart.plusMinutes(graceMinutes))) null else "weekly:${startDay}"
            }
            else -> null
        }
    }
    /** 시작일에만 게임 일일 초기화 시각을 확인. 중간 날짜는 이미 회차가 열려 있다. */
    fun startedForDate(game: String, start: LocalDate, nowMillis: Long,
                       graceMinutes: Long = 20): Boolean {
        val now = nowKst(nowMillis)
        if (start.isAfter(now.toLocalDate())) return false
        if (start.isBefore(now.toLocalDate())) return true
        val reset = when (game) {
            "genshin", "hsr", "zzz", "endfield" -> 5
            "limbus" -> 6
            // 확인되지 않은 게임은 초기화 시각을 추측해서 숨기지 않는다.
            else -> return true
        }
        return !now.isBefore(start.atTime(reset, 0).atZone(kst).plusMinutes(graceMinutes))
    }

    fun dueEligible(due: String?, nowMillis: Long): Boolean {
        if (due.isNullOrBlank()) return false
        return try {
            val date = if (due.contains('T')) {
                // 시각/오프셋이 있는 일정은 반드시 KST로 변환. 시간대 없는 시각은 보류.
                java.time.OffsetDateTime.parse(due.replace("Z", "+00:00"))
                    .atZoneSameInstant(kst).toLocalDate()
            } else LocalDate.parse(due.take(10))
            !date.isAfter(nowKst(nowMillis).toLocalDate())
        } catch (_: Exception) { false }
    }
}

