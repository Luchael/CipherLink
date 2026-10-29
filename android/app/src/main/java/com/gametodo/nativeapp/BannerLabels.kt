package com.gametodo.nativeapp

/** Keep user labels while making generated gacha tasks filterable. */
object BannerLabels {
    const val GACHA = "가챠"
    fun merge(gameLabel: String, existing: List<String> = emptyList()): List<String> =
        (existing + gameLabel + GACHA).filter {it.isNotBlank()}.distinct().sorted()
}
