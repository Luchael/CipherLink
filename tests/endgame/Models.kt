package com.gametodo.nativeapp
import org.json.JSONObject
class AccountGauge(
    val game: String, val account: String, val metric: String, val current: Int, val maximum: Int,
    val observedAtMs: Long = System.currentTimeMillis(), val periodKey: String? = null,
    val periodStartMs: Long? = null, val periodEndMs: Long? = null, val displayDetail: String = "", val displayTitle:String="",val displayOnly:Boolean=false, val completionVerified:Boolean=true, val hasRecord:Boolean=true) {
    val filled: Boolean get() = completionVerified && maximum > 0 && current >= maximum
}
class GameRole(val game: String, val uid: String, val server: String, val nickname: String)
object GameNet { fun encode(s: String): String = s
    fun json(url: String, headers: Map<String,String>): JSONObject = error("Network disabled in test") }
object HoyoProvider { fun headers(cookie: String): Map<String,String> = emptyMap()
    fun recordHeaders(cookie: String): Map<String,String> = mapOf("DS" to "dummy", "x-rpc-lang" to "ko-kr")
    fun data(j: JSONObject): JSONObject = j }
fun readString(root: JSONObject, path: String): String? {
    var o: Any? = root
    for (name in path.split('.')) o = (o as? JSONObject)?.opt(name)
    return o?.toString()?.takeUnless { it == "null" }
}
fun readNumber(root: JSONObject, vararg paths: String): Int? = paths.firstNotNullOfOrNull { path ->
    var o: Any? = root
    for (name in path.split('.')) o = (o as? JSONObject)?.opt(name)
    when(o) { is Int -> o; is Long -> o.takeIf {it in Int.MIN_VALUE..Int.MAX_VALUE}?.toInt(); is String -> o.toIntOrNull(); else -> null }
}
