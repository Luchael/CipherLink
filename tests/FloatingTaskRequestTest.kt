import com.gametodo.nativeapp.*

fun main() {
    val draft=FloatingTaskDraft("  직접 추가한 할 일  ","2026-11-02","매주 월요일","project","weekly","게임")
    val command=FloatingTaskRequest.command(draft)
    val retry=FloatingTaskRequest.command(draft.copy())
    check(command.getString("uuid")==retry.getString("uuid"))
    check(command.getString("temp_id")==retry.getString("temp_id"))
    val args=command.getJSONObject("args")
    check(args.getString("content")=="직접 추가한 할 일")
    check(args.getString("project_id")=="project" && args.getString("section_id")=="weekly")
    check(args.getJSONArray("labels").getString(0)=="게임")
    val due=args.getJSONObject("due")
    check(due.getString("date")=="2026-11-02" && due.getString("string")=="매주 월요일")
    check(due.getBoolean("is_recurring") && due.getString("lang")=="ko")
    check(!FloatingTaskRequest.command(draft.copy(repeat="")).getJSONObject("args").getJSONObject("due").has("string"))
    check(FloatingTaskRequest.command(FloatingTaskDraft("같은 이름","2026-11-02","","p","s","게임"))
        .getString("uuid")!=command.getString("uuid"))
    // Same cross-device endgame completion UUID as Python's Todoist.command.
    check(SharedCommandIds.uuid5("item_close","synthetic:rotation:until:1793371200")=="219fed90-4ff6-5074-8a83-867b96ada8ad")
    println("할 일 날짜·반복·섹션·게임 라벨·재시도 UUID 및 PC/Android 완료 UUID 검사 통과")
}
