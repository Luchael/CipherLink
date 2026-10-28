import com.gametodo.nativeapp.CompletionDispatch

fun main() {
    val events = mutableListOf<String>()
    CompletionDispatch.run({ events += "approved" }, { events += "recorded" }, { events += "popup" })
    check(events == listOf("approved", "recorded", "popup"))
    events.clear()
    try {
        CompletionDispatch.run({ error("server failure") }, { events += "recorded" }, { events += "popup" })
        error("failure must propagate")
    } catch (_: IllegalStateException) {}
    check(events.isEmpty())
    CompletionDispatch.run({ events += "approved" }, { events += "recorded" }, { error("permission denied") })
    check(events == listOf("approved", "recorded"))
    println("One-shot completion, approval ordering, failure and notification isolation passed")
}
