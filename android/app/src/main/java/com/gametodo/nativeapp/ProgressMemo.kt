package com.gametodo.nativeapp

import org.json.JSONObject

/** Auxiliary notes only: each API metric has one visual representation. */
object ProgressMemo {
    fun lines(game: String, note: JSONObject): List<String> {
        val resources = mutableListOf<String>()
        fun gauge(name: String, current: String, maximum: String) {
            val cur = readNumber(note,current); val max = readNumber(note,maximum)
            if(cur != null && max != null && cur >= 0 && max > 0) resources += "$name $cur/$max"
        }
        when(game) {
            "genshin" -> gauge("레진","current_resin","max_resin")
            "hsr" -> {
                gauge("개척력","current_stamina","max_stamina")
                readNumber(note,"current_reserve_stamina")?.let { resources += "예비 개척력 $it" }
            }
            "zzz" -> gauge("배터리","energy.progress.current","energy.progress.max")
        }
        val covered = when(game) {
            "hsr" -> setOf("시뮬레이션 우주·화폐 전쟁 통합 주간 포인트", "역전의 여운 주간 할인 잔여")
            "zzz" -> setOf("메모 일일 활약도", "주간 일정")
            else -> emptySet()
        }
        return (resources + RealTimeMemo.detailLines(game,note).filterNot { line ->
            covered.any { line.startsWith("$it ") }
        }).distinct()
    }
}
