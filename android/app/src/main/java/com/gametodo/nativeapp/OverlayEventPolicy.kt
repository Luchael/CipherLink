package com.gametodo.nativeapp

/**
 * 플로팅 표시 기준: 실제 실행 중인 게임의 화면 위에서만 보여준다.
 * Game Booster/알림/키보드 등 작은 보조 창은 게임 전환으로 오인하지 않는다.
 * 홈 화면 또는 다른 앱의 Activity가 나타나면 짧은 전환 유예 후 숨긴다.
 * 과거 버전의 '고정' 설정이 남아 있어도 다른 앱에서 떠 있는 것은 허용하지 않는다.
 */
object OverlayEventPolicy {
    enum class Kind { GAME, IGNORE, HIDE_LATER }
    data class Decision(val kind: Kind, val delayMs: Long = 0L, val reason: String = "")

    private val transientPackages = listOf(
        "com.android.systemui", "com.google.android.inputmethod",
        "com.samsung.android.honeyboard", "com.sec.android.inputmethod",
        "com.android.permissioncontroller", "com.google.android.permissioncontroller",
        "com.samsung.android.permissioncontroller"
    )
    private val transientOverlayPackages = listOf(
        "com.samsung.android.game.", "com.samsung.android.gametools",
        "com.samsung.android.gamebooster", "com.discord"
    )
    private val launcherPackages = setOf(
        "com.sec.android.app.launcher", "com.google.android.apps.nexuslauncher",
        "com.android.launcher3", "com.miui.home", "com.huawei.android.launcher"
    )

    @Suppress("UNUSED_PARAMETER")
    fun evaluate(pkg: String, ownPackage: String, className: String?, matchedGame: Boolean,
                 pinned: Boolean): Decision {
        if (matchedGame) return Decision(Kind.GAME, reason = "game")
        val cls = className.orEmpty()
        val activity = cls.contains("Activity", ignoreCase = true)
        if (pkg == ownPackage) {
            return if (activity) Decision(Kind.HIDE_LATER, 250L, "own_activity")
                else Decision(Kind.IGNORE, reason = "own_overlay")
        }
        if (pkg in launcherPackages) return Decision(Kind.HIDE_LATER, 250L, "launcher")
        if (transientPackages.any { pkg == it || pkg.startsWith("$it.") } ||
            pkg.contains("inputmethod", ignoreCase = true)) {
            return Decision(Kind.IGNORE, reason = "auxiliary_window")
        }
        if (transientOverlayPackages.any { pkg == it || pkg.startsWith(it) } && !activity) {
            return Decision(Kind.IGNORE, reason = "auxiliary_window")
        }
        // 다른 앱 전체 화면은 바로 숨기되, 전환 이벤트의 흔들림을 막는 짧은 유예만 둔다.
        // 'pinned' 값은 사용하지 않는다. 다른 앱에 게임 플로팅이 남아 있으면 안 되기 때문.
        return Decision(Kind.HIDE_LATER, 600L, "other_app")
    }
}
