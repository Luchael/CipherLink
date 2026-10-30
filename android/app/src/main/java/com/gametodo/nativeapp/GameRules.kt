package com.gametodo.nativeapp

import android.content.Context
import org.json.JSONObject
import org.json.JSONArray

/** PC와 동일한 shared/game_rules.json을 읽는 단일 게임 규칙 관리자. */
object GameRules {
    // 게임 전환마다 JSON 파일을 재파싱하지 않도록 앱 프로세스 안에서만 캐시.
    @Volatile private var cached: List<Game>? = null

    data class Game(val key: String, val name: String, val prefix: String,
                    val label: String, val resetHour: Int?, val packages: List<String>, val resetMinute: Int = 0) {
        val resetMinutes: Int? get() = resetHour?.let {it*60+resetMinute}
    }

    fun all(context: Context): List<Game> {
        val prefs=context.getSharedPreferences("gametodo",Context.MODE_PRIVATE)
        return (builtIn(context)+labelGames(context)).map {game ->
            val key="reset_time:${game.key}"
            val minute=if(prefs.contains(key)) GamePeriods.parseResetTime(prefs.getString(key,"").orEmpty())
                else game.resetMinutes
            game.copy(resetHour=minute?.div(60),resetMinute=minute?.rem(60) ?: 0)
        }
    }

    fun resetMinutes(context: Context, game: String): Int? = all(context).firstOrNull {it.key==game}?.resetMinutes

    fun setResetTime(context: Context, game: String, raw: String?) {
        require((builtIn(context)+labelGames(context)).any {it.key==game})
        require(raw==null || GamePeriods.parseResetTime(raw)!=null)
        context.getSharedPreferences("gametodo",Context.MODE_PRIVATE).edit().apply {
            if(raw==null) remove("reset_time:$game") else putString("reset_time:$game",raw)
        }.apply()
    }

    private fun builtIn(context: Context): List<Game> {
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

    private fun labelGames(context: Context): List<Game> = runCatching {
        val labels=JSONArray(context.getSharedPreferences("gametodo",Context.MODE_PRIVATE).getString("game_labels","[]"))
        (0 until labels.length()).map {labels.getString(it)}.filter {it.isNotBlank()}.distinct()
            .filter {label -> builtIn(context).none {it.label==label}}
            .map {label->Game(LabelGames.key(label),label,"",label,null,emptyList())}
    }.getOrDefault(emptyList())

    fun addLabelGame(context: Context, label: String) {
        require(label.isNotBlank())
        val labels=(labelGames(context).map {it.label}+label).distinct()
        context.getSharedPreferences("gametodo",Context.MODE_PRIVATE).edit()
            .putString("game_labels",JSONArray(labels).toString()).apply()
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
        (game.prefix.isNotBlank() && title.startsWith("[${game.prefix}]")) || LabelGames.matches(game.label,labels)
}
