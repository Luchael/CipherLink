package com.gametodo.nativeapp

import android.app.AlertDialog
import android.app.DatePickerDialog
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.text.InputType
import android.view.ContextThemeWrapper
import android.view.WindowManager
import android.widget.*
import org.json.JSONObject
import java.time.LocalDate

/** Focusable accessibility dialog: editing never requires leaving the game for the app. */
class FloatingTaskComposer(private val service: Context, private val game: GameRules.Game,
    private val execute: (() -> Unit) -> Unit, private val onCreated: () -> Unit) {
    private val context=ContextThemeWrapper(service,android.R.style.Theme_Material_Light_Dialog_Alert)
    private val main=Handler(Looper.getMainLooper())
    private var dialog:AlertDialog?=null
    private var active=true

    fun dismiss() {active=false;dialog?.dismiss();dialog=null}

    fun show() {
        execute {
            try {
                val api=TodoistApi(service)
                val scope=api.accountScope()
                val locations=api.floatingLocations()
                main.post {if(active) render(locations,scope)}
            } catch (_:Exception) {main.post {if(active) {
                Toast.makeText(service,"추가할 위치를 불러오지 못했어요. Todoist 연결을 확인해 주세요.",Toast.LENGTH_LONG).show()
            }}}
        }
    }

    private fun render(locations:List<TodoistApi.FloatingLocation>,scope:String) {
        if(locations.isEmpty()) {
            Toast.makeText(service,"Todoist에 할 일을 넣을 섹션이 필요해요. 가챠·이벤트 섹션은 제외됩니다.",Toast.LENGTH_LONG).show()
            return
        }
        val prefs=service.getSharedPreferences("floating_task_drafts",Context.MODE_PRIVATE)
        val key="$scope:${game.key}"
        var pending=prefs.getString(key,null)?.let {text->runCatching {
            val j=JSONObject(text)
            FloatingTaskDraft(j.getString("title"),j.getString("date"),j.getString("repeat"),
                j.getString("project"),j.getString("section"),j.getString("label"),j.getString("request"))
        }.getOrNull()}
        val box=LinearLayout(context).apply {orientation=LinearLayout.VERTICAL;setPadding(24,12,24,12)}
        fun caption(text:String) {box.addView(TextView(context).apply {this.text=text;textSize=14f;setPadding(0,16,0,4)})}
        caption("${game.name} · 게임 라벨이 함께 저장됩니다")
        val title=EditText(context).apply {hint="할 일 이름";setText(pending?.title);maxLines=3;inputType=InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES}
        box.addView(title)
        var date=pending?.date?.let {runCatching {LocalDate.parse(it)}.getOrNull()} ?: GamePeriods.nowKst(System.currentTimeMillis()).toLocalDate()
        caption("날짜")
        val dateButton=Button(context).apply {text=date.toString()}
        dateButton.setOnClickListener {
            val picker=DatePickerDialog(context,{_,year,month,day->date=LocalDate.of(year,month+1,day);dateButton.text=date.toString()},date.year,date.monthValue-1,date.dayOfMonth)
            picker.window?.setType(WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY)
            picker.show()
        }
        box.addView(dateButton)
        val shortcuts=LinearLayout(context)
        listOf("오늘" to 0L,"내일" to 1L).forEach {(name,offset)->
            shortcuts.addView(Button(context).apply {text=name;setOnClickListener {
                date=GamePeriods.nowKst(System.currentTimeMillis()).toLocalDate().plusDays(offset);dateButton.text=date.toString()
            }},LinearLayout.LayoutParams(0,-2,1f))
        }
        box.addView(shortcuts)
        caption("반복")
        val repeat=Spinner(context).apply {adapter=ArrayAdapter(context,android.R.layout.simple_spinner_dropdown_item,
            listOf("반복 안 함","매일","매주","매월","N일마다","직접 입력"));setSelection(if(pending?.repeat.isNullOrBlank()) 0 else 5)}
        box.addView(repeat)
        val rule=EditText(context).apply {hint="N일의 숫자 또는 반복 규칙 (예: 매주 월요일)";setText(pending?.repeat);isSingleLine=true}
        box.addView(rule)
        repeat.onItemSelectedListener=object:AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent:AdapterView<*>?)=Unit
            override fun onItemSelected(parent:AdapterView<*>?,view:android.view.View?,position:Int,id:Long) {
                rule.visibility=if(position>=4) android.view.View.VISIBLE else android.view.View.GONE
                rule.inputType=if(position==4) InputType.TYPE_CLASS_NUMBER else InputType.TYPE_CLASS_TEXT
                rule.hint=if(position==4) "반복 간격: 1~366일" else "예: 매주 월요일 / 매 49일"
            }
        }
        caption("프로젝트 / 섹션")
        val section=Spinner(context).apply {adapter=ArrayAdapter(context,android.R.layout.simple_spinner_dropdown_item,locations)
            setSelection(locations.indexOfFirst {it.projectId==pending?.project && it.sectionId==pending?.section}.coerceAtLeast(0))}
        box.addView(section)
        val status=TextView(context).apply {text="미래 날짜나 게임 초기화 전의 할 일은 시작 시각 이후 목록에 나타납니다."}
        box.addView(status)
        val inputs=listOf(title,dateButton,shortcuts,repeat,rule,section)
        fun editable(enabled:Boolean) {inputs.forEach {it.isEnabled=enabled};for(i in 0 until shortcuts.childCount) shortcuts.getChildAt(i).isEnabled=enabled}
        if(pending!=null) {editable(false);status.text="이전 추가 요청이 남아 있어요. 같은 내용으로 재시도하면 중복 등록을 방지합니다."}
        val current=AlertDialog.Builder(context).setTitle("할 일 추가").setView(ScrollView(context).apply {addView(box)})
            .setNegativeButton("닫기",null).setPositiveButton(if(pending==null) "추가" else "같은 요청 재시도",null).create()
        dialog=current
        current.window?.setType(WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY)
        current.setOnShowListener {
            current.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                try {
                    val draft=pending ?: run {
                        val interval=rule.text.toString().trim()
                        val recurring=when(repeat.selectedItemPosition) {
                            0->"";1->"매일";2->"매주";3->"매월"
                            4->{require(interval.toIntOrNull() in 1..366) {"반복 간격을 1~366일로 입력해 주세요"};"매 ${interval.toInt()}일"}
                            else->{require(interval.isNotBlank()) {"반복 규칙을 입력해 주세요"};interval}
                        }
                        val location=locations[section.selectedItemPosition]
                        FloatingTaskDraft(title.text.toString(),date.toString(),recurring,location.projectId,location.sectionId,game.label).also {it.validate()}
                    }
                    val j=JSONObject().put("title",draft.title).put("date",draft.date).put("repeat",draft.repeat)
                        .put("project",draft.project).put("section",draft.section).put("label",draft.label).put("request",draft.requestId)
                    // Retain identity and exact fields even if the app dies after server acceptance.
                    check(prefs.edit().putString(key,j.toString()).commit()) {"추가 요청을 저장하지 못했어요"}
                    pending=draft;editable(false)
                    current.getButton(AlertDialog.BUTTON_POSITIVE).isEnabled=false
                    current.getButton(AlertDialog.BUTTON_NEGATIVE).isEnabled=false
                    current.setCancelable(false);status.text="Todoist에 추가하고 있어요…"
                    execute {
                        try {
                            val api=TodoistApi(service)
                            check(api.accountScope()==scope) {"Todoist 계정이 변경됐습니다"}
                            api.createFloatingTask(draft)
                            prefs.edit().remove(key).commit()
                            main.post {if(active) {current.dismiss();onCreated();Toast.makeText(service,"할 일을 추가했어요",Toast.LENGTH_SHORT).show()}}
                        } catch (_:FloatingTaskRejected) {
                            prefs.edit().remove(key).commit()
                            main.post {if(active) {
                                pending=null;editable(true);status.text="반복 규칙이나 선택한 섹션을 확인해 주세요. Todoist에서 추가를 거절했습니다."
                                current.getButton(AlertDialog.BUTTON_POSITIVE).apply {isEnabled=true;text="수정해서 추가"}
                                current.getButton(AlertDialog.BUTTON_NEGATIVE).isEnabled=true;current.setCancelable(true)
                            }}
                        } catch (_:Exception) {main.post {if(active) {
                            status.text="추가 확인에 실패했어요. 같은 요청 재시도로 중복 없이 확인할 수 있습니다."
                            current.getButton(AlertDialog.BUTTON_POSITIVE).apply {isEnabled=true;text="같은 요청 재시도"}
                            current.getButton(AlertDialog.BUTTON_NEGATIVE).isEnabled=true;current.setCancelable(true)
                        }}}
                    }
                } catch(ex:IllegalArgumentException) {status.text=ex.message ?: "입력 내용을 확인해 주세요"}
                  catch(_:Exception) {status.text="추가 요청을 준비하지 못했어요. 다시 시도해 주세요."}
            }
        }
        current.show()
        current.window?.setLayout((service.resources.displayMetrics.widthPixels*0.9).toInt(),WindowManager.LayoutParams.WRAP_CONTENT)
        current.window?.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)
    }
}
