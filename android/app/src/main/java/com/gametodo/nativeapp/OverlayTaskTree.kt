package com.gametodo.nativeapp

/** Manual floating-list ancestry only. Automatic API completion never uses this policy. */
object OverlayTaskTree {
    private const val MAX_ANCESTORS = 64

    /**
     * A child may inherit game membership and an absent due date from its nearest
     * parent. Every ancestor must be known, acyclic, in the same project, and
     * outside event sections. An explicit child date is never overwritten.
     *
     * Returns a presentation copy; callers must not persist its inherited fields.
     */
    fun displayTask(task: TodoTask, tasksById: Map<String, TodoTask>, gameKey: String,
                    nowMillis: Long, excludedSectionIds: Set<String>,
                    sectionKinds: Map<String, RecurrenceWindow.Kind>,
                    gameKeys: (TodoTask) -> Set<String>): TodoTask? {
        val chain = mutableListOf<TodoTask>()
        val visited = mutableSetOf<String>()
        var cursor: TodoTask? = task
        while (cursor != null) {
            if (chain.size >= MAX_ANCESTORS || !visited.add(cursor.id)) return null
            if (cursor.projectId != task.projectId) return null
            if (cursor.sectionId in excludedSectionIds) return null
            chain += cursor
            val parent = cursor.parentId?.takeUnless { it.isBlank() || it == "null" }
            // Equal missing project IDs do not prove that ancestry is in one project.
            if (parent != null && task.projectId.isBlank()) return null
            cursor = if (parent == null) null else tasksById[parent] ?: return null
        }
        val membership = chain.asSequence().map(gameKeys).firstOrNull { it.isNotEmpty() }
            ?: return null
        // Conflicting explicit game labels are not resolved by arbitrary order.
        if (membership != setOf(gameKey)) return null
        val dueSource = chain.firstOrNull { !it.dueDate.isNullOrBlank() } ?: return null
        val section = chain.firstOrNull { it.sectionId.isNotBlank() }?.sectionId ?: ""
        val displayed = task.copy(dueDate = dueSource.dueDate,
            dueString = dueSource.dueString, isRecurring = dueSource.isRecurring,
            sectionId = section)
        return displayed.takeIf {
            OverlayTaskPolicy.canDisplay(it.title, it.dueDate, it.sectionId,
                excludedSectionIds, gameKey, nowMillis, it.dueString, it.isRecurring,
                sectionKinds[section] ?: RecurrenceWindow.Kind.OTHER)
        }
    }

    /** Do not close a new recurrence or a renamed/moved task from an old visible row. */
    fun sameDisplayedOccurrence(shown: TodoTask, current: TodoTask): Boolean =
        shown.id == current.id && shown.title == current.title &&
            shown.parentId == current.parentId && shown.projectId == current.projectId &&
            shown.sectionId == current.sectionId && shown.dueDate == current.dueDate &&
            shown.dueString == current.dueString && shown.isRecurring == current.isRecurring
}
