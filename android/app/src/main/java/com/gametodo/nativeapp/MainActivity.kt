package com.gametodo.nativeapp

import android.accessibilityservice.AccessibilityServiceInfo
import android.app.Activity
import android.app.AlertDialog
import android.app.Dialog
import android.content.Intent
import android.content.pm.PackageManager
import android.content.res.ColorStateList
import android.text.Editable
import android.text.TextWatcher
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.view.WindowInsets
import android.view.accessibility.AccessibilityManager
import android.widget.*
import java.time.ZonedDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Everyday app UI. Credentials and API diagnostics never appear in these views. */
class MainActivity : Activity() {
    private val jobs: UiJobRunner by lazy { UiJobRunner { runOnUiThread { updateBusy() } } }
    private lateinit var busyBar: ProgressBar
    private val requestButtons=mutableListOf<Triple<Button,String,String>>()
    private var page = 0
    private var statusText = "준비됐어요"
    private lateinit var content: LinearLayout
    private lateinit var statusView: TextView
    private fun dp(n: Int) = UiKit.dp(this,n)
    private fun label(text: String, size: Float=15f, color: Int=UiKit.TEXT, bold: Boolean=false) =
        UiKit.text(this,text,size,color,bold)
    private fun rowTitle(text: String) { content.addView(label(text,22f,bold=true),UiKit.margin(this,8,16)) }
    private fun addCard(title: String, desc: String, action: String?=null, cb:(()->Unit)?=null) {
        val box=UiKit.column(this)
        box.addView(label(title,17f,bold=true))
        if(desc.isNotBlank()) box.addView(label(desc,14f,UiKit.MUTED),UiKit.margin(this,7,2))
        if(action!=null && cb!=null) box.addView(UiKit.button(this,action,true,cb),UiKit.margin(this,12,0))
        content.addView(box,UiKit.margin(this,0,12))
    }
    private fun action(text: String, primary: Boolean=false, jobKey: String?=null, cb:()->Unit) {
        val button=UiKit.button(this,text,primary,cb)
        if(jobKey!=null) requestButtons+=Triple(button,jobKey,text)
        content.addView(button,UiKit.margin(this,0,10))
    }
    private fun updateBusy() {
        if(isDestroyed || !::statusView.isInitialized) return
        val active = jobs.snapshot()
        statusView.text = if(active.isEmpty()) statusText else active.values.joinToString("\n")
        busyBar.visibility = if(active.isEmpty()) View.GONE else View.VISIBLE
        statusView.setTextColor(if(active.isEmpty()) UiKit.MUTED else UiKit.BLUE)
        requestButtons.forEach { (button,key,title)->
            val loading=key in active
            button.isEnabled=!loading
            button.text=if(loading) "진행도를 불러오는 중…" else title
        }
    }
    private fun push(message: String) { runOnUiThread {
        if(!isDestroyed) { statusText=message;updateBusy() }
    } }
    private fun startJob(key: String, message: String, job:()->String) {
        jobs.submit(key,message,{push(it)}, {e->
            push("완료하지 못했어요 · ${SafeFailure.describe(e)}. 연결을 다시 시도해 주세요.")
        },job)
    }
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        page=state?.getInt("page") ?: 0
        window.statusBarColor=UiKit.BG; window.navigationBarColor=UiKit.CARD
        window.decorView.systemUiVisibility=View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR or View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR
        render()
        SyncWorker.restoreLegacy(this) { if(!isDestroyed) render() }
        if(android.os.Build.VERSION.SDK_INT>=33 && checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED &&
            !getPreferences(MODE_PRIVATE).getBoolean("completion_permission_asked",false)) {
            getPreferences(MODE_PRIVATE).edit().putBoolean("completion_permission_asked",true).apply()
            requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS),4210)
        }
    }
    override fun onSaveInstanceState(state: Bundle) { state.putInt("page",page); super.onSaveInstanceState(state) }
    override fun onResume() { super.onResume(); if(::content.isInitialized) render() }
    private fun accessible():Boolean = (getSystemService(ACCESSIBILITY_SERVICE) as AccessibilityManager)
        .getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)
        .any { it.resolveInfo.serviceInfo.packageName==packageName && it.resolveInfo.serviceInfo.name.endsWith("GameDetectionService") }
    private fun roles(slot: String) = runCatching { loadRoles(SecureTokens(this),slot) }.getOrDefault(emptyList())
    private fun render() {
        requestButtons.clear()
        val root=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL; setBackgroundColor(UiKit.BG) }
        root.setOnApplyWindowInsetsListener { view,insets ->
            val safe=insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            view.setPadding(safe.left,safe.top,safe.right,safe.bottom); insets
        }
        val header=LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL; gravity=Gravity.CENTER_VERTICAL; setPadding(dp(20),dp(18),dp(20),dp(16)) }
        header.addView(ImageView(this).apply { setImageDrawable(applicationInfo.loadIcon(packageManager)); contentDescription="사이퍼링크" },LinearLayout.LayoutParams(dp(42),dp(42)))
        val heading=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL; setPadding(dp(12),0,0,0) }
        heading.addView(label("사이퍼링크",24f,bold=true)); heading.addView(label("게임 할 일, 한곳에서",13f,UiKit.MUTED))
        header.addView(heading); root.addView(header)
        // Always visible, including when the page is scrolled or the browser returns.
        val busy=LinearLayout(this).apply { gravity=Gravity.CENTER_VERTICAL;setPadding(dp(20),dp(6),dp(20),dp(10)) }
        busyBar=ProgressBar(this).apply {isIndeterminate=true;indeterminateTintList=ColorStateList.valueOf(UiKit.GREEN)}
        busy.addView(busyBar,LinearLayout.LayoutParams(dp(28),dp(28)).apply {setMargins(0,0,dp(12),0)})
        statusView=label(statusText,15f,bold=true).apply {accessibilityLiveRegion=View.ACCESSIBILITY_LIVE_REGION_POLITE}
        busy.addView(statusView,LinearLayout.LayoutParams(0,-2,1f));root.addView(busy)
        val scroll=ScrollView(this).apply { isFillViewport=true; clipToPadding=false }
        content=LinearLayout(this).apply { orientation=LinearLayout.VERTICAL; setPadding(dp(20),dp(4),dp(20),dp(24)) }
        scroll.addView(content); root.addView(scroll,LinearLayout.LayoutParams(-1,0,1f))
        val nav=LinearLayout(this).apply { setBackgroundColor(UiKit.CARD); setPadding(dp(8),dp(8),dp(8),dp(8)) }
        listOf("홈","계정","할 일","설정").forEachIndexed { i,name ->
            nav.addView(UiKit.button(this,name,page==i) { page=i;render() },LinearLayout.LayoutParams(0,dp(50),1f).apply { setMargins(dp(3),0,dp(3),0) })
        }
        root.addView(nav); setContentView(root)
        when(page) { 0->home();1->accounts();2->tasks();else->settingsPage() }
        updateBusy()
    }
    private fun home() {
        val today=ZonedDateTime.now(ZoneId.of("Asia/Seoul")).format(DateTimeFormatter.ofPattern("M월 d일 EEEE",Locale.KOREAN))
        rowTitle(today)
        val connected=TodoistAuth(this).isConnected()
        addCard("Todoist",if(connected) "연결 정보가 저장돼 있어요. 게임 할 일을 동기화할 수 있습니다." else "먼저 Todoist를 연결해 주세요. 비밀번호는 공식 사이트에서만 입력합니다.",
            if(connected) "지금 동기화" else "Todoist 연결하기") { if(connected) syncNow() else connectTodoist() }
        val count=roles("hoyolab_roles").size+roles("endfield_roles").size
        addCard("게임 계정 ${count}개 연결됨","원신 · 스타레일 · 젠레스 존 제로 · 엔드필드", "게임 계정 관리") {page=1;render()}
        val options=InteractionSettings.read(this)
        addCard("게임 중 할 일",if(options.showTasks && accessible()) "게임 화면에 작은 아이콘이 표시됩니다. 아이콘을 눌러 할 일을 확인하세요."
            else if(!options.showTasks) "화면 위 할 일 표시가 꺼져 있어요. 자동 동기화 설정은 그대로 유지됩니다."
            else "게임 화면에 표시하려면 접근성 권한이 필요해요.","표시 설정") {page=3;render()}
        action("게임 진행도 보기",jobKey="details") {showGameDetails()}
    }
    private fun connectTodoist() {
        startJob("auth","Todoist 연결을 시작합니다…") {
            TodoistAuth(this).login {jobs.update("auth",it)}
            runOnUiThread { if(!isDestroyed) render() }
            "Todoist에 연결했어요. 이제 게임 할 일을 동기화할 수 있습니다."
        }
    }
    private fun launch(provider: String) { startActivity(Intent(this,GameAccountLoginActivity::class.java).putExtra("provider",provider)) }
    private fun accounts() {
        rowTitle("계정 연결")
        addCard("Todoist",if(TodoistAuth(this).isConnected()) "연결 정보 저장됨 · 필요하면 다시 연결할 수 있어요." else "공식 브라우저 로그인으로 연결합니다.",
            if(TodoistAuth(this).isConnected()) "Todoist 다시 연결" else "Todoist 연결하기") {connectTodoist()}
        val hoyo=roles("hoyolab_roles")
        addCard("HoYoLAB",if(hoyo.isEmpty()) "원신 · 스타레일 · 젠레스 존 제로의 Asia 계정을 연결합니다."
            else "${hoyo.size}개 캐릭터 연결됨", "HoYoLAB 연결") {launch("hoyolab")}
        val endfield=roles("endfield_roles")
        addCard("명일방주: 엔드필드",if(endfield.isEmpty()) "SKPORT 공식 로그인으로 Asia 캐릭터를 연결합니다."
            else "${endfield.size}개 캐릭터 연결됨", "SKPORT 연결") {launch("endfield")}
        action("상세 진행도 보기",true,jobKey="details") {showGameDetails()}
        addCard("다른 게임도 할 일을 체크할 수 있어요","계정 진행도 연동을 지원하지 않는 게임은 게임 화면의 목록에서 직접 완료할 수 있습니다. 가챠 일정 수집과 진행도 연동은 별개입니다.")
    }
    private fun tasks() {
        rowTitle("할 일")
        addCard("동기화","현재 회차의 목표 점수를 확인하면 바로 완료합니다. 이전 회차나 아직 시작하지 않은 할 일은 자동 완료하지 않아요.","지금 동기화") {syncNow()}
        addCard("가챠 일정","현재 캐릭터 픽업만 기간 한정 작업으로 관리합니다. 진행도와 일반 할 일 목록에는 섞지 않습니다.")
        action("지원하는 할 일 보기") {showTaskSupport()}
        action("완료 알림 설정") {startActivity(Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS).putExtra(Settings.EXTRA_APP_PACKAGE,packageName))}
    }
    private fun syncNow() {
        if(!TodoistAuth(this).isConnected()) { connectTodoist(); return }
        startJob("sync","게임 목표를 확인하고 있어요…") {
            val api=TodoistApi(applicationContext)
            val completed=AccountSync(applicationContext).runOnce(api)
            jobs.update("sync","가챠 일정을 확인하고 있어요…")
            val created=MobileBannerSync(applicationContext).run(api,force=true)
            "동기화 완료 · 새 가챠 ${created}개 · 완료한 할 일 ${completed.size}개"
        }
    }
    private fun showTaskSupport() {
        val rows=org.json.JSONObject(assets.open("todoist_bindings.json").bufferedReader().use {it.readText()}).getJSONArray("tasks")
        val entries=(0 until rows.length()).map {i-> val r=rows.getJSONObject(i)
            TaskSupport.Entry(r.getString("game"),r.getString("title"),r.getString("cadence"),r.optString("metric"),r.getString("status"),r.optString("note")) }
        val text=label(TaskSupport.report(entries),15f).apply {setPadding(dp(20),dp(16),dp(20),dp(16))}
        AlertDialog.Builder(this).setTitle("지원하는 할 일").setView(ScrollView(this).apply {addView(text)}).setPositiveButton("닫기",null).show()
    }
    private fun toggle(title: String, subtitle: String, checked: Boolean, onChange:(Boolean)->Unit) {
        val box=UiKit.column(this)
        val row=LinearLayout(this).apply {gravity=Gravity.CENTER_VERTICAL}
        val copy=LinearLayout(this).apply {orientation=LinearLayout.VERTICAL}
        copy.addView(label(title,16f,bold=true));copy.addView(label(subtitle,13f,UiKit.MUTED),UiKit.margin(this,6,0))
        row.addView(copy,LinearLayout.LayoutParams(0,-2,1f))
        row.addView(Switch(this).apply {
            isChecked=checked;showText=false;text="";contentDescription=title;minimumHeight=dp(48)
            thumbTintList=ColorStateList.valueOf(android.graphics.Color.WHITE)
            trackTintList=ColorStateList(arrayOf(intArrayOf(android.R.attr.state_checked),intArrayOf()),intArrayOf(UiKit.GREEN,0xFF8290A2.toInt()))
            setOnCheckedChangeListener {_,value->onChange(value)}
        },LinearLayout.LayoutParams(dp(58),dp(52)))
        box.addView(row);content.addView(box,UiKit.margin(this,0,12))
    }
    private fun settingsPage() {
        rowTitle("내 설정")
        val options=InteractionSettings.read(this)
        toggle("게임 화면에 할 일 표시","작은 사이퍼링크 아이콘을 누르면 할 일 목록이 열립니다.",options.showTasks) {
            InteractionSettings.set(this,InteractionSettings.SHOW,it);push(if(it) "할 일 표시를 켰어요" else "할 일 표시를 껐어요")
        }
        toggle("게임 실행 시 자동 확인","게임을 열 때 진행도를 조회합니다. 화면 표시와 별도로 동작합니다.",options.checkOnGameOpen) {
            InteractionSettings.set(this,InteractionSettings.CHECK,it);push(if(it) "게임 실행 시 확인을 켰어요" else "게임 실행 시 확인을 껐어요")
        }
        addCard("게임 화면 접근 권한",if(accessible()) "허용됨 · 위 두 기능에서 함께 사용하는 Android 권한입니다. 각 기능은 위 스위치로 따로 끌 수 있어요."
            else "게임을 구분하려면 접근성 권한이 필요해요. 화면을 캡처하거나 게임을 조작하지 않습니다.","권한 설정 열기") {accessibilityHelp()}
        rowTitle("연결된 게임 앱")
        val linked=installedApps().mapNotNull {app->GameRules.forPackage(this,app.second)?.let { Triple(app.first,app.second,it) }}
        if(linked.isEmpty()) addCard("연결된 앱이 없어요","게임 앱을 선택하면 설치 스토어와 관계없이 사용할 수 있어요.")
        linked.forEach { (name,pkg,game)->
            val box=appRow(name,pkg,"연결됨 · ${game.name}",true)
            box.setOnClickListener {selectGameForPackage(pkg,name)}
            content.addView(box,UiKit.margin(this,0,8))
        }
        action("게임 앱 연결 · 변경",true) {pickInstalledGame()}
        addCard("새 게임도 연결할 수 있어요","Todoist에서 같은 게임에 같은 라벨을 붙인 뒤 추가하세요. 연결한 게임 앱의 아이콘이 위 목록에 표시됩니다.","Todoist 라벨로 새 게임 추가") {discoverGameLabels()}
        rowTitle("자동 동기화")
        toggle("주기적으로 확인","PC가 꺼져 있어도 이 휴대폰에서 확인합니다.",SyncWorker.isEnabled(this)) {SyncWorker.setEnabled(this,it)}
        val box=UiKit.column(this);box.addView(label("확인 간격",16f,bold=true))
        val optionsMinutes=AutoCheckIntervals.minutes
        val spinner=Spinner(this).apply {
            minimumHeight=dp(52)
            adapter=ArrayAdapter(this@MainActivity,android.R.layout.simple_spinner_dropdown_item,optionsMinutes.map(AutoCheckIntervals::display))
            setSelection(optionsMinutes.indexOf(SyncWorker.intervalMinutes(this@MainActivity)).coerceAtLeast(0))
        }
        var initial=true
        spinner.onItemSelectedListener=object:AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(p:AdapterView<*>?)=Unit
            override fun onItemSelected(p:AdapterView<*>?,v:View?,position:Int,id:Long) {
                if(initial) {initial=false;return}
                SyncWorker.setInterval(this@MainActivity,optionsMinutes[position]);push("확인 간격을 저장했어요")
            }
        }
        box.addView(spinner);box.addView(label("배터리·네트워크 상태에 따라 확인 시각이 늦어질 수 있어요.",13f,UiKit.MUTED))
        content.addView(box,UiKit.margin(this,0,12))
        rowTitle("게임별 진행도 조회")
        for((key,name) in GameLookupSettings.names.filterKeys {it in GameLookupSettings.implemented}) {
            toggle(name,"연결된 계정의 진행도를 읽기 전용으로 확인합니다.",GameLookupSettings.enabled(this,key)) {GameLookupSettings.setEnabled(this,key,it)}
        }
        rowTitle("앱 정보와 업데이트")
        val version=packageManager.getPackageInfo(packageName,0).versionName ?: ""
        addCard("사이퍼링크 $version","최신 설치 파일과 버전별 변경 내용을 GitHub에서 확인합니다. 비공개 저장소는 브라우저에서 GitHub 로그인이 필요해요.","최신 버전 다운로드") {
            startActivity(Intent(Intent.ACTION_VIEW,android.net.Uri.parse("https://github.com/Luchael/CipherLink/releases/latest")))
        }
        action("Todoist 연결 해제") {
            AlertDialog.Builder(this).setTitle("Todoist 연결을 해제할까요?").setMessage("게임 계정과 기존 Todoist 작업은 그대로 유지됩니다.")
                .setNegativeButton("취소",null).setPositiveButton("연결 해제") {_,_->TodoistAuth(this).logout();render()}.show()
        }
    }
    private fun installedApps():List<Pair<String,String>> = packageManager
        .queryIntentActivities(Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER),0)
        .map {it.loadLabel(packageManager).toString() to it.activityInfo.packageName}
        .distinctBy {it.second}.sortedBy {it.first.lowercase(Locale.KOREAN)}
    private fun appRow(name: String,pkg: String,subtitle: String,linked: Boolean):LinearLayout {
        val box=UiKit.column(this,UiKit.CARD,14).apply {orientation=LinearLayout.HORIZONTAL;gravity=Gravity.CENTER_VERTICAL}
        box.addView(ImageView(this).apply {setImageDrawable(runCatching {packageManager.getApplicationIcon(pkg)}.getOrNull());contentDescription=name},LinearLayout.LayoutParams(dp(42),dp(42)))
        val copy=LinearLayout(this).apply {orientation=LinearLayout.VERTICAL;setPadding(dp(12),0,dp(8),0)}
        copy.addView(label(name,16f,bold=true));copy.addView(label(subtitle,13f,if(linked) UiKit.GREEN else UiKit.MUTED))
        box.addView(copy,LinearLayout.LayoutParams(0,-2,1f));box.addView(label(if(linked) "✓" else "＋",22f,UiKit.GREEN,true))
        return box
    }
    private fun pickInstalledGame() {
        val all=installedApps().filter {it.second!=packageName}
        if(all.isEmpty()) {push("선택할 수 있는 앱이 없어요");return}
        val recommended=all.filter {app->GameRules.forPackage(this,app.second)!=null || Regex("원신|스타레일|젠레스|명조|명일방주|림버스|스텔라|리버스|Genshin|Honkai|Zenless|Wuthering|Arknights|Limbus|Stella|Reverse|Endfield",RegexOption.IGNORE_CASE).containsMatchIn(app.first)}
        showAppList(if(recommended.isEmpty()) all else recommended,all)
    }
    private fun showAppList(display:List<Pair<String,String>>,all:List<Pair<String,String>>) {
        var visible=display
        val box=LinearLayout(this).apply {orientation=LinearLayout.VERTICAL;setPadding(dp(12),0,dp(12),0)}
        val search=EditText(this).apply {hint="앱 이름 검색";setSingleLine();textSize=16f;minimumHeight=dp(52);setTextColor(UiKit.TEXT)}
        val count=label("",13f,UiKit.MUTED)
        val list=ListView(this).apply {dividerHeight=dp(6)}
        val adapter=object:BaseAdapter() {
            override fun getCount()=visible.size
            override fun getItem(position:Int)=visible[position]
            override fun getItemId(position:Int)=position.toLong()
            override fun getView(position:Int,old:View?,parent:ViewGroup?):View {
                val (name,pkg)=visible[position];val game=GameRules.forPackage(this@MainActivity,pkg)
                return appRow(name,pkg,game?.let {"현재 연결 · ${it.name}"} ?: "아직 연결하지 않은 앱",game!=null)
            }
        }
        fun filter(query:String) {
            // Typing always searches all launchable apps, not only recommendations.
            visible=if(query.isBlank()) display else LabelGames.filterApps(all,query)
            count.text=if(visible.isEmpty()) "검색 결과가 없어요" else "${visible.size}개 앱"
            adapter.notifyDataSetChanged()
        }
        list.adapter=adapter;filter("")
        search.addTextChangedListener(object:TextWatcher {
            override fun beforeTextChanged(s:CharSequence?,start:Int,count:Int,after:Int)=Unit
            override fun onTextChanged(s:CharSequence?,start:Int,before:Int,count:Int) {filter(s?.toString().orEmpty())}
            override fun afterTextChanged(s:Editable?)=Unit
        })
        box.addView(search);box.addView(count,UiKit.margin(this,4,8))
        box.addView(list,LinearLayout.LayoutParams(-1,0,1f))
        val dialog=AlertDialog.Builder(this).setTitle("연결할 게임 앱 선택").setView(box)
            .setNeutralButton(if(display.size<all.size) "모든 앱 보기" else "닫기") {_,_->if(display.size<all.size) showAppList(all,all)}
            .setNegativeButton("취소",null).create()
        list.setOnItemClickListener {_,_,position,_->
            val app=visible[position];dialog.dismiss();selectGameForPackage(app.second,app.first)
        }
        dialog.show();dialog.window?.setLayout(-1,(resources.displayMetrics.heightPixels*0.82).toInt())
    }
    private fun discoverGameLabels(then: (() -> Unit)?=null) {
        if(!TodoistAuth(this).isConnected()) {connectTodoist();return}
        startJob("labels","Todoist에서 게임 라벨을 불러오고 있어요…") {
            val labels=TodoistApi(applicationContext).tasks().flatMap {it.labels}
            val candidates=LabelGames.candidates(labels,GameRules.all(this).map {it.label}.toSet())
            runOnUiThread {
                if(!isDestroyed) {
                    if(candidates.isEmpty()) AlertDialog.Builder(this).setTitle("추가할 게임 라벨이 없어요")
                        .setMessage("Todoist에서 새 게임의 할 일에 같은 라벨을 붙이고 다시 불러오세요. 이미 연결한 라벨은 게임 목록에 있습니다.")
                        .setPositiveButton("확인",null).show()
                    else chooseNewGameLabel(candidates,then)
                }
            }
            "게임 라벨을 불러왔어요"
        }
    }
    private fun chooseNewGameLabel(labels:List<String>,then:(()->Unit)?) {
        var selected=-1
        val dialog=AlertDialog.Builder(this).setTitle("게임으로 사용할 라벨 선택")
            .setSingleChoiceItems(labels.toTypedArray(),-1) {d,index->selected=index;(d as AlertDialog).getButton(AlertDialog.BUTTON_POSITIVE).isEnabled=true}
            .setNegativeButton("취소",null).setPositiveButton("게임 추가",null).create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).isEnabled=false
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                if(selected>=0) {
                    GameRules.addLabelGame(this,labels[selected]);dialog.dismiss();render()
                    if(then!=null) then() else pickInstalledGame()
                }
            }
        }
        dialog.show()
    }
    private fun selectGameForPackage(pkg:String,appName:String) {
        val games=GameRules.all(this).sortedBy {it.name}
        val choices=games.map {"${it.name}\n라벨: ${it.label}"}+"＋ Todoist 라벨로 새 게임 추가"
        val current=GameRules.forPackage(this,pkg)?.key
        var selected=games.indexOfFirst {it.key==current}
        val dialog=AlertDialog.Builder(this).setTitle("$appName 연결")
            .setSingleChoiceItems(choices.toTypedArray(),selected) {d,index->
                if(index==games.size) {d.dismiss();discoverGameLabels {selectGameForPackage(pkg,appName)}}
                else {selected=index;(d as AlertDialog).getButton(AlertDialog.BUTTON_POSITIVE).isEnabled=true}
            }
            .setNegativeButton("취소",null).setNeutralButton("연결 해제") {_,_->
                val prefs=getSharedPreferences("gametodo",MODE_PRIVATE)
                val rows=prefs.getString("packages","").orEmpty().lines().filter {it.substringBefore('=')!=pkg && it.contains('=')}
                // Explicitly suppress built-in package mapping too.
                prefs.edit().putString("packages",(rows+"$pkg=none").joinToString("\n")).apply();render()
            }.setPositiveButton("연결 저장",null).create()
        dialog.setOnShowListener {
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).isEnabled=selected>=0
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                if(selected<0) {push("목록에서 게임을 먼저 선택해 주세요.");return@setOnClickListener}
                val prefs=getSharedPreferences("gametodo",MODE_PRIVATE)
                val rows=prefs.getString("packages","").orEmpty().lines().filter {it.substringBefore('=')!=pkg && it.contains('=')}
                val game=games[selected];prefs.edit().putString("packages",(rows+"$pkg=${game.key}").joinToString("\n")).apply()
                dialog.dismiss();render()
                AlertDialog.Builder(this).setTitle("연결했어요").setMessage("$appName\n↓\n${game.name}\n\n다음 게임 실행부터 적용됩니다.").setPositiveButton("확인",null).show()
            }
        }
        dialog.show()
    }
    private data class DetailGroup(val game:String,val name:String,val gauges:List<AccountGauge>,val memo:List<String>,val error:String="")
    private fun showGameDetails() {
        startJob("details","게임 진행도를 불러오고 있어요…") {
            val vault=SecureTokens(applicationContext);val groups=mutableListOf<DetailGroup>()
            val cookie=vault.loadNamed("hoyolab_cookie")
            if(cookie!=null) for(role in loadRoles(vault,"hoyolab_roles")) {
                try {
                    val gameName=GameRules.all(this).firstOrNull {it.key==role.game}?.name ?: "게임"
                    jobs.update("details","$gameName · 실시간 진행도를 불러오고 있어요…")
                    val note=HoyoProvider.note(cookie,role)
                    jobs.update("details","$gameName · 현재 회차 기록을 불러오고 있어요…")
                    val gauges=HoyoProvider.progressFromNote(role,note)+EndgameRecords.fetch(cookie,role)
                    groups+=DetailGroup(role.game,role.nickname,gauges,HoyoProvider.detailLines(role,note))
                } catch(e:Exception) {groups+=DetailGroup(role.game,role.nickname,emptyList(),emptyList(),SafeFailure.describe(e))}
            }
            val token=vault.loadNamed("endfield_token")
            if(token!=null) for(role in loadRoles(vault,"endfield_roles")) {
                try {
                    jobs.update("details","엔드필드 · 진행도를 불러오고 있어요…")
                    groups+=DetailGroup(role.game,role.nickname,EndfieldProvider.progress(token,role),emptyList())
                }
                catch(e:Exception) {groups+=DetailGroup(role.game,role.nickname,emptyList(),emptyList(),SafeFailure.describe(e))}
            }
            runOnUiThread {if(!isDestroyed) renderDetails(groups)}
            "진행도를 새로 불러왔어요"
        }
    }
    private fun renderDetails(groups:List<DetailGroup>) {
        val dialog=Dialog(this)
        val root=LinearLayout(this).apply {orientation=LinearLayout.VERTICAL;setBackgroundColor(UiKit.BG);setPadding(dp(20),dp(20),dp(20),dp(16))}
        root.addView(label("게임 진행도",24f,bold=true));root.addView(label("방금 조회한 기록 · 한국 시간 기준",13f,UiKit.MUTED),UiKit.margin(this,5,16))
        val scroll=ScrollView(this);val list=LinearLayout(this).apply {orientation=LinearLayout.VERTICAL}
        scroll.addView(list);root.addView(scroll,LinearLayout.LayoutParams(-1,0,1f))
        if(groups.isEmpty()) list.addView(label("계정 화면에서 게임 계정을 먼저 연결해 주세요.",16f))
        for(group in groups) {
            val game=GameRules.all(this).firstOrNull {it.key==group.game}
            val card=UiKit.column(this)
            card.addView(label(game?.name ?: "게임 진행도",20f,bold=true))
            if(group.name.isNotBlank()) card.addView(label(group.name,14f,UiKit.MUTED),UiKit.margin(this,4,10))
            if(group.error.isNotBlank()) card.addView(label("기록을 가져오지 못했어요 · ${group.error}",14f,UiKit.MUTED))
            for(g in group.gauges.distinctBy {it.metric}) {
                val row=LinearLayout(this).apply {gravity=Gravity.CENTER_VERTICAL}
                row.addView(label(ProgressPresentation.title(g.metric),15f,bold=true),LinearLayout.LayoutParams(0,-2,1f))
                row.addView(label(ProgressPresentation.value(g.metric,g.current,g.maximum),17f,UiKit.BLUE,true))
                card.addView(row,UiKit.margin(this,14,6))
                card.addView(ProgressBar(this,null,android.R.attr.progressBarStyleHorizontal).apply {
                    max=1000;progress=ProgressPresentation.fraction(g.current,g.maximum)
                    progressTintList=ColorStateList.valueOf(UiKit.GREEN);progressBackgroundTintList=ColorStateList.valueOf(UiKit.PANEL)
                },LinearLayout.LayoutParams(-1,dp(7)))
                val period=if(g.metric !in setOf("daily","weekly","weekly_task","rogue_weekly","weekly_boss_used")) {
                    if(EndgameRecords.currentPeriod(g,System.currentTimeMillis())) " · 현재 회차" else " · 회차 확인 필요"
                } else ""
                card.addView(label(ProgressPresentation.state(g.current,g.maximum)+period,12f,UiKit.MUTED),UiKit.margin(this,5,4))
            }
            if(group.memo.isNotEmpty()) {
                card.addView(label("실시간 메모",15f,bold=true),UiKit.margin(this,18,6))
                group.memo.forEach {line->card.addView(label(line.replace(" true"," 예").replace(" false"," 아니오"),14f,UiKit.MUTED),UiKit.margin(this,3,3))}
            }
            if(group.gauges.isEmpty() && group.error.isBlank()) card.addView(label("조회할 수 있는 기록이 아직 없어요.",14f,UiKit.MUTED))
            list.addView(card,UiKit.margin(this,0,14))
        }
        root.addView(UiKit.button(this,"닫기",true) {dialog.dismiss()},UiKit.margin(this,12,0))
        dialog.setContentView(root);dialog.show()
        dialog.window?.setLayout(-1,(resources.displayMetrics.heightPixels*0.91).toInt())
    }
    private fun accessibilityHelp() {
        AlertDialog.Builder(this).setTitle("게임 화면 접근 허용")
            .setMessage("접근성 → 설치된 앱 → 사이퍼링크 게임 감지에서 사용을 허용해 주세요.\n\n권한을 허용한 뒤 이 앱에서 화면 표시와 게임 실행 시 확인을 각각 켜고 끌 수 있어요.")
            .setNegativeButton("나중에",null).setPositiveButton("설정 열기") {_,_->startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))}.show()
    }
    override fun onDestroy() {jobs.close();super.onDestroy()}
}
