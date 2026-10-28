package com.gametodo.nativeapp

import android.accessibilityservice.AccessibilityServiceInfo
import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.WindowInsets
import android.view.accessibility.AccessibilityManager
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Switch
import android.widget.Spinner
import android.widget.ArrayAdapter
import android.widget.AdapterView
import android.content.res.ColorStateList
import java.util.concurrent.Executors

/** PC와 독립 실행되는 안드로이드 설정·상태 앱. 메인에 UID·비밀 토큰을 노출하지 않는다. */
class MainActivity : Activity() {
    private val io = Executors.newSingleThreadExecutor()
    private var page = 0
    private var pendingDiagnosticJson: String? = null
    private val diagnosticSaveRequest = 9909
    private lateinit var content: LinearLayout
    private lateinit var bottom: LinearLayout
    private var statusText = "준비됨"
    private lateinit var statusView: TextView

    private fun label(text: String, size: Float=15f, color:Int=UiKit.TEXT, bold:Boolean=false) =
        UiKit.text(this,text,size,color,bold)
    private fun rowTitle(text:String) { content.addView(label(text,19f,bold=true),UiKit.margin(this,10,10)) }
    private fun addCard(title:String, desc:String, action:String?=null, cb:(()->Unit)?=null) {
        val box=UiKit.column(this)
        box.addView(label(title,16f,bold=true))
        box.addView(label(desc,13f,UiKit.MUTED),UiKit.margin(this,6,2))
        if(action!=null && cb!=null) box.addView(UiKit.button(this,action,false,cb),UiKit.margin(this,10,0))
        content.addView(box,UiKit.margin(this,0,12))
    }
    private fun action(text:String, main:Boolean=false, cb:()->Unit) {
        content.addView(UiKit.button(this,text,main,cb),UiKit.margin(this,0,9))
    }
    private fun push(message:String) {
        runOnUiThread {
            statusText=message
            if(::statusView.isInitialized) statusView.text=message
        }
    }
    private fun startJob(message:String, action:()->String) {
        push(message)
        io.execute {
            try { push(action()) }
            catch (e:Exception) {
                // 키·쿠키·토큰이 예외 메시지에 섞이지 않도록 종류만 사용자에게 표시.
                push("실행 오류 (${e.javaClass.simpleName}). 계정 상태와 연결을 확인하세요.")
            }
        }
    }
    override fun onCreate(savedInstanceState:Bundle?) {
        super.onCreate(savedInstanceState)
        window.statusBarColor=UiKit.BG
        window.navigationBarColor=UiKit.BG
        page=savedInstanceState?.getInt("page") ?: 0
        render()
    }
    override fun onSaveInstanceState(state:Bundle) {state.putInt("page",page);super.onSaveInstanceState(state)}
    override fun onResume() { super.onResume(); if(::bottom.isInitialized) render() }
    private fun accessible():Boolean {
        val mgr=getSystemService(ACCESSIBILITY_SERVICE) as AccessibilityManager
        return mgr.getEnabledAccessibilityServiceList(AccessibilityServiceInfo.FEEDBACK_ALL_MASK)
            .any { it.resolveInfo.serviceInfo.packageName==packageName && it.resolveInfo.serviceInfo.name.endsWith("GameDetectionService") }
    }
    private fun connectedNames(slot:String):List<String> {
        return try {loadRoles(SecureTokens(this),slot).map { it.nickname.ifBlank { "이름 미등록" } }.distinct()}
        catch (_:Exception) { emptyList() }
    }
    private fun render() {
        val root=LinearLayout(this).apply {orientation=LinearLayout.VERTICAL;setBackgroundColor(UiKit.BG)}
        root.setOnApplyWindowInsetsListener { view:View, insets:WindowInsets ->
            val safe=insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            view.setPadding(safe.left,safe.top,safe.right,safe.bottom)
            insets
        }
        val top=UiKit.column(this,UiKit.BG,18)
        top.addView(label("사이퍼링크",26f,bold=true))
        top.addView(label("게임 할 일을 더 가볍게",13f,UiKit.MUTED))
        root.addView(top)
        val scroll=ScrollView(this).apply {clipToPadding=false;isFillViewport=false}
        content=LinearLayout(this).apply {
            orientation=LinearLayout.VERTICAL
            setPadding(UiKit.dp(this@MainActivity,18),0,UiKit.dp(this@MainActivity,18),UiKit.dp(this@MainActivity,28))
        }
        scroll.addView(content)
        root.addView(scroll, LinearLayout.LayoutParams(-1,0,1f))
        bottom=LinearLayout(this).apply {
            orientation=LinearLayout.HORIZONTAL
            setBackgroundColor(UiKit.CARD)
            setPadding(UiKit.dp(this@MainActivity,6),UiKit.dp(this@MainActivity,8),UiKit.dp(this@MainActivity,6),UiKit.dp(this@MainActivity,8))
        }
        arrayOf("⌂  홈","♙  계정","☑  할 일","⚙  설정").forEachIndexed { index,title ->
            val b=UiKit.button(this,title,page==index) {page=index;render()}
            b.textSize=12f
            bottom.addView(b,LinearLayout.LayoutParams(0,UiKit.dp(this,48),1f).apply {
                setMargins(UiKit.dp(this@MainActivity,2),0,UiKit.dp(this@MainActivity,2),0)
            })
        }
        root.addView(bottom)
        setContentView(root)
        when(page) {0->home();1->accounts();2->tasks();else->settingsPage()}
        statusView=label(statusText,12f,UiKit.MUTED)
        content.addView(statusView,UiKit.margin(this,16,6))
    }
    private fun home() {
        rowTitle("내 자동화")
        val t=SecureTokens(this)
        addCard("Todoist",if(t.load()!=null)"로그인 정보 저장됨 · 같은 Todoist 계정으로 동기화" else "연결이 필요해요",
            "Todoist 계정 확인") {startJob("Todoist 확인 중…") {"Todoist 연결 성공 · 미완료 ${TodoistApi(applicationContext).tasks().size}개"}}
        val count=connectedNames("hoyolab_roles").size
        addCard("HoYoLAB",if(count>0)"연동된 캐릭터 ${count}개" else "연결된 캐릭터 없음", "계정 관리") {page=1;render()}
        val enf=connectedNames("endfield_roles")
        addCard("명일방주: 엔드필드",if(enf.isNotEmpty())enf.joinToString(" · ") else "캐릭터를 연결해 주세요", "SKPORT 계정 연결") {launch("endfield")}
        addCard("게임 감지",if(accessible())"접근성 사용 중" else "접근성 권한이 꺼져 있어요",
            if(accessible())"설정 확인" else "간편 설정하기") {accessibilityHelp()}
        action("지금 동기화",true) {syncNow()}
    }
    private fun launch(provider:String) {
        startActivity(Intent(this,GameAccountLoginActivity::class.java).putExtra("provider",provider))
    }
    private fun accounts() {
        rowTitle("연결된 계정")
        addCard("HoYoLAB","원신 · 붕괴: 스타레일 · 젠레스 존 제로", "로그인 및 캐릭터 선택") {launch("hoyolab")}
        connectedNames("hoyolab_roles").forEach { name ->addCard(name,"연동된 HoYoLAB 캐릭터")}
        addCard("SKPORT","명일방주: 엔드필드 · 글로벌 아시아", "로그인 및 캐릭터 선택") {launch("endfield")}
        connectedNames("endfield_roles").forEach {name->addCard(name,"연동된 엔드필드 캐릭터")}
        // 별도 팝업으로 위젯 수준의 실시간 메모를 확인한다.
        // 미수령 보상, 에너지 등은 Todoist 자동 완료 점수와 구분해 표시한다.
        action("게임별 상세 상태 보기",true) {
            startJob("HoYoLAB·SKPORT의 실제 기록을 조회 중…") {
                val vault=SecureTokens(applicationContext)
                val fragments=mutableListOf<String>()
                vault.loadNamed("hoyolab_cookie")?.let { cookie ->
                    for(role in loadRoles(vault,"hoyolab_roles")) {
                        try {
                            val note=HoyoProvider.note(cookie,role)
                            val entries=HoyoProvider.detailLines(role,note)
                            val gauges = HoyoProvider.progressFromNote(role,note)
                            val auto = gauges.joinToString("\n") { g ->
                                "${g.metric}: ${g.current}/${g.maximum} · ${if (g.filled) "점수 충족" else "미달"}"
                            }
                            fragments.add("${role.nickname.ifBlank { role.game }} (${role.game})\n" +
                                (if(entries.isEmpty()) "표시할 실시간 메모 필드가 없습니다." else entries.joinToString("\n")) +
                                "\n\nTodoist 감지용 점수\n" + (auto.ifBlank { "주간 복합 조건 미확인 · 자동 체크 보류" }))
                        } catch(e:Exception) {
                            fragments.add("${role.game}: 조회 실패 — ${e.message ?: e.javaClass.simpleName}")
                        }
                    }
                }
                // 엔드 콘텐츠: 별 수/시즌 시작·종료 시각 등 확인 가능한 기록만 표시.
                // 기록 API가 없거나 만점 조건이 불확실한 콘텐츠는 자동 완료하지 않는다.
                vault.loadNamed("hoyolab_cookie")?.let { cookie ->
                    for (role in loadRoles(vault,"hoyolab_roles")) {
                        val scan = EndgameRecords.probe(cookie,role)
                        for (g in scan.gauges) fragments.add(
                            "${role.nickname.ifBlank { role.game }} · ${g.metric}\n" +
                            "${if (g.metric == "shiyu" && g.maximum == 4) "S등급 ${g.current}/4 (제4전선 1 + 제5전선 3)" else "달성 ${g.current}/${g.maximum}"}\n" +
                            (if (g.periodKey != null) "회차 확인됨" else "회차 정보 없음 · 자동 완료 보류")
                        )
                        if (scan.diagnostics.isNotEmpty()) {
                            fragments.add("${role.game} 엔드 콘텐츠 조회 진단\n" +
                                scan.diagnostics.joinToString("\n"))
                        }
                    }
                }
                vault.loadNamed("endfield_token")?.let { token ->
                    for(role in loadRoles(vault,"endfield_roles")) {
                        try {
                            val gs=EndfieldProvider.progress(token,role)
                            fragments.add("엔드필드 (${role.nickname})\n"+
                                if(gs.isEmpty())"조회 가능한 진행도 없음" else gs.joinToString("\n") { "${it.metric}: ${it.current}/${it.maximum}" })
                        } catch(e:Exception) {fragments.add("엔드필드: 조회 실패 — ${e.message ?: e.javaClass.simpleName}")}
                    }
                }
                val appVersion = try { packageManager.getPackageInfo(packageName, 0).versionName ?: "알 수 없음" }
                    catch (_: Exception) { "알 수 없음" }
                val report = "CipherLink Android $appVersion · 엔드 콘텐츠 조회 방식 v0.10.1\n\n" +
                    fragments.joinToString("\n\n").ifBlank { "먼저 게임 계정을 연결해 주세요." }
                runOnUiThread {
                    AlertDialog.Builder(this).setTitle("게임 계정 실시간 상태")
                        .setMessage(report).setPositiveButton("닫기",null).show()
                }
                "상세 데이터 조회 완료"
            }
        }
        // 테스트 중인 API는 15분 주기에서 호출하지 않는다.
        // 버튼을 누른 경우에만 읽기 전용 요청하며, 결과로 Todoist를 변경하지 않는다.
        action("미검증 엔드콘텐츠 API 시험 조회") {
            startJob("엔드콘텐츠 시험 API를 확인하는 중…") {
                val vault = SecureTokens(applicationContext)
                val cookie = vault.loadNamed("hoyolab_cookie")
                val roles = loadRoles(vault,"hoyolab_roles")
                val report = if (cookie == null || roles.isEmpty()) "먼저 HoYoLAB 계정을 연결해 주세요." else
                    roles.flatMap {role ->
                        val result = EndgameRecords.probe(cookie,role,includeExperimental = true)
                        listOf("${role.game}:\n" + result.diagnostics.joinToString("\n"))
                    }.joinToString("\n\n")
                runOnUiThread {
                    AlertDialog.Builder(this).setTitle("API 시험 조회 (읽기 전용)")
                        .setMessage(report).setPositiveButton("닫기",null).show()
                }
                "시험 조회 완료 · Todoist 변경 없음"
            }
        }
        action("연결된 데이터 실제 조회") {
            startJob("게임 진행도 확인 중…") {
                val gauges=AccountSync(applicationContext).snapshots()
                if(gauges.isEmpty()) "현재 조회 가능한 게임 점수가 없습니다." else
                    gauges.joinToString("\n") {"${it.game}: ${it.current}/${it.maximum}"}
            }
        }
        addCard("API 정밀 진단 (비식별)",
            "본인이 누를 때만 전적 목록 및 이전 회차 시험 조회. 원본 쿠키·UID·닉네임 제외 JSON 저장", 
            "진단 실행 후 파일 내보내기") { exportSafeApiDiagnostic() }
        addCard("명조 글로벌 · 명일방주 한국/영어/일본 서버",
            "명조 글로벌 개인 임무 API는 미확인. 명일방주 계정 내부 조회는 실제 게임 연결을 끊을 위험이 있어 자동 로그인·조회 비활성화. 기존 수동 Todoist 체크는 유지합니다.")
        action("계정 연결 정보 초기화") {
            AlertDialog.Builder(this).setTitle("게임 계정 연결 해제")
                .setMessage("HoYoLAB·SKPORT의 저장된 연결만 해제합니다. Todoist 연결은 유지됩니다.")
                .setNegativeButton("취소",null).setPositiveButton("해제") {_,_->
                    val v=SecureTokens(this)
                    listOf("hoyolab_cookie","hoyolab_roles","endfield_token","endfield_roles")
                        .forEach(v::clearNamed)
                    render()
                }.show()
        }
    }
    /** 계정 식별자/토큰을 포함하지 않는 진단 스키마. 자동 전송은 하지 않는다. */
    private fun exportSafeApiDiagnostic() {
        startJob("읽기 전용 API 응답 구조를 검사하는 중…") {
            val report = SafeApiDiagnostics.collect(SecureTokens(applicationContext))
            val count = report.optJSONArray("requests")?.length() ?: 0
            pendingDiagnosticJson = report.toString(2)
            runOnUiThread {
                AlertDialog.Builder(this)
                    .setTitle("비식별 API 진단 준비됨")
                    .setMessage("전적 API ${count}개 요청의 필드 구조·배열 크기·점수·회차·오류 코드만 저장합니다.\n\n" +
                        "계정 쿠키, 로그인 토큰, UID, 닉네임, 링크, 이미지 주소는 저장하지 않습니다.\n" +
                        "날짜·점수 등 게임 진행도는 포함되므로 저장 후 파일 내용을 확인하고 공유하세요.\n\n" +
                        "이 기능은 게임 조작 및 Todoist 자동 완료를 하지 않습니다.\n" +
                        "이전 회차 조회는 별도 실험으로 기록되며 자동 판정에 사용하지 않습니다.")
                    .setNegativeButton("취소") { _, _ -> pendingDiagnosticJson = null }
                    .setPositiveButton("파일 저장") { _, _ ->
                        val intent = Intent(Intent.ACTION_CREATE_DOCUMENT).apply {
                            addCategory(Intent.CATEGORY_OPENABLE)
                            type = "application/json"
                            putExtra(Intent.EXTRA_TITLE, "CipherLink_api_diagnostic_safe.json")
                        }
                        startActivityForResult(intent, diagnosticSaveRequest)
                    }
                    .show()
            }
            "비식별 진단 ${count}개 준비됨 · 파일 내보내기 선택 가능"
        }
    }

