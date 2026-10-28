package com.gametodo.nativeapp
import org.json.JSONObject
fun readNumber(root:JSONObject,vararg paths:String):Int? {
    for(path in paths) {
        var value:Any?=root
        for(part in path.split('.')) value=(value as? JSONObject)?.opt(part)
        if(value is Int) return value
    }
    return null
}
fun readString(root:JSONObject,path:String):String? {
    var value:Any?=root
    for(part in path.split('.')) value=(value as? JSONObject)?.opt(part)
    return value?.toString()
}
fun main() {
    fun obj(vararg p:Pair<String,Any?>)=JSONObject(mapOf(*p))
    val hsr=ProgressMemo.lines("hsr",obj("current_rogue_score" to 18000,"max_rogue_score" to 18000,
        "remaining_weekly_discounts" to 0,"max_weekly_discounts" to 3,
        "current_train_score" to 500,"current_stamina" to 100,"max_stamina" to 300,
        "accepted_expedition_num" to 4,"total_expedition_num" to 4))
    check(hsr.count {it.startsWith("개척력 ")}==1)
    check(hsr.count {it.startsWith("탐사 파견 ")}==1)
    check(hsr.none {it.contains("통합") || it.contains("역전") || it.contains("일일 훈련")})
    val zzz=ProgressMemo.lines("zzz",obj("vitality" to obj("current" to 400,"max" to 400),
        "weekly_task" to obj("cur_point" to 800,"max_point" to 2100),
        "vhs_sale" to obj("sale_state" to "SaleStateDone")))
    check(zzz.size==1 && zzz.single()=="비디오 가게 완료")
    check(ProgressMemo.lines("hsr",obj()).isEmpty())
    println("Progress memo: overlapping training, weekly, rogue and boss text removed; resources retained once")
}
