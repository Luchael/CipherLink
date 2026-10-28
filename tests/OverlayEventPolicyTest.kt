import com.gametodo.nativeapp.OverlayEventPolicy as Policy

fun main() {
    fun checkPolicy(pkg: String, own: String = "com.gametodo.nativeapp", klass:String? = null,
        game:Boolean=false, pin:Boolean=false) = Policy.evaluate(pkg,own,klass,game,pin)
    check(checkPolicy("com.miHoYo.GI.samsung",game=true).kind == Policy.Kind.GAME)
    check(checkPolicy("com.samsung.android.game.gametools").kind == Policy.Kind.IGNORE)
    check(checkPolicy("com.samsung.android.game.gamehome").kind == Policy.Kind.IGNORE)
    check(checkPolicy("com.discord").kind == Policy.Kind.IGNORE)
    check(checkPolicy("com.android.systemui").kind == Policy.Kind.IGNORE)
    check(checkPolicy("com.gametodo.nativeapp","com.gametodo.nativeapp","android.widget.Button").kind == Policy.Kind.IGNORE)
    check(checkPolicy("com.gametodo.nativeapp","com.gametodo.nativeapp","com.gametodo.nativeapp.MainActivity").kind == Policy.Kind.HIDE_LATER)
    check(checkPolicy("com.sec.android.app.launcher").kind == Policy.Kind.HIDE_LATER)
    check(checkPolicy("com.other.app").delayMs <= 1000L)
    check(checkPolicy("com.other.app",pin=true).kind == Policy.Kind.HIDE_LATER) // 고정도 다른 앱에는 적용하지 않음
    check(checkPolicy("com.miHoYo.GI.samsung",game=true,pin=true).kind == Policy.Kind.GAME)
    check(checkPolicy("com.discord",klass="com.discord.MainActivity").kind == Policy.Kind.HIDE_LATER)
    println("전경 앱 전환 정책 회귀 테스트 통과")
}
