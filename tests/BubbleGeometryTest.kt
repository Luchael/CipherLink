import com.gametodo.nativeapp.BubbleGeometry

fun main() {
    val b = BubbleGeometry.clampBubble(2000,3000,1080,2400,168,72,120)
    check(b.x == 912 && b.y == 2112)
    check(BubbleGeometry.clampBubble(-100,-100,1080,2400,168,72,120) ==
        BubbleGeometry.Point(0,72))
    val p = BubbleGeometry.panelPoint(912,400,168,900,1080,1080,2400,24,72,120)
    check(p.x == 180 && p.y == 592)
    val top = BubbleGeometry.panelPoint(400,2100,168,900,1080,1080,2400,24,72,120)
    check(top.y == 996)
    // 회전된 좁은 화면에서도 음수 좌표가 나오지 않아야 한다.
    val rotated = BubbleGeometry.clampBubble(300,400,500,320,168,20,30)
    check(rotated.x in 0..332 && rotated.y in 20..122)
    println("원형 버튼 이동/저장 좌표/패널 화면 내 배치 테스트 통과")
}
