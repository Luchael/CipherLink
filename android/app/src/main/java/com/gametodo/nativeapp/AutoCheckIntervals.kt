package com.gametodo.nativeapp

/** WorkManager의 최소 주기 15분. 사용자 설정과 게임 시작 조회 제한에 공통 사용한다. */
object AutoCheckIntervals {
    val minutes = listOf(15, 30, 60, 120, 180, 360, 720, 1440)
    fun normalize(value: Int): Int = value.takeIf { it in minutes } ?: 15
    fun display(value: Int): String = when (normalize(value)) {
        60 -> "1시간"
        120 -> "2시간"
        180 -> "3시간"
        360 -> "6시간"
        720 -> "12시간"
        1440 -> "24시간"
        else -> "${normalize(value)}분"
    }
}
