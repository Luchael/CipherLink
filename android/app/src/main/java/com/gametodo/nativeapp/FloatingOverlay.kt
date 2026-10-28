package com.gametodo.nativeapp

import android.content.Context
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.os.Handler
import android.os.Looper
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import android.view.WindowManager
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.Button
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import java.util.concurrent.Executors
import kotlin.math.abs
import kotlin.math.roundToInt

/**
 * 게임 전경에서만 나타나는 원형 아이콘 오버레이.
 * - 작은 원형 버튼: 현재 실행된 게임 앱의 런처 아이콘만 표시 (문자 없음).
 * - 탭: Todoist 목록 패널 열기/닫기. 드래그: 위치 변경, 로컬 설정에 위치 저장.
 * - PC와 같은 Todoist 계정을 읽으며 미완료/날짜/섹션 필터와 완료 전 재검증 적용.
 * - 접근성 이벤트로 현재 게임을 감지하므로 화면 캡처/OCR/상시 폴링 없음.
 */
class FloatingOverlay(private val context: Context) {
    private val wm = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private val main = Handler(Looper.getMainLooper())
    private val io = Executors.newSingleThreadExecutor()
    private val prefs = context.getSharedPreferences("gametodo", Context.MODE_PRIVATE)
    private val density = context.resources.displayMetrics.density
    private fun dp(n: Int) = (n * density + .5f).toInt()
    private val bubbleSize = dp(56)

    private var game: GameRules.Game? = null
    private var gamePackage: String? = null
    private var bubbleView: FrameLayout? = null
    private var bubbleParams: WindowManager.LayoutParams? = null
    private var expanded = false
    private var panelView: LinearLayout? = null
    private var panelParams: WindowManager.LayoutParams? = null
    private var holder: LinearLayout? = null
    private var sequence = 0

    private fun bounds(): Pair<Int,Int> {
        val rectangle = wm.currentWindowMetrics.bounds
        return rectangle.width() to rectangle.height()
    }
    private fun bubblePosition(): Pair<Int,Int> {
        val (w,h) = bounds()
        // 설정은 px로 보관한다. 휴대폰 방향·해상도가 변경되면 다시 화면 안으로 제한.
        val x = prefs.getInt("bubble_x", w - bubbleSize - dp(16))
        val y = prefs.getInt("bubble_y", dp(100))
        val point = BubbleGeometry.clampBubble(x, y, w, h, bubbleSize, dp(24), dp(40))
        return point.x to point.y
    }
    private fun layout(x: Int,y: Int,width: Int,height: Int): WindowManager.LayoutParams =
        WindowManager.LayoutParams(width,height,
            WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
            PixelFormat.TRANSLUCENT).apply {
                gravity = Gravity.TOP or Gravity.START
                this.x = x; this.y = y
            }

    /** 활성 앱 패키지로 실제 설치된 앱의 런처 아이콘을 불러온다. */
    private fun installedIcon(target: GameRules.Game, activePackage: String?) =
        sequenceOf(activePackage).plus(target.packages.asSequence()).filterNotNull()
            .firstNotNullOfOrNull { pkg ->
                try { context.packageManager.getApplicationIcon(pkg) }
                catch (_: Exception) { null }
            } ?: context.getDrawable(android.R.drawable.sym_def_app_icon)

