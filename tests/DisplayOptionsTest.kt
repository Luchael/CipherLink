import com.gametodo.nativeapp.DisplayOptions

fun main() {
    for (show in listOf(false, true)) for (detect in listOf(false, true)) {
        val options = DisplayOptions(show, detect)
        check(options.showTasks == show)
        check(options.checkOnGameOpen == detect)
        check(options.shouldObserveWindows == (show || detect))
        check(options.copy(showTasks = !show).checkOnGameOpen == detect)
        check(options.copy(checkOnGameOpen = !detect).showTasks == show)
    }
    println("All four display/launch-check combinations remain independent")
}
