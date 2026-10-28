package com.gametodo.nativeapp

/** Foreground observation serves two independently chosen features. */
data class DisplayOptions(val showTasks: Boolean = true, val checkOnGameOpen: Boolean = true) {
    val shouldObserveWindows get() = showTasks || checkOnGameOpen
}
