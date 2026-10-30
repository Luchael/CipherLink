package com.gametodo.nativeapp

import android.app.AlertDialog
import android.app.TimePickerDialog
import android.content.Context
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

object ResetTimeDialog {
    fun show(context: Context, game: GameRules.Game, onSaved: () -> Unit) {
        var selected=game.resetMinutes
        val box=LinearLayout(context).apply {orientation=LinearLayout.VERTICAL;setPadding(32,16,32,16)}
        val value=TextView(context).apply {textSize=24f}
        fun update() {value.text=selected?.let {"%02d:%02d KST".format(java.util.Locale.ROOT,it/60,it%60)} ?: "초기화 시각을 선택해 주세요"}
        box.addView(TextView(context).apply {text="한국 시간으로 지정합니다. 자동 완료와 게임 화면의 할 일 표시가 함께 바뀝니다."})
        box.addView(value);update()
        box.addView(Button(context).apply {
            text="시간 선택"
            setOnClickListener {
                val minute=selected ?: 300
                TimePickerDialog(context,{_,h,m->selected=h*60+m;update()},minute/60,minute%60,true).show()
            }
        })
        val shortcuts=LinearLayout(context)
        listOf(0,240,300,360).forEach {minute ->
            shortcuts.addView(Button(context).apply {
                text="%02d:00".format(java.util.Locale.ROOT,minute/60);isAllCaps=false
                setOnClickListener {selected=minute;update()}
            },LinearLayout.LayoutParams(0,-2,1f))
        }
        box.addView(shortcuts)
        val dialog=AlertDialog.Builder(context).setTitle("${game.name} 초기화 시각")
            .setView(box).setNegativeButton("취소",null).setNeutralButton("기본값으로") {_,_->
                GameRules.setResetTime(context,game.key,null);onSaved()
            }.setPositiveButton("저장",null).create()
        dialog.setOnShowListener {dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
            selected?.let {GameRules.setResetTime(context,game.key,"%02d:%02d".format(java.util.Locale.ROOT,it/60,it%60));dialog.dismiss();onSaved()}
                ?: run {value.text="시간 선택 버튼으로 시각을 먼저 지정해 주세요"}
        }}
        dialog.show()
    }
}
