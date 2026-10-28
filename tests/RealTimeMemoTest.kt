package com.gametodo.nativeapp
import org.json.JSONObject

fun readNumber(root: JSONObject, vararg paths: String): Int? {
    for(path in paths) {
        var at:Any? = root
        for(part in path.split('.')) at = (at as? JSONObject)?.opt(part)
        when(at) {
            is Int -> return at
            is Long -> if(at in Int.MIN_VALUE..Int.MAX_VALUE) return at.toInt()
            is String -> at.toIntOrNull()?.let { return it }
        }
    }
    return null
}
fun readString(root: JSONObject,path:String):String? {
    var at:Any? = root
    for(part in path.split('.')) at = (at as? JSONObject)?.opt(part)
    return at?.toString()?.takeIf { it != "null" && it.isNotBlank() }
}
fun main() {
    fun obj(vararg items:Pair<String,Any?>) = JSONObject(mapOf(*items))
    val hsr = obj(
        "current_rogue_score" to 9000, "max_rogue_score" to 18000,
        "remaining_weekly_discounts" to 0, "max_weekly_discounts" to 3,
        "current_bonus_synchronicity_points" to 500,
        "max_bonus_synchronicity_points" to 1000
    )
    val hsrLines=RealTimeMemo.detailLines("hsr",hsr)
    check(hsrLines.any { it.contains("시뮬레이션") && it.contains("9000/18000") })
    check(hsrLines.any { it.contains("할인 잔여") && it.contains("0/3") })
    val zzz = obj(
        "engagement" to obj("current" to 400,"max" to 400),
        "hollow_zero" to obj("bounty_commission" to obj("cur_completed" to 4,"total" to 4),
            "investigation_point" to obj("num" to 4000,"total" to 8000)),
        "weekly_task" to obj("cur_point" to 550, "max_point" to 2100),
        "video_store_state" to "SaleStateDoing"
    )
    val zzzLines=RealTimeMemo.detailLines("zzz",zzz)
    check(zzzLines.any { it.contains("현상금 임무") && it.contains("4/4") })
    check(zzzLines.any { it.contains("조사 포인트") && it.contains("4000/8000") })
    check(zzzLines.any { it.contains("주간 일정") && it.contains("550/2100") })
    check(zzzLines.any { it.contains("비디오 가게") })
    check(RealTimeMemo.detailLines("zzz",obj()).isEmpty())
    println("RealTimeMemo 7 assertions passed")
}
