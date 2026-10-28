package com.gametodo.nativeapp

import android.content.Context

object InteractionSettings {
    const val SHOW = "show_game_tasks"
    const val CHECK = "check_on_game_open"
    fun read(context: Context): DisplayOptions {
        val p = context.getSharedPreferences("gametodo", Context.MODE_PRIVATE)
        return DisplayOptions(p.getBoolean(SHOW,true), p.getBoolean(CHECK,true))
    }
    fun set(context: Context, key: String, enabled: Boolean) {
        require(key == SHOW || key == CHECK)
        context.getSharedPreferences("gametodo", Context.MODE_PRIVATE).edit().putBoolean(key,enabled).apply()
    }
}
