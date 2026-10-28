package com.gametodo.nativeapp

import android.content.Context
import org.json.JSONObject

/** PC와 동일한 shared/game_rules.json을 읽는 단일 게임 규칙 관리자. */
object GameRules {
    // 게임 전환마다 JSON 파일을 재파싱하지 않도록 앱 프로세스 안에서만 캐시.
    @Volatile private var cached: List<Game>? = null

    data class Game(val key: String, val name: String, val prefix: String,
                    val label: String, val resetHour: Int?, val packages: List<String>)

    fun all(context: Context): List<Game> {
        cached?.let { return it }
        synchronized(this) {
            cached?.let { return it }
            return parseAndCache(context)
        }
    }

    private fun parseAndCache(context: Context): List<Game> {
        val source = context.assets.open("game_rules.json")
            .bufferedReader(Charsets.UTF_8).use { it.readText() }
        val games = JSONObject(source).getJSONObject("games")
        val result = games.keys().asSequence().map { key ->
            val item = games.getJSONObject(key)
            val apps = item.getJSONArray("android_packages")
            Game(key, item.getString("name"), item.getString("prefix"),
                item.getString("label"),
                if (item.isNull("daily_reset_hour_kst")) null else item.getInt("daily_reset_hour_kst"),
                (0 until apps.length()).map { apps.getString(it) })
        }.toList()
        cached = result
        return result
    }

    fun forPackage(context: Context, packageName: String): Game? {
        val custom = context.getSharedPreferences("gametodo", Context.MODE_PRIVATE)
            .getString("packages", "") ?: ""
        for (line in custom.lines()) {
            val parts = line.trim().split("=", limit = 2)
            if (parts.size == 2 && parts[0].trim() == packageName)
                return all(context).firstOrNull { it.key == parts[1].trim() }
        }
        return all(context).firstOrNull { packageName in it.packages }
    }

    fun matchingTask(game: Game, title: String, labels: List<String>): Boolean =
        title.startsWith("[${game.prefix}]") || game.label in labels
}
