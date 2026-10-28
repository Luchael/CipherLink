package com.gametodo.nativeapp

import android.app.Activity
import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/**
 * GameTodo 디자인 토큰. 외부 이미지/폰트 라이브러리를 쓰지 않아 Termux 빌드 부담을 줄인다.
 * 모든 컨트롤 크기는 dp, 글자는 sp. 터치 영역 최소 48dp.
 */
object UiKit {
    const val BG = 0xFFF3F5F8.toInt()
    const val CARD = 0xFFFFFFFF.toInt()
    const val PANEL = 0xFFE7EDF3.toInt()
    const val TEXT = 0xFF172B42.toInt()
    const val MUTED = 0xFF56677B.toInt()
    const val BLUE = 0xFF1C637B.toInt()
    const val ACCENT = 0xFF176C64.toInt()
    const val GREEN = 0xFF176C64.toInt()
    const val YELLOW = 0xFF9A6200.toInt()

    fun dp(c: Context, value: Int) = (c.resources.displayMetrics.density * value + .5f).toInt()
    fun bg(c: Context, color: Int, radius: Int = 18, stroke: Int? = null): GradientDrawable =
        GradientDrawable().apply {
            setColor(color); cornerRadius = dp(c, radius).toFloat()
            if (stroke != null) setStroke(dp(c, 1), stroke)
        }
    fun text(c: Context, title: String, size: Float = 15f, color: Int = TEXT, bold: Boolean = false): TextView =
        TextView(c).apply {
            text = title; textSize = size; setTextColor(color)
            if (bold) setTypeface(null, Typeface.BOLD)
            gravity = Gravity.CENTER_VERTICAL
            includeFontPadding = true
            setLineSpacing(0f,1.15f)
        }
    fun column(c: Context, color: Int = CARD, padding: Int = 16): LinearLayout =
        LinearLayout(c).apply {
            orientation = LinearLayout.VERTICAL
            background = bg(c, color)
            setPadding(dp(c,padding),dp(c,padding),dp(c,padding),dp(c,padding))
        }
    fun spacer(c: Context, height: Int): View = View(c).apply {
        layoutParams = LinearLayout.LayoutParams(-1, dp(c,height))
    }
    fun button(c: Context, title: String, primary: Boolean = false, onClick: () -> Unit): Button =
        Button(c).apply {
            text=title; textSize=14f; isAllCaps=false
            setTextColor(if (primary) Color.WHITE else TEXT)
            background=bg(c, if(primary) ACCENT else PANEL, 13)
            elevation=0f; minHeight=dp(c,50)
            setPadding(dp(c,12),dp(c,8),dp(c,12),dp(c,8))
            setOnClickListener { onClick() }
        }
    fun item(c: Context, title: String, subtitle: String, onClick: () -> Unit): LinearLayout =
        column(c,PANEL,12).apply {
            addView(text(c,title,15f,TEXT,true))
            addView(text(c,subtitle,12f,MUTED))
            setOnClickListener { onClick() }
            minimumHeight=dp(c,60)
        }
    fun margin(c: Context, top: Int = 0, bottom: Int = 0): LinearLayout.LayoutParams =
        LinearLayout.LayoutParams(-1, -2).apply { setMargins(0,dp(c,top),0,dp(c,bottom)) }
}
