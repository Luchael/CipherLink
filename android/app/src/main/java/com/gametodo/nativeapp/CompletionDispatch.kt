package com.gametodo.nativeapp

/** One server-approved completion, then persistence and a best-effort popup. */
object CompletionDispatch {
    fun run(complete: () -> Unit, record: () -> Unit, notify: () -> Unit) {
        complete() // throws on HTTP/Sync failure: never announce an unapproved task
        record()
        try { notify() } catch (_: Exception) { /* Notification permission is independent. */ }
    }
}