    @Deprecated("Android SAF 결과 처리; 기존 Activity와 호환성 유지")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode != diagnosticSaveRequest) return
        val text = pendingDiagnosticJson
        pendingDiagnosticJson = null
        if (resultCode != Activity.RESULT_OK || data?.data == null || text == null) return
        try {
            contentResolver.openOutputStream(data.data!!, "w")?.use {
                it.write(text.toByteArray(Charsets.UTF_8))
            } ?: error("출력 스트림 생성 실패")
            push("진단 JSON을 선택한 위치에 저장했습니다. 공유 전에 내용을 확인하세요.")
        } catch (_: Exception) {
            push("파일 저장 실패. 저장 권한/공간을 확인하세요.")
        }
    }

    private fun tasks() {
        rowTitle("할 일 동기화")
        addCard("계정 데이터 기반 완료","게임 초기화 전에는 체크하지 않고, 동일 회차는 한 번만 처리해요.")
        addCard("가챠 자동 관리","시작일은 Todoist 날짜, 종료되면 앱에서 자동 완료해요.")
        action("지금 동기화",true) {syncNow()}
        action("자동 완료가 안 되는 이유 확인") {
            startJob("서버 회차·완료 점수·Todoist 날짜를 점검하고 있어요…") {
                val result=AccountSync(applicationContext).diagnose(TodoistApi(applicationContext))
                runOnUiThread {
                    AlertDialog.Builder(this).setTitle("자동 완료 진단")
                        .setMessage(result.joinToString("\n\n"))
                        .setPositiveButton("닫기",null).show()
                }
                "자동 완료 진단 완료"
            }
        }
    }
    private fun syncNow() {
        startJob("가챠 및 게임 진행도 동기화 중…") {
            val todoist=TodoistApi(applicationContext)
            val created=MobileBannerSync(applicationContext).run(todoist,force=true)
            val updated=AccountSync(applicationContext).runOnce(todoist)
            "새 가챠 ${created}개 · 완료 감지 ${updated.size}개"
        }
    }
    /**
     * 설치된 앱의 이름과 패키지 ID를 직접 선택한다.
     * 갤럭시 스토어/구글 플레이 버전의 실제 패키지명은 파일명과 다를 수 있다.
     * 매핑은 사용자가 바꾸거나 삭제하기 전까지 SharedPreferences에 유지된다.
     * QUERY_ALL_PACKAGES 권한 없이 Launcher 앱 목록만 읽는다.
     */
    private fun pickInstalledGame() {
        val intent=Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER)
        val items=packageManager.queryIntentActivities(intent,0)
            .map { item ->
                item.loadLabel(packageManager).toString() to item.activityInfo.packageName
            }.distinctBy { it.second }.sortedBy { it.first.lowercase() }
        if(items.isEmpty()) {
            AlertDialog.Builder(this).setMessage("실행 가능한 앱 목록을 찾지 못했습니다. 아래의 수동 패키지 등록을 이용해 주세요.")
                .setPositiveButton("확인",null).show()
            return
        }
        // 게임 이름에 익숙한 문자열만 우선 보여줘서 선택을 쉽게 한다.
        val hint = Regex("원신|스타레일|Zenless|젠레스|명조|Wuthering|Arknights|명일방주|림버스|Limbus|Stella|스텔라|Reverse|리버스|Genshin|Honkai|Endfield",RegexOption.IGNORE_CASE)
        val suggested=items.filter { hint.containsMatchIn(it.first) || GameRules.all(this).any {g -> it.second in g.packages} }
        val present=if(suggested.isNotEmpty()) suggested else items
        showAppList(present,items)
    }

    private fun showAppList(display:List<Pair<String,String>>,all:List<Pair<String,String>>) {
        val lines=display.map { "${it.first}\n${it.second}" }.toTypedArray()
        AlertDialog.Builder(this).setTitle("게임 앱 선택")
            .setItems(lines) {_,pos -> selectGameForPackage(display[pos].second,display[pos].first) }
            .setNeutralButton(if(display.size<all.size) "모든 앱 보기" else "닫기") {_,_->
                if(display.size<all.size) showAppList(all,all)
            }.setNegativeButton("취소",null).show()
    }

    private fun selectGameForPackage(pkg:String,appName:String) {
        val games=GameRules.all(this).filter { it.key!="colorsweeper" }.sortedBy {it.name}
        AlertDialog.Builder(this).setTitle("$appName → 어떤 게임?")
            .setItems(games.map { it.name }.toTypedArray()) { _,position ->
                val existing=getSharedPreferences("gametodo",MODE_PRIVATE).getString("packages","").orEmpty()
                val lines=existing.lines().filter { it.substringBefore('=') != pkg && it.contains('=') }
                val next=(lines+"$pkg=${games[position].key}").joinToString("\n")
                getSharedPreferences("gametodo",MODE_PRIVATE).edit().putString("packages",next).apply()
                push("저장됨: $appName → ${games[position].name} · 실행 중이라면 게임을 다시 열어 주세요")
            }.setNegativeButton("취소",null).show()
    }

    /** Android 설정 화면에서 사용하는 기본 슬라이드형 Switch + 간격 드롭다운. */
    private fun addAutoCheckSettings() {
        rowTitle("자동 확인")
        val panel = UiKit.column(this)
        val titleRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            gravity = Gravity.CENTER_VERTICAL
        }
        val titles = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        titles.addView(label("게임 계정 자동 확인", 16f, bold = true))
        val state = label("상태 확인 중…", 13f, UiKit.MUTED)
        titles.addView(state)
        titleRow.addView(titles, LinearLayout.LayoutParams(0, -2, 1f))
        val toggle = Switch(this).apply {
            text = ""
            showText = false
            minWidth = UiKit.dp(this@MainActivity, 54)
            minimumHeight = UiKit.dp(this@MainActivity, 48)
            isEnabled = false
            val states = arrayOf(intArrayOf(android.R.attr.state_checked), intArrayOf())
            thumbTintList = ColorStateList(states, intArrayOf(0xFFFFFFFF.toInt(), 0xFFE2E5EC.toInt()))
            trackTintList = ColorStateList(states, intArrayOf(UiKit.GREEN, 0xFF667181.toInt()))
            contentDescription = "게임 계정 자동 확인 켜기 또는 끄기"
        }
        titleRow.addView(toggle)
        panel.addView(titleRow)
        panel.addView(UiKit.spacer(this, 9))
        panel.addView(label("확인 간격", 14f, UiKit.MUTED))
        val minuteOptions = AutoCheckIntervals.minutes
        val names = minuteOptions.map(AutoCheckIntervals::display)
        val dropdown = Spinner(this).apply {
            minimumHeight = UiKit.dp(this@MainActivity, 48)
            adapter = ArrayAdapter(this@MainActivity,
                android.R.layout.simple_spinner_item, names).also {
                    it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
                }
        }
        dropdown.setSelection(minuteOptions.indexOf(SyncWorker.intervalMinutes(this)).coerceAtLeast(0))
        dropdown.isEnabled = false
        panel.addView(dropdown)
        panel.addView(label("Android에서 백그라운드 확인은 정확한 시각을 보장하지 않습니다. " +
            "끄면 주기 확인과 게임 실행 시 자동 계정 조회가 중지되며, 수동 동기화는 가능합니다.",
            12f, UiKit.MUTED), UiKit.margin(this, 7, 0))
        content.addView(panel, UiKit.margin(this, 0, 12))

        fun updateStatus(enabled: Boolean) {
            state.text = if (enabled) "● 켜짐 · ${AutoCheckIntervals.display(SyncWorker.intervalMinutes(this))}마다 확인" else "○ 꺼짐 · 자동 조회 중지"
            state.setTextColor(if (enabled) UiKit.GREEN else UiKit.MUTED)
        }
        var firstSelect = true
        dropdown.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onNothingSelected(parent: AdapterView<*>?) = Unit
            override fun onItemSelected(parent: AdapterView<*>?, view: View?, position: Int, id: Long) {
                if (firstSelect) { firstSelect = false; return }
                val minutes = minuteOptions[position]
                SyncWorker.setInterval(this@MainActivity, minutes)
                updateStatus(SyncWorker.isEnabled(this@MainActivity))
                push("확인 간격: ${AutoCheckIntervals.display(minutes)}")
            }
        }
        SyncWorker.restoreLegacy(this) { enabled ->
            // 프로그램에서 초기 체크 상태를 바꿀 때 리스너가 실수로 작업을 예약하지 않도록 함.
            toggle.setOnCheckedChangeListener(null)
            toggle.isChecked = enabled
            toggle.isEnabled = true
            dropdown.isEnabled = true
            toggle.setOnCheckedChangeListener { _, newValue ->
                SyncWorker.setEnabled(this, newValue)
                updateStatus(newValue)
                push(if (newValue) "자동 확인 켜짐 (${AutoCheckIntervals.display(SyncWorker.intervalMinutes(this))} 간격)" else "자동 확인 꺼짐")
            }
            updateStatus(enabled)
        }
    }

    /** 게임별 조회 토글. 미지원 게임은 ON을 선택해도 API 성공을 가장하지 않는다. */
    private fun addGameLookupSettings() {
        rowTitle("게임별 자동 조회")
        for ((key, name) in GameLookupSettings.names) {
            val supported = key in GameLookupSettings.implemented
            val panel = UiKit.column(this)
            val line = LinearLayout(this).apply { orientation=LinearLayout.HORIZONTAL; gravity=Gravity.CENTER_VERTICAL }
            val copy = LinearLayout(this).apply { orientation=LinearLayout.VERTICAL }
            copy.addView(label(name, 15f, bold=true))
            copy.addView(label(if (supported) "계정 API 조회 및 Todoist 자동 판정"
                else if (key=="arknights") "KR: 23:59 인증 조회는 게임 세션 충돌 위험 · Android 조회 어댑터 미연결"
                else "글로벌: 일일 진행도 조회 API 미검증 (중국 서버 API 사용 안 함)",
                12f, UiKit.MUTED))
            line.addView(copy, LinearLayout.LayoutParams(0, -2, 1f))
            val sw = Switch(this).apply {
                showText=false; text=""; isChecked=GameLookupSettings.enabled(this@MainActivity,key)
                isEnabled=supported
                contentDescription="$name 자동 계정 조회 켜기 또는 끄기"
            }
            sw.setOnCheckedChangeListener { _, isOn ->
                GameLookupSettings.setEnabled(this,key,isOn)
                push("$name 계정 조회 ${if(isOn) "켜짐" else "꺼짐"}")
            }
            line.addView(sw)
            panel.addView(line)
            content.addView(panel,UiKit.margin(this,0,6))
        }
        addCard("명일방주 23:59 자동 조회", "조회 1회라도 게임을 강제 로그아웃시킬 수 있습니다. " +
            "PC용 ArkPRTS 예약 조회는 별도 제공하며, Android는 안전한 단독 인증 경로가 아직 검증되지 않아 켤 수 없습니다.")
    }

    private fun settingsPage() {
        rowTitle("권한 및 설정")
        addCard("게임 실행 자동 감지",if(accessible())"● 권한 허용됨" else "○ 권한이 필요합니다",
            "접근성 설정 방법") {accessibilityHelp()}
        addCard("게임 화면 위에 할 일 표시",
            if (accessible()) "● 게임 감지 접근성 서비스로 표시 가능" else "○ 접근성 서비스를 먼저 켜 주세요",
            "게임 감지 사용법") { accessibilityHelp() }
        addAutoCheckSettings()
        addGameLookupSettings()
        addCard("배터리 사용량", "게임 실행 시 조회와 자동 확인 주기는 Android의 배터리 정책에 따라 지연될 수 있습니다.")
        action("접근성 설정 바로 열기") {openAccessibility()}
        rowTitle("고급 설정")
        action("설치된 게임 앱 선택해서 연결") { pickInstalledGame() }
        val prefs = getSharedPreferences("gametodo",MODE_PRIVATE)
        val custom = prefs.getString("packages", "").orEmpty()
        val recent = prefs.getString("last_detected_package", "없음")
        val unknown = prefs.getString("last_overlay_candidate_package", "없음")
        val hideReason = prefs.getString("last_overlay_hide_reason", "없음")
        val ignored = prefs.getString("last_overlay_ignore_reason", "없음")
        val overlayFailure = prefs.getString("last_overlay_show_failure", "없음")
        val overlayVisible = prefs.getBoolean("overlay_visible", false)
        addCard("플로팅 진단", "접근성: ${if(accessible()) "켜짐" else "꺼짐"} · 게임을 떠나면 자동 숨김\n앱이 표시한 상태: ${if(overlayVisible) "표시 요청 성공" else "표시하지 않음"} · 표시 실패: $overlayFailure\n감지된 게임 앱: $recent\n다른 앱 전환 후보: $unknown\n마지막 숨김 이유: $hideReason\n무시한 창: $ignored"+
            (if(custom.isNotBlank()) "\n직접 등록: ${custom.lines().filter{it.contains('=')}.size}개" else ""),
            "진단 새로고침") {render()}
        action("추가 게임 패키지 직접 등록") {
            val prefs=getSharedPreferences("gametodo",MODE_PRIVATE)
            val field=EditText(this).apply {
                setText(prefs.getString("packages",""));hint="패키지명=게임키 (줄 단위)";minLines=3
            }
            AlertDialog.Builder(this).setTitle("게임 패키지 추가").setView(field)
                .setNegativeButton("취소",null).setPositiveButton("저장") {_,_->
                    prefs.edit().putString("packages",field.text.toString()).apply();push("패키지 설정 저장됨")
                }.show()
        }
        action("Todoist 연결 해제") {
            AlertDialog.Builder(this).setTitle("Todoist 로그아웃")
                .setNegativeButton("취소",null).setPositiveButton("로그아웃") {_,_->
                    TodoistAuth(this).logout();render()
                }.show()
        }
    }
    private fun accessibilityHelp() {
        AlertDialog.Builder(this).setTitle("게임 자동 감지 켜기")
            .setMessage("① 접근성 설정 열기\n② 설치된 앱 또는 다운로드한 앱에서 사이퍼링크 게임 감지 선택\n③ 사용 허용을 켜기\n④ 사이퍼링크로 돌아와 상태 확인\n\n이 권한은 게임이 실행됐는지 알기 위해 사용해요. 화면 OCR은 기본 사용하지 않아요.")
            .setNegativeButton("나중에",null).setPositiveButton("접근성 설정 열기") {_,_->openAccessibility()}.show()
    }
    private fun openAccessibility() {startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))}
    override fun onDestroy() {io.shutdown();super.onDestroy()}
}
