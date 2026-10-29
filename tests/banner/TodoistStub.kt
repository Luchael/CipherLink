package com.gametodo.nativeapp

object HttpApi {
    fun request(url: String): String = error("Network disabled in parser test")
}

/** Parser tests must never enter Todoist or Android persistence paths. */
class TodoistApi {
    fun tasks(): List<TodoTask> = error("Todoist is disabled in the banner parser test")
    fun bannerSection(): Pair<String, String>? = error("Todoist is disabled in the banner parser test")
    fun updateBanner(id: String, banner: BannerRecord, labels: List<String> = emptyList()): Unit = error("Todoist is disabled in the banner parser test")
    fun createBanner(project: String, section: String, banner: BannerRecord): String? =
        error("Todoist is disabled in the banner parser test")
    fun completeForCycle(id: String, occurrence: String): Unit =
        error("Todoist is disabled in the banner parser test")
}
