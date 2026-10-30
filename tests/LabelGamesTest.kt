import com.gametodo.nativeapp.*
import java.time.LocalDate
import java.time.ZoneId

fun main() {
    val label="새 게임"
    val key=LabelGames.key(label)
    check(key==LabelGames.key(label) && key!=LabelGames.key("다른 게임"))
    check(LabelGames.candidates(listOf(label,label,"원신"," ","가챠"),setOf("원신"))==listOf(label))
    val games=listOf(GameRules.Game(key,label,"",label,null,emptyList()),
        GameRules.Game("genshin","원신","원신","원신",5,emptyList()))
    check(!GameRules.matchingTask(games[0],"[] 일일",emptyList()))
    check(GameRules.matchingTask(games[0],"오늘 할 일",listOf(label)))
    check(!GameRules.matchingTask(games[0],"할 일",listOf("새 게임2")))
    val now=LocalDate.parse("2026-10-28").atTime(12,0).atZone(ZoneId.of("Asia/Seoul")).toInstant().toEpochMilli()
    val parent=TodoTask("p","할 일",listOf(label),"","2026-10-28","daily","project")
    val child=parent.copy(id="c",title="하위 할 일",labels=emptyList(),dueDate=null,parentId="p")
    val membership:(TodoTask)->Set<String> = {t->games.filter {GameRules.matchingTask(it,t.title,t.labels)}.map {it.key}.toSet()}
    fun shown(p:TodoTask=parent) = OverlayTaskTree.displayTask(child,listOf(p,child).associateBy {it.id},key,now,setOf("event"),emptyMap(),membership,resetMinutes=300)
    check(shown()?.dueDate=="2026-10-28")
    check(shown(parent.copy(sectionId="event"))==null)
    check(shown(parent.copy(labels=listOf(label,"원신")))==null)
    check(shown(parent.copy(dueDate="2026-10-29"))==null)
    val apps=listOf("명조" to "com.kuro.global","새 게임" to "com.game.kr")
    check(LabelGames.filterApps(apps,"명조")==apps.take(1))
    check(LabelGames.filterApps(apps,"GAME.KR")==apps.drop(1))
    check(LabelGames.filterApps(apps,"없음").isEmpty())
    check(LabelGames.filterApps(apps," ")==apps)
    println("Label game membership, inherited tasks, conflict/event/future exclusion and app search passed")
}
