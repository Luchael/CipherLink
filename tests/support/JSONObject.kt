// JVM-only minimal JSONObject substitute. Not included in Android source tree.
package org.json
class JSONObject(private val values: Map<String, Any?> = emptyMap()) {
    fun opt(key: String): Any? = values[key]
}
