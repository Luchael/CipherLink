package com.gametodo.nativeapp

import java.io.Closeable
import java.util.concurrent.Executors

/** Independent UI requests must not discard each other; repeated taps share one request. */
class UiJobRunner(private val changed: () -> Unit) : Closeable {
    private val executor = Executors.newFixedThreadPool(3)
    private val active = linkedMapOf<String, String>()
    private var closed = false
    fun snapshot(): Map<String,String> = synchronized(this) { active.toMap() }
    fun update(key: String, message: String) {
        synchronized(this) { if (key !in active) return; active[key] = message }
        changed()
    }
    fun submit(key: String, message: String, finished: (String) -> Unit,
               failed: (Exception) -> Unit, job: () -> String): Boolean {
        synchronized(this) {
            if (closed || key in active) return false
            active[key] = message
            executor.execute {
                var result: String? = null
                var error: Exception? = null
                try { result = job() } catch(e: Exception) { error = e }
                finally {
                    synchronized(this) { active.remove(key) }
                    if (error == null) finished(result.orEmpty()) else failed(error!!)
                    changed()
                }
            }
        }
        changed()
        return true
    }
    override fun close() {
        synchronized(this) { closed = true; active.clear() }
        executor.shutdownNow()
    }
}
