package com.gametodo.nativeapp

import android.app.Activity
import android.app.AlertDialog
import android.os.Bundle
import android.content.Intent
import android.net.Uri
import android.view.View
import android.view.WindowInsets
import android.view.inputmethod.EditorInfo
import android.view.WindowManager
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.CheckBox
import android.widget.Button
import android.widget.GridLayout
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.FrameLayout
import android.widget.TextView
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.Executors

/**
 * GameTodo 게임사 계정 연결.
 *
 * 설계 포인트:
 * 1. 상단의 로그인/계정 불러오기 버튼은 고정: WebView/하단 시스템 내비게이션 바가 가리지 못하게 한다.
 * 2. WebView 안에서 직접 로그인해야 앱의 CookieManager로 해당 세션을 확인할 수 있다.
 * 3. 공식 로그인 페이지를 WebView 안에서 표시하며 상태 조회는 사용자가 누를 때만 실행한다.
 * 4. 쿠키 값은 절대로 로그/화면에 출력하지 않는다. UID는 마지막 4자리만 보여준다.
 * 5. 계정 목록 API와 실제 진행도 API를 각각 검증한 뒤 암호화 저장한다.
 */
class GameAccountLoginActivity : Activity() {
    private lateinit var web: WebView
    private lateinit var status: TextView
    private lateinit var provider: String
    private lateinit var accountButton: Button
    private val executor = Executors.newSingleThreadExecutor()
    private val px get() = resources.displayMetrics.density
    private fun dp(x: Int) = (x * px).toInt()

    private val hoyoOrigins = listOf(
        "https://www.hoyolab.com/", "https://act.hoyolab.com/",
        "https://api-account-os.hoyolab.com/", "https://api-os-takumi.mihoyo.com/",
        "https://api-os-takumi.hoyoverse.com/", "https://account.hoyoverse.com/",
        "https://bbs-api-os.hoyolab.com/", "https://passport.hoyoverse.com/"
    )
    private val skOrigins = listOf("https://game.skport.com/", "https://web-api.skport.com/")
    private val homeHoyo = "https://www.hoyolab.com/home"
    private val homeSkport = "https://game.skport.com/endfield/sign-in"

