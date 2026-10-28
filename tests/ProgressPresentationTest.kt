import com.gametodo.nativeapp.ProgressPresentation as P
fun main() {
    check(P.value(0,9) == "0 / 9" && P.state(0,9) == "진행 전")
    check(P.state(0,0) == "확인 필요" && P.value(null,9) == "정보 없음")
    check(P.state(9,9) == "목표 달성" && P.fraction(9,9) == 1000)
    check(P.fraction(1,4) == 250 && P.fraction(Int.MAX_VALUE,1) == 1000)
    check(P.title("shiyu") == "시유 방어전")
    println("Progress cards preserve zero, unknown and fulfilled values without inventing scores")
}
