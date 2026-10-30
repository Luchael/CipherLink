package org.json
class JSONObject(private val map: Map<String,Any?> = emptyMap()) {
    fun isNull(s: String): Boolean = map[s] == null
    fun optJSONObject(s: String): JSONObject? = map[s] as? JSONObject
    fun optString(s: String): String = map[s]?.toString() ?: ""
    fun optJSONArray(s: String): JSONArray? = map[s] as? JSONArray
    fun opt(s: String): Any? = map[s]
    fun keys(): MutableIterator<String> = map.keys.toMutableSet().iterator()
}
class JSONArray(private val list: List<Any?> = emptyList()) {
    fun length(): Int = list.size
    fun optJSONObject(index: Int): JSONObject? = list.getOrNull(index) as? JSONObject
    fun opt(index: Int): Any? = list.getOrNull(index)
}
