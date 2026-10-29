package com.gametodo.nativeapp

object ProgressPresentation {
    private val titles = mapOf("daily" to "일일 목표", "weekly" to "주간 목표",
        "spiral" to "나선", "theater" to "환상극", "moc" to "혼돈의 기억",
        "pure_fiction" to "허구 이야기", "apocalyptic" to "종말의 환영",
        "arbitration" to "이상 중재", "shiyu" to "시유 방어전", "deadly" to "위험한 강습전",
        "weekly_boss_used" to "주간 보스",
        "rogue_weekly" to "시뮬레이션 우주 · 화폐 전쟁", "weekly_mission" to "주간 임무", "weekly_task" to "리두 주간 일정", "bounty_tasks" to "현상금 의뢰 횟수", "bounty_points" to "현상금 의뢰 포인트")
    fun title(metric: String) = titles[metric] ?: "추가 진행도"
    fun title(game: String, metric: String) = if(game=="genshin" && metric=="weekly") "주간 보스" else title(metric)
    fun visible(game: String, metric: String) = metric !in setOf("umbral_complete","crisis_complete","war_complete") && !(game in setOf("hsr","zzz") && metric=="weekly")
    fun known(current: Int?, maximum: Int?) = current != null && current >= 0 && maximum != null && maximum > 0
    fun value(current: Int?, maximum: Int?) = if (known(current,maximum)) "$current / $maximum" else "정보 없음"
    fun value(metric: String, current: Int?, maximum: Int?) = value(current,maximum) +
        (if(known(current,maximum)) when(metric) {"shiyu"->" S";"deadly"->"별";else->""} else "")
    fun fraction(current: Int?, maximum: Int?) = if (known(current,maximum))
        (current!!.toLong() * 1000L / maximum!!).coerceIn(0L,1000L).toInt() else 0
    fun state(current: Int?, maximum: Int?) = when {
        !known(current,maximum) -> "확인 필요"
        current!! >= maximum!! -> "목표 달성"
        current == 0 -> "진행 전"
        else -> "진행 중"
    }
}
