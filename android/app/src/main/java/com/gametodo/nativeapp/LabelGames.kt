package com.gametodo.nativeapp

import java.security.MessageDigest

/** User-chosen Todoist label. It grants manual task display only, never automatic scoring. */
object LabelGames {
    fun key(label: String): String = "label_" + MessageDigest.getInstance("SHA-256")
        .digest(label.toByteArray(Charsets.UTF_8)).joinToString("") { "%02x".format(it.toInt() and 255) }
    fun candidates(labels: List<String>, registered: Set<String>): List<String> = labels
        .filter { it.isNotBlank() && it !in registered }.distinct().sorted()
    fun matches(label: String, taskLabels: List<String>): Boolean = label in taskLabels
    fun filterApps(apps: List<Pair<String,String>>, query: String): List<Pair<String,String>> {
        val term = query.trim()
        return apps.filter { term.isEmpty() || it.first.contains(term,true) || it.second.contains(term,true) }
    }
}
