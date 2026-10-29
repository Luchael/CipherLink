import com.gametodo.nativeapp.BannerLabels
fun main() {
    check(BannerLabels.merge("원신").toSet()==setOf("원신","가챠"))
    val expected=setOf("스타레일","가챠","사용자 라벨")
    check(BannerLabels.merge("스타레일",listOf("스타레일","사용자 라벨")).toSet()==expected)
    check(BannerLabels.merge("스타레일",expected.toList()).toSet()==expected)
    println("Gacha labels are added once while game/user labels are preserved")
}