    private fun report(message: String) = runOnUiThread { status.text = message }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        provider = intent.getStringExtra("provider") ?: "hoyolab"
        if (provider !in setOf("hoyolab", "endfield")) { finish(); return }
        window.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_ADJUST_RESIZE)

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(UiKit.BG)
        }
        // 상하·좌우 시스템 바 영역 확보. dp로 고정값을 사용하면 3버튼 내비게이션,
        // 제스처 모드, 디스플레이 컷아웃, 키보드 높이를 올바르게 처리할 수 없다.
        root.setOnApplyWindowInsetsListener { view: View, insets: WindowInsets ->
            val safe = insets.getInsets(WindowInsets.Type.systemBars() or WindowInsets.Type.displayCutout())
            val keyboard = insets.getInsets(WindowInsets.Type.ime()).bottom
            view.setPadding(safe.left, safe.top, safe.right, maxOf(safe.bottom, keyboard))
            insets
        }

        // 이 컨트롤은 WebView 위에 고정되므로 아래로 스크롤할 필요가 없다.
        val tools = GridLayout(this).apply {
            columnCount = 2
            setPadding(dp(12), dp(10), dp(12), dp(6))
        }
        fun toolButton(name: String, click: () -> Unit): Button {
            val b = UiKit.button(this,name,false,click)
            tools.addView(b, GridLayout.LayoutParams().apply {
                width = 0
                height = dp(56)
                columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f)
                setMargins(dp(4), dp(4), dp(4), dp(4))
            })
            return b
        }
        toolButton("로그인 페이지", { openOfficial() })
        accountButton = toolButton("계정 불러오기", { verifyLogin() })
        val title = UiKit.column(this,UiKit.BG,16).apply {
            addView(UiKit.text(this@GameAccountLoginActivity,
                if(provider=="hoyolab")"HoYoLAB 연결" else "SKPORT 연결",24f,UiKit.TEXT,true))
            addView(UiKit.text(this@GameAccountLoginActivity,
                "로그인 → 세션 확인 → 캐릭터 선택",13f,UiKit.MUTED))
        }
        root.addView(title)
        root.addView(tools, LinearLayout.LayoutParams(-1, -2))

        // 진행상태가 길어지더라도 버튼을 화면 아래로 밀어내지 않도록 별도 스크롤 영역 사용.
        val statusArea = ScrollView(this).apply { isFillViewport = false }
        status = TextView(this).apply {
            text = "[1/4] 공식 사이트에서 로그인하세요.\n로그인 완료 후 상단 '계정 불러오기'를 눌러 주세요."
            textSize = 13f
            setTextColor(UiKit.MUTED)
            setPadding(dp(18), dp(10), dp(18), dp(10))
        }
        statusArea.addView(status)
        root.addView(statusArea, LinearLayout.LayoutParams(-1, dp(94)))

        web = WebView(this)
        web.settings.javaScriptEnabled = true
        web.settings.domStorageEnabled = true
        web.settings.cacheMode = WebSettings.LOAD_DEFAULT
        web.settings.setSupportMultipleWindows(false)
        // 인증 페이지에서 쿠키와 Google SSO 리디렉션을 처리할 수 있도록 지원.
        val cm = CookieManager.getInstance()
        cm.setAcceptCookie(true)
        cm.setAcceptThirdPartyCookies(web, true)
        web.webChromeClient = WebChromeClient()
        web.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView?, request: WebResourceRequest?): Boolean {
                val url = request?.url ?: return false
                val host = url.host?.lowercase() ?: return true
                if (url.scheme != "https") return true
                val trusted = if (provider == "hoyolab") listOf("hoyolab.com", "hoyoverse.com", "mihoyo.com")
                    else listOf("skport.com", "gryphline.com")
                if (trusted.none { host == it || host.endsWith(".$it") }) {
                    // 제3자 인증은 기본 브라우저로 열린다. 브라우저 세션은 WebView로 공유되지 않는다.
                    // 인증 후에도 WebView가 로그인 상태가 아니라면 '다른 로그인 방법'이 필요하다.
                    startActivity(Intent(Intent.ACTION_VIEW, url))
                    report("외부 인증 페이지가 브라우저에서 열렸어. 별도 브라우저의 쿠키는 사이퍼링크에서 자동 읽을 수 없어.")
                    return true
                }
                return false
            }
            override fun onReceivedError(view: WebView?, request: WebResourceRequest?, error: WebResourceError?) {
                if (request?.isForMainFrame == true)
                    report("웹페이지 로딩 오류: ${error?.errorCode ?: -1} · 네트워크 상태와 주소를 확인하세요.")
            }
        }
        root.addView(web, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
        openOfficial()
    }

    private fun openOfficial() {
        val url = if (provider == "hoyolab") homeHoyo else homeSkport
        report("[1/4] 공식 ${if (provider == "hoyolab") "HoYoLAB" else "SKPORT"} 로그인 화면 이동 중…")
        web.loadUrl(url)
    }

    /** 웹뷰가 로드한 실제 URL도 포함해서, 각 도메인에 속하는 쿠키 헤더만 병합. */
    private fun rawCookieHeaders(): List<String?> {
        val cookies = CookieManager.getInstance()
        cookies.flush()
        val base = if (provider == "hoyolab") hoyoOrigins else skOrigins
        return (base + listOfNotNull(web.url)).distinct().map { url ->
            try { cookies.getCookie(url) } catch (_: Exception) { null }
        }
    }

    private fun cookieString(): String {
        val headers = rawCookieHeaders()
        return if (provider == "hoyolab") HoyoAuthCore.asHeader(HoyoAuthCore.merge(headers))
            else SkportCookieCore.header(headers)
    }

    private fun verifyLogin() {
        // 쿠키 수집은 UI 스레드에서 실행. 네트워크는 executor 스레드에서 실행.
        val credential = cookieString()
        if (provider == "endfield") {
            // WebView의 localStorage는 Android 앱 저장소와 분리되어 있으며,
            // 공식 game.skport.com 페이지가 현재 열린 경우에만 접근할 수 있다.
            // 쿠키에 ACCOUNT_TOKEN이 있으면 우선 사용한다.
            val token = SkportCookieCore.value(credential, "ACCOUNT_TOKEN")
            if (!token.isNullOrBlank()) {
                lookupWithCredential(JSONObject().put("accountToken", token).toString())
                return
            }
            val cred = SkportCookieCore.value(credential, "SK_OAUTH_CRED_KEY")
            val host = try { Uri.parse(web.url ?: "").host.orEmpty() } catch (_: Exception) { "" }
            if (host == "game.skport.com" || host.endsWith(".skport.com")) {
                web.evaluateJavascript("(function(){try{return localStorage.getItem('SK_TOKEN_CACHE_KEY')||'';}catch(e){return '';}})();") { result ->
                    // evaluateJavascript 반환값은 JS 문자열을 JSON으로 인코딩한 값이다.
                    val salt = try { JSONArray("[$result]").optString(0) } catch (_: Exception) { "" }
                    val usableSalt = if (salt == "null" || salt == "undefined") "" else salt
                    if (!cred.isNullOrBlank()) {
                        lookupWithCredential(JSONObject().put("cred", cred).put("salt", usableSalt).toString())
                    } else {
                        report("[2/4] SKPORT 로그인 세션을 확인했지만 캐릭터 API용 인증정보가 없습니다.\n공식 로그인 페이지에서 로그인을 완료한 뒤 다시 시도해 주세요.")
                    }
                }
            } else {
                report("[2/4] SKPORT 공식 웹페이지를 먼저 열어 로그인해 주세요.")
            }
            return
        }
        lookupWithCredential(credential)
    }

    private fun lookupWithCredential(credential: String) {
        if (provider == "hoyolab") {
            val parsed = HoyoAuthCore.merge(listOf(credential))
            if (!HoyoAuthCore.hasSession(parsed)) {
                report("로그인을 아직 확인하지 못했어요. 공식 페이지에서 로그인을 완료한 뒤 계정을 불러와 주세요.")
                return
            }
        } else if (credential.isBlank()) {
            report("[2/4] SKPORT 세션 없음. 먼저 공식 페이지에서 로그인하세요.")
            return
        }
        accountButton.isEnabled = false // 중복 API 호출과 반복 팝업을 방지
        report("[2/4] 게임사 API로 캐릭터 목록을 조회하고 있습니다…")
        executor.execute {
            try {
                if (provider == "hoyolab") {
                    val roles = HoyoProvider.roles(credential)
                    runOnUiThread { showPicker(roles, credential) }
                } else {
                    report("[3/4] SKPORT 인증정보를 검증하고 아시아 서버 캐릭터를 조회하는 중…")
                    val roles = EndfieldProvider.roles(credential)
                    runOnUiThread { showPicker(roles, credential) }
                }
            } catch (error: Exception) {
                report("[2/4] 캐릭터 목록 조회 실패: ${SafeFailure.describe(error)}")
            } finally {
                runOnUiThread { accountButton.isEnabled = true }
            }
        }
    }

    /**
     * 화면 높이가 낮아도 목록을 스크롤할 수 있고 선택 버튼은 화면 하단 고정.
     * UID는 계정 구별이 필요한 경우에만 끝 네 자리로 표시. 여러 서버 계정 선택 가능.
     */
    private fun showPicker(roles: List<GameRole>, credential: String) {
        if (roles.isEmpty()) {
            report(if (provider == "hoyolab") "HoYoLAB 캐릭터 목록은 비어 있습니다. 게임 계정 연동 및 서버 설정을 확인하세요."
                   else "SKPORT 캐릭터 바인딩 목록에서 아시아 서버 캐릭터를 찾지 못했습니다.")
            return
        }
        val checked = BooleanArray(roles.size) { i ->
            roles.size==1 && (provider=="endfield" || HoyoProvider.isAsiaRole(roles[i]))
        }
        val list = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(14),dp(8),dp(14),dp(8))
        }
        roles.forEachIndexed { index,role ->
            val eligible = provider=="endfield" || HoyoProvider.isAsiaRole(role)
            val serverName = if(eligible) "아시아 서버" else role.server
            val c = UiKit.column(this,UiKit.CARD,14)
            val check=CheckBox(this).apply {
                text = "${displayGame(role.game)} · ${role.nickname.ifBlank { "이름 없음" }}"
                textSize=16f
                setTextColor(UiKit.TEXT)
                buttonTintList=android.content.res.ColorStateList.valueOf(UiKit.BLUE)
                isChecked=checked[index];isEnabled=eligible
                setOnCheckedChangeListener {_,selected->checked[index]=selected}
            }
            c.addView(check)
            c.addView(UiKit.text(this,"$serverName   ·   UID 끝 ${role.uid.takeLast(4)}자리",12f,UiKit.MUTED))
            c.setOnClickListener { if(eligible) check.isChecked=!check.isChecked }
            list.addView(c,UiKit.margin(this,0,10))
        }
        val scroll = ScrollView(this).apply {
            setBackgroundColor(UiKit.BG)
            addView(list)
        }
        val dialog=AlertDialog.Builder(this)
            .setTitle("사용할 캐릭터 선택 (${roles.size}개)")
            .setView(scroll)
            .setNegativeButton("취소",null)
            .setPositiveButton("선택한 계정 연결",null)
            .create()
        dialog.setOnShowListener {
            dialog.window?.setBackgroundDrawable(UiKit.bg(this,UiKit.BG,20))
            dialog.window?.setLayout((resources.displayMetrics.widthPixels*0.92).toInt(),-2)
            scroll.layoutParams?.let { params ->
                params.height = minOf(dp(480),(resources.displayMetrics.heightPixels*0.48).toInt())
                scroll.layoutParams = params
            }
            dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                val chosen=roles.filterIndexed { i,_->checked[i] }
                if(chosen.isEmpty()) report("연결할 아시아 서버 캐릭터를 선택해 주세요.")
                else { dialog.dismiss();saveAndProbe(credential,chosen) }
            }
        }
        report("[5/5] ${roles.size}개 캐릭터 발견 · 사용할 계정을 선택하세요.")
        dialog.show()
    }

    private fun displayGame(game: String) = when(game) {
        "genshin" -> "원신"; "hsr" -> "붕괴: 스타레일"; "zzz" -> "젠레스 존 제로"
        "endfield" -> "엔드필드"; else -> game
    }

    private fun saveAndProbe(credential: String, selected: List<GameRole>) {
        report("[4/4] 게임별 일일/주간 실제 데이터 확인 중…")
        executor.execute {
            val results = selected.map { role ->
                try {
                    val list = if (provider == "hoyolab") HoyoProvider.progress(credential, role)
                        else EndfieldProvider.progress(credential, role)
                    "${displayGame(role.game)}: " +
                        if (list.isEmpty()) "계정 확인됨 / 지원하는 점수 필드 미발견" else list.joinToString { "${it.metric}: ${it.current}/${it.maximum}" }
                } catch (error: Exception) {
                    "${displayGame(role.game)}: 데이터 조회 실패 (${SafeFailure.describe(error)})"
                }
            }
            // 실제로 게임 역할 API에서 조회된 항목만 로컬에 암호화 저장한다.
            // 각 게임 상태가 실패하면 자동 완료 판정은 AccountSync에서 건너뛴다.
            val vault = SecureTokens(applicationContext)
            if (provider == "hoyolab") {
                vault.saveNamed("hoyolab_cookie", credential)
                saveRoles(vault, "hoyolab_roles", selected)
            } else {
                vault.saveNamed("endfield_token", credential)
                saveRoles(vault, "endfield_roles", selected)
            }
            report("[4/4] 계정 ${selected.size}개 저장 완료\n" + results.joinToString("\n"))
        }
    }

    override fun onDestroy() {
        if (::web.isInitialized) web.destroy()
        executor.shutdown()
        super.onDestroy()
    }
}

fun saveRoles(vault: SecureTokens, slot: String, roles: List<GameRole>) {
    val array = JSONArray()
    roles.forEach { array.put(JSONObject().put("game", it.game).put("uid", it.uid)
        .put("server", it.server).put("nickname", it.nickname)) }
    vault.saveNamed(slot, array.toString())
}

fun loadRoles(vault: SecureTokens, slot: String): List<GameRole> {
    val raw = vault.loadNamed(slot) ?: return emptyList()
    return try {
        val rows = JSONArray(raw)
        (0 until rows.length()).map { rows.getJSONObject(it) }.map {
            GameRole(it.getString("game"), it.getString("uid"), it.getString("server"), it.optString("nickname")) }
    } catch (_: Exception) { emptyList() }
}
