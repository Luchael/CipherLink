package com.gametodo.nativeapp

/** Todoist task shape shared by API parsing and pure manual-overlay policy. */
data class TodoTask(val id: String, val title: String, val labels: List<String>,
                    val description: String, val dueDate: String?,
                    val sectionId: String = "", val projectId: String = "",
                    val dueString: String? = null, val isRecurring: Boolean = false,
                    val parentId: String? = null)
