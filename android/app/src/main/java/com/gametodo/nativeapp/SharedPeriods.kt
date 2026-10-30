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

    /** KST minutes after midnight. Unknown games require an explicit user setting. */
    fun defaultResetMinutes(game: String): Int? = when(game) {
        "genshin", "hsr", "zzz", "wuthering", "endfield" -> 5 * 60
        "limbus" -> 6 * 60
        else -> null
    }

    fun parseResetTime(raw: String): Int? {
        if (!Regex("[0-9]{2}:[0-9]{2}").matches(raw)) return null
        val hour=raw.take(2).toInt(); val minute=raw.takeLast(2).toInt()
        return if(hour in 0..23 && minute in 0..59) hour*60+minute else null
    }

    fun currentCycle(game: String, kind: String, nowMillis: Long, graceMinutes: Long = 20,
                     resetMinutes: Int? = defaultResetMinutes(game)): String? {
        val minute=resetMinutes?.takeIf {it in 0..1439} ?: return null
        val now=nowKst(nowMillis)
        val todayReset=now.toLocalDate().atStartOfDay(kst).plusMinutes(minute.toLong())
        // All automatic paths obey today's reset, including weekly/seasonal goals.
        if(now.isBefore(todayReset.plusMinutes(graceMinutes))) return null
        return when(kind) {
            "daily" -> todayReset.toLocalDate().toString()
            "weekly" -> {
                val day=if(game=="limbus") DayOfWeek.THURSDAY else DayOfWeek.MONDAY
                val start=now.toLocalDate().with(TemporalAdjusters.previousOrSame(day))
                "weekly:$start"
            }
            else -> null
        }
    }

    /** Old outstanding tasks stay visible; today's task opens at the game's reset. */
    fun startedForDate(game: String, start: LocalDate, nowMillis: Long,
                       graceMinutes: Long = 20,
                       resetMinutes: Int? = defaultResetMinutes(game)): Boolean {
        val now=nowKst(nowMillis)
        if(start.isAfter(now.toLocalDate())) return false
        if(start.isBefore(now.toLocalDate())) return true
        val minute=resetMinutes?.takeIf {it in 0..1439} ?: return false
        return !now.isBefore(start.atStartOfDay(kst).plusMinutes(minute.toLong()+graceMinutes))
    }

    /** A still-active OLD API season cannot close a NEW Todoist recurrence. */
    fun seasonMatchesTask(game: String, due: String?, startMs: Long?, endMs: Long?,
                          nowMillis: Long, resetMinutes: Int? = defaultResetMinutes(game)): Boolean {
        val date=RecurrenceWindow.dateKst(due) ?: return false
        val minute=resetMinutes?.takeIf {it in 0..1439} ?: return false
        if(startMs==null || endMs==null || startMs>=endMs || nowMillis<startMs || nowMillis>=endMs) return false
        val opens=date.atStartOfDay(kst).plusMinutes(minute.toLong()).toInstant().toEpochMilli()
        return startMs>=opens && currentCycle(game,"daily",nowMillis,resetMinutes=minute)!=null
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

