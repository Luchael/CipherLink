package com.gametodo.nativeapp

import android.accessibilityservice.AccessibilityService
import android.view.accessibility.AccessibilityEvent
import android.os.Handler
import android.os.Looper

/**
 * 게임 실행 감지: 앱 패키지명만 사용하며 화면 캡처·OCR은 하지 않는다.
 * Samsung Gaming Hub/Game Booster의 임시 창 이벤트 때문에
 * 플로팅이 1초 만에 사라지던 문제를 방지하기 위해 지연·예외 처리를 분리했다.
 */
class GameDetectionService : AccessibilityService() {
    private lateinit var overlay: FloatingOverlay
    private val handler = Handler(Looper.getMainLooper())
    private var pendingHide: Runnable? = null
    private var pendingPackage: String? = null
    private var activeGameKey: String? = null
    private val settingsListener = android.content.SharedPreferences.OnSharedPreferenceChangeListener { _, key ->
        if (key == InteractionSettings.SHOW && ::overlay.isInitialized && !InteractionSettings.read(this).showTasks)
            overlay.setGame(null)
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        // v0.9.0의 플로팅 고정 플래그는 더 이상 다른 앱 표시를 허용하지 않는다.
        prefs().edit().remove("overlay_pinned").apply()
        overlay = FloatingOverlay(this)
        prefs().registerOnSharedPreferenceChangeListener(settingsListener)
    }

    private fun prefs() = getSharedPreferences("gametodo", MODE_PRIVATE)

    private fun cancelHide() {
        pendingHide?.let(handler::removeCallbacks)
        pendingHide = null
        pendingPackage = null
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event?.eventType != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED) return
        if (!::overlay.isInitialized) return
        val options = InteractionSettings.read(this)
        if (!options.shouldObserveWindows) { overlay.setGame(null); return }
        val pkg = event.packageName?.toString() ?: return
        val game = GameRules.forPackage(this, pkg)
        val decision = OverlayEventPolicy.evaluate(
            pkg, packageName, event.className?.toString(), game != null, false
        )
        when (decision.kind) {
            OverlayEventPolicy.Kind.GAME -> {
                cancelHide()
                val target = game ?: return
                if (options.showTasks) overlay.setGame(target, pkg) else overlay.setGame(null)
                activeGameKey = target.key
                prefs().edit().putString("last_detected_package", pkg)
                    .putString("last_detected_game", target.key)
                    .putLong("last_game_event_time", System.currentTimeMillis()).apply()
                // 사용자가 설정한 간격 안에 앱 전환을 반복해도 중복 조회하지 않는다.
                val now = System.currentTimeMillis()
                if (options.checkOnGameOpen && SyncWorker.isEnabled(this) &&
                    now - prefs().getLong("last_launch_sync", 0L) >=
                    SyncWorker.intervalMinutes(this).toLong() * 60L * 1000L) {
                    prefs().edit().putLong("last_launch_sync", now).apply()
                    SyncWorker.checkOnce(this)
                }
            }
            OverlayEventPolicy.Kind.IGNORE -> {
                // 게임 안의 보조 창은 게임 종료 증거가 아니다.
                // 단, 실제로 다른 앱으로 전환해 숨김이 예약된 경우에는
                // 늦게 들어온 시스템 알림 이벤트가 숨김을 취소하지 못하도록 한다.
                prefs().edit().putString("last_overlay_ignore_reason", decision.reason).apply()
            }
            OverlayEventPolicy.Kind.HIDE_LATER -> {
                if (activeGameKey == null) return
                // 홈/다른 앱이 실제 전면으로 이동하면 고정 여부와 무관하게 숨긴다.
                // 단기 전환 이벤트를 위한 최대 600ms 유예만 둔다.
                if (pendingHide != null && pendingPackage == pkg) return
                cancelHide()
                pendingPackage = pkg
                val reason = decision.reason
                val action = Runnable {
                    if (activeGameKey != null) {
                        overlay.setGame(null)
                        activeGameKey = null
                        prefs().edit().putString("last_overlay_hide_reason", "$reason:$pkg")
                            .putLong("last_overlay_hide_time", System.currentTimeMillis()).apply()
                    }
                    pendingHide = null
                    pendingPackage = null
                }
                pendingHide = action
                prefs().edit().putString("last_overlay_candidate_package", pkg).apply()
                handler.postDelayed(action, decision.delayMs)
            }
        }
    }

    override fun onConfigurationChanged(newConfig: android.content.res.Configuration) {
        super.onConfigurationChanged(newConfig)
        if(::overlay.isInitialized) handler.post {overlay.onBoundsChanged()}
    }

    override fun onInterrupt() {
        // 접근성 일시 중단이 반드시 게임 종료를 뜻하지 않는다.
        // 특히 Samsung Game Booster에 의해 끊겼을 때 오버레이를 즉시 제거하면 깜빡인다.
        cancelHide()
    }

    override fun onDestroy() {
        prefs().unregisterOnSharedPreferenceChangeListener(settingsListener)
        cancelHide()
        if (::overlay.isInitialized) overlay.dispose()
        super.onDestroy()
    }
}
