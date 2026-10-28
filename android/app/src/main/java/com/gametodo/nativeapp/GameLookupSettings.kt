package com.gametodo.nativeapp

import android.content.Context

/** 점수 API 자동 조회만 제어한다. Todoist 수동 체크와 플로팅은 계속 동작한다. */
object GameLookupSettings {
    const val PREFS = "cipherlink_lookup_per_game_v1"
    val names = linkedMapOf(
        "genshin" to "원신", "hsr" to "붕괴: 스타레일", "zzz" to "젠레스 존 제로",
        "endfield" to "명일방주: 엔드필드", "wuthering" to "명조 (글로벌)",
        "arknights" to "명일방주 (한국)"
    )
    val implemented = setOf("genshin", "hsr", "zzz", "endfield")
    fun enabled(context: Context, game: String): Boolean =
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .getBoolean("lookup_$game", game in implemented)
    fun setEnabled(context: Context, game: String, value: Boolean) {
        require(game in names)
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putBoolean("lookup_$game", value).apply()
    }
}