    fun setGame(next: GameRules.Game?, activePackage: String? = null) {
        if (next == null) { remove(); return }
        if (game?.key == next.key && gamePackage == activePackage && bubbleView != null) return
        remove()
        game = next
        gamePackage = activePackage
        val bubble = FrameLayout(context).apply {
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(Color.rgb(36, 47, 69))
                setStroke(dp(2), Color.rgb(124, 188, 234))
            }
            clipToOutline = true
            elevation = dp(5).toFloat()
            contentDescription = "${next.name} 할 일 열기. 드래그하여 이동"
        }
        bubble.addView(ImageView(context).apply {
            setImageDrawable(installedIcon(next, activePackage))
            scaleType = ImageView.ScaleType.CENTER_CROP
            // 둥근 테두리와 게임 아이콘 사이 여백. 아이콘 자체 외의 문자는 노출하지 않는다.
            setPadding(dp(5),dp(5),dp(5),dp(5))
        }, FrameLayout.LayoutParams(-1,-1))
        bubble.setOnClickListener { togglePanel(next) }
        attachDrag(bubble)
        val (x,y) = bubblePosition()
        val params = layout(x,y,bubbleSize,bubbleSize)
        try {
            wm.addView(bubble, params)
            bubbleView = bubble
            bubbleParams = params
            prefs.edit().putBoolean("overlay_visible", true)
                .remove("last_overlay_show_failure").apply()
        } catch (ex: Exception) {
            prefs.edit().putBoolean("overlay_visible", false)
                .putString("last_overlay_show_failure", ex.javaClass.simpleName).apply()
            bubbleView = null
            bubbleParams = null
        }
    }

    private fun attachDrag(view: View) {
        val threshold = ViewConfiguration.get(context).scaledTouchSlop
        var initialRawX = 0f
        var initialRawY = 0f
        var startX = 0
        var startY = 0
        var moving = false
        view.setOnTouchListener { v, e ->
            when (e.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    val p = bubbleParams ?: return@setOnTouchListener false
                    initialRawX = e.rawX; initialRawY = e.rawY
                    startX = p.x; startY = p.y
                    moving = false
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val p = bubbleParams ?: return@setOnTouchListener true
                    val dx = e.rawX - initialRawX
                    val dy = e.rawY - initialRawY
                    if (!moving && (abs(dx) > threshold || abs(dy) > threshold)) moving = true
                    if (moving) {
                        val (w,h) = bounds()
                        val point = BubbleGeometry.clampBubble(startX + dx.roundToInt(),
                            startY + dy.roundToInt(), w, h, bubbleSize, dp(24), dp(40))
                        p.x=point.x; p.y=point.y
                        try { wm.updateViewLayout(v,p) } catch (_: Exception) {}
                        // 열린 목록은 드래그 위치를 따라 이동.
                        positionPanel()
                    }
                    true
                }
                MotionEvent.ACTION_UP -> {
                    if (moving) {
                        bubbleParams?.let { prefs.edit().putInt("bubble_x",it.x)
                            .putInt("bubble_y",it.y).apply() }
                    } else v.performClick()
                    moving = false
                    true
                }
                MotionEvent.ACTION_CANCEL -> {
                    bubbleParams?.let { prefs.edit().putInt("bubble_x",it.x)
                        .putInt("bubble_y",it.y).apply() }
                    moving = false
                    true
                }
                else -> false
            }
        }
    }

    private fun positionPanel() {
        val params = panelParams ?: return
        val p = bubbleParams ?: return
        val (w,h) = bounds()
        val point = BubbleGeometry.panelPoint(p.x,p.y,bubbleSize,
            params.width,dp(390),w,h,dp(8),dp(24),dp(40))
        params.x = point.x
        params.y = point.y
        panelView?.let { try { wm.updateViewLayout(it,params) } catch (_: Exception) {} }
    }

    private fun togglePanel(target: GameRules.Game) {
        if (expanded) { hidePanel(); return }
        expanded = true
        val panel = LinearLayout(context).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(12),dp(12),dp(12),dp(12))
            background = GradientDrawable().apply {
                setColor(Color.rgb(29, 39, 56)); cornerRadius = dp(18).toFloat()
            }
            elevation = dp(5).toFloat()
        }
        val header = LinearLayout(context).apply { orientation=LinearLayout.HORIZONTAL }
        header.addView(TextView(context).apply {
            text = "${target.name} 할 일"
            textSize = 15f
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER_VERTICAL
        }, LinearLayout.LayoutParams(0,dp(48),1f))
        header.addView(Button(context).apply {
            text = "↻"; contentDescription = "새로고침"; isAllCaps=false
            setOnClickListener { refresh(target) }
        }, LinearLayout.LayoutParams(dp(58),dp(48)))
        header.addView(Button(context).apply {
            text="×"; contentDescription="접기"; isAllCaps=false
            setOnClickListener { hidePanel() }
        }, LinearLayout.LayoutParams(dp(52),dp(48)))
        panel.addView(header)
        val scroll = ScrollView(context)
        val list = LinearLayout(context).apply { orientation=LinearLayout.VERTICAL }
        scroll.addView(list)
        panel.addView(scroll, LinearLayout.LayoutParams(-1,dp(320)))
        val screenWidth = bounds().first
        val params = layout(0,0,(dp(320)).coerceAtMost((screenWidth-dp(20)).coerceAtLeast(dp(180))),
            WindowManager.LayoutParams.WRAP_CONTENT)
        try {
            // WindowManager에 추가하기 전에 패널 좌표를 계산해 화면 구석에서 깜빡이지 않게 한다.
            panelParams=params
            positionPanel()
            wm.addView(panel,params)
            panelView=panel; holder=list
            refresh(target)
        } catch (ex: Exception) {
            expanded=false
            panelView=null; panelParams=null; holder=null
            prefs.edit().putString("last_overlay_show_failure",ex.javaClass.simpleName).apply()
        }
    }

    private fun hidePanel() {
        sequence++ // 이전 비동기 응답은 버린다.
        panelView?.let { try { wm.removeView(it) } catch (_: Exception) {} }
        panelView=null; panelParams=null; holder=null; expanded=false
    }

    private fun message(msg: String) {
        holder?.apply {
            removeAllViews()
            addView(TextView(context).apply { text=msg; textSize=14f; setTextColor(Color.WHITE) })
        }
    }

    private fun refresh(target: GameRules.Game) {
        val id = ++sequence
        message("할 일 불러오는 중…")
        io.execute {
            try {
                val api = TodoistApi(context)
                val nowMillis = System.currentTimeMillis()
                val sectionIndex = api.floatingSections(nowMillis)
                val allTasks = api.tasks()
                val tasksById = allTasks.associateBy { it.id }
                val games = GameRules.all(context)
                val gameKeys: (TodoTask) -> Set<String> = { item ->
                    games.filter { GameRules.matchingTask(it, item.title, item.labels) }
                        .map { it.key }.toSet()
                }
                val tasks = allTasks.mapNotNull { item ->
                    OverlayTaskTree.displayTask(item, tasksById, target.key, nowMillis,
                        sectionIndex.excludedIds, sectionIndex.kinds, gameKeys)
                }
                main.post {
                    if (id != sequence || !expanded || game?.key != target.key) return@post
                    val list = holder ?: return@post
                    list.removeAllViews()
                    if (tasks.isEmpty()) { message("지금 체크할 수 있는 게임 할 일이 없습니다."); return@post }
                    tasks.forEach { item ->
                        val itemRow = LinearLayout(context).apply { orientation=LinearLayout.HORIZONTAL }
                        itemRow.addView(TextView(context).apply {
                            text = item.title; setTextColor(Color.WHITE); textSize=13f
                        }, LinearLayout.LayoutParams(0,-2,1f))
                        itemRow.addView(Button(context).apply {
                            text = "완료"
                            setOnClickListener {
                                isEnabled=false
                                io.execute {
                                    try {
                                        // PC/모바일에서 동일 Todoist 계정을 사용한다. 서버의 현재 회차를 다시 확인.
                                        val liveApi = TodoistApi(context)
                                        // Re-fetch ancestry as well as the child: a parent's due date,
                                        // section or game affiliation may have changed since display.
                                        val liveTree = liveApi.tasks().associateBy { it.id }.toMutableMap()
                                        val latest=liveApi.taskById(item.id)
                                        val now = System.currentTimeMillis()
                                        val sections = liveApi.floatingSections(now)
                                        if (latest != null && liveTree.containsKey(latest.id)) {
                                            liveTree[latest.id] = latest
                                            val current = OverlayTaskTree.displayTask(latest, liveTree,
                                                target.key, now, sections.excludedIds, sections.kinds, gameKeys)
                                            if (current != null && OverlayTaskTree.sameDisplayedOccurrence(item, current)) {
                                                liveApi.complete(item.id)
                                            }
                                        }
                                        main.post { if (expanded && game?.key==target.key) refresh(target) }
                                    } catch (_: Exception) {
                                        main.post { if (expanded) message("완료 요청에 실패했습니다. 다시 시도해 주세요.") }
                                    }
                                }
                            }
                        })
                        list.addView(itemRow)
                    }
                }
            } catch (ex: Exception) {
                main.post {
                    if (id==sequence && expanded) {
                        message(if (ex.message?.contains("섹션") == true)
                            "이벤트 섹션을 확인할 수 없어 목록을 숨깁니다."
                            else "Todoist 연결 또는 인터넷 상태를 확인하세요. (${ex.javaClass.simpleName})")
                    }
                }
            }
        }
    }

    private fun remove() {
        hidePanel()
        bubbleView?.let { try { wm.removeView(it) } catch (_: Exception) {} }
        bubbleView=null; bubbleParams=null; game=null; gamePackage=null
        prefs.edit().putBoolean("overlay_visible",false).apply()
    }

    fun dispose() { remove(); io.shutdownNow() }
}
