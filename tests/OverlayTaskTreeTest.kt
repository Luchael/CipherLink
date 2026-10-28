import com.gametodo.nativeapp.OverlayTaskTree
import com.gametodo.nativeapp.TodoTask
import com.gametodo.nativeapp.RecurrenceWindow
import java.time.LocalDate
import java.time.ZoneId

private fun task(id: String, title: String, due: String? = null,
                 parent: String? = null, section: String = "weekly",
                 project: String = "project") =
    TodoTask(id, title, emptyList(), "", due, section, project, parentId = parent)

fun main() {
    val now = LocalDate.parse("2026-10-28").atTime(12, 0)
        .atZone(ZoneId.of("Asia/Seoul")).toInstant().toEpochMilli()
    val gameKeys: (TodoTask) -> Set<String> = { item ->
        when {
            item.title.startsWith("[젠존제]") -> setOf("zzz")
            item.title.startsWith("[원신]") -> setOf("genshin")
            item.title.startsWith("[색지뢰]") -> setOf("colorsweeper")
            else -> emptySet()
        }
    }
    fun display(item: TodoTask, all: List<TodoTask>, game: String = "zzz") =
        OverlayTaskTree.displayTask(item, all.associateBy { it.id }, game, now,
            setOf("event"), mapOf("weekly" to RecurrenceWindow.Kind.WEEKLY), gameKeys)

    val parent = task("parent", "[젠존제] 주간퀘", "2026-10-26")
    val child = task("child", "주간퀘스트(폴리크롬 최대치)", parent = "parent")
    val visible = display(child, listOf(parent, child)) ?: error("Unprefixed subtask must inherit game/due")
    check(visible.id == "child" && visible.title == child.title)
    check(visible.dueDate == parent.dueDate)

    val nested = child.copy(id = "nested", parentId = "child")
    check(display(nested, listOf(parent, child, nested)) != null)
    check(display(child, listOf(parent, child), "genshin") == null)
    check(display(child, listOf(child)) == null) // unknown/missing parent fails closed
    check(display(child, listOf(parent.copy(projectId = "other"), child)) == null)
    val unknownProjectChild = child.copy(projectId = "")
    check(display(unknownProjectChild, listOf(parent.copy(projectId = ""), unknownProjectChild)) == null)
    check(display(child, listOf(parent.copy(parentId = "child"), child)) == null)
    check(display(child, listOf(parent.copy(sectionId = "event"), child)) == null)
    check(display(child.copy(sectionId = "event"), listOf(parent, child)) == null)

    // Explicit future/invalid child dates must never inherit an earlier parent date.
    check(display(child.copy(dueDate = "2026-10-29"), listOf(parent, child)) == null)
    check(display(child.copy(dueDate = "not-a-date"), listOf(parent, child)) == null)
    check(display(child.copy(dueDate = "2026-10-01"), listOf(parent, child)) != null)
    check(display(child, listOf(parent.copy(dueDate = null), child)) == null)
    val inheritedSection = child.copy(sectionId = "")
    check(display(inheritedSection, listOf(parent, inheritedSection))?.sectionId == "weekly")
    val tooDeep = mutableListOf(parent.copy(id = "depth0"))
    for (index in 1..64) tooDeep += child.copy(id = "depth$index", parentId = "depth${index - 1}")
    check(display(tooDeep.last(), tooDeep) == null)

    val otherGameChild = child.copy(title = "[원신] 수동 작업")
    check(display(otherGameChild, listOf(parent, otherGameChild)) == null)
    check(display(otherGameChild, listOf(parent, otherGameChild), "genshin") != null)
    val conflictingLabels = child.copy(title = "[젠존제] 혼합", labels = listOf("원신"))
    val mixedKeys: (TodoTask) -> Set<String> = { item ->
        if (item.id == conflictingLabels.id) setOf("genshin", "zzz") else gameKeys(item)
    }
    check(OverlayTaskTree.displayTask(conflictingLabels,
        listOf(parent, conflictingLabels).associateBy { it.id }, "zzz", now,
        emptySet(), emptyMap(), mixedKeys) == null)

    // A new parent occurrence/moved task must not be closed using an old visible row.
    val next = visible.copy(dueDate = "2026-11-02")
    check(!OverlayTaskTree.sameDisplayedOccurrence(visible, next))
    check(!OverlayTaskTree.sameDisplayedOccurrence(visible, visible.copy(parentId = "other")))
    check(!OverlayTaskTree.sameDisplayedOccurrence(visible, visible.copy(projectId = "other")))
    check(OverlayTaskTree.sameDisplayedOccurrence(visible, visible.copy()))

    // All four task sections remain eligible when overdue; no automatic completion is involved.
    for (section in listOf("daily", "weekly", "monthly", "interval")) {
        val manual = task("manual", "[젠존제] 수동 작업", "2026-09-01", section = section)
        check(display(manual, listOf(manual)) != null)
    }
    val colorsweeper = task("colorsweeper", "[색지뢰] 일퀘", "2026-10-28", section = "daily")
    check(display(colorsweeper, listOf(colorsweeper), "colorsweeper") != null)
    check(display(colorsweeper.copy(dueDate = "2026-10-29"), listOf(colorsweeper), "colorsweeper") == null)
    println("하위 작업 소속·예정일·이벤트 제외·현재 회차 재확인 테스트 통과")
}
