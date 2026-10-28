package com.gametodo.nativeapp

import android.content.Context

/**
 * Todoist의 반복 일정과 게임 서버 회차를 연결하는 계층.
 * 게임 데이터를 읽지 못해도 다른 게임·다른 작업을 체크하지 않는다.
 * PC와 모바일은 동일한 Todoist 계정을 쓰되 개별적으로 로그인한다.
 */
class AccountSync(private val context: Context) {
    private val vault = SecureTokens(context)
    private val prefs = context.getSharedPreferences("game_observation_v1", Context.MODE_PRIVATE)

    /**
     * 화면 인식은 사용하지 않는다. 정상 연결된 계정의 API에서만 상태를 읽는다.
     * 일일 메모와 엔드 콘텐츠를 독립 조회해 한쪽 오류가 다른 쪽을 막지 않도록 한다.
     */
    fun snapshots(): List<AccountGauge> {
        val gauges = mutableListOf<AccountGauge>()
        vault.loadNamed("hoyolab_cookie")?.let { cookie ->
            for (role in loadRoles(vault,"hoyolab_roles")) {
                if (!GameLookupSettings.enabled(context, role.game)) continue
                try { gauges.addAll(HoyoProvider.progress(cookie, role)) }
                catch (_: Exception) { /* 미확인 상태를 임의로 0점/완료로 간주하지 않는다. */ }
                try { gauges.addAll(EndgameRecords.fetch(cookie, role)) }
                catch (_: Exception) { /* 엔드 콘텐츠 API는 별도로 실패 가능 */ }
            }
        }
        vault.loadNamed("endfield_token")?.let { token ->
            for (role in loadRoles(vault,"endfield_roles")) {
                if (!GameLookupSettings.enabled(context, role.game)) continue
                try { gauges.addAll(EndfieldProvider.progress(token, role)) }
                catch (_: Exception) { /* 같은 원리 */ }
            }
        }
        return gauges
    }

    /**
     * UI의 '자동 완료 진단' 버튼에서 사용.
     * 어떤 단계 때문에 체크가 보류되었는지 확인하되, 이 함수는 절대 Todoist 완료 명령을 보내지 않는다.
     * 반환 정보에 쿠키/인증 토큰/UID 전체를 포함하지 않는다.
     */
    fun diagnose(todoist: TodoistApi, nowMillis: Long = System.currentTimeMillis()): List<String> {
        val roles = snapshots()
        if (roles.isEmpty()) return listOf("게임 상태가 비어 있습니다. 게임별 로그인·계정 선택·실시간 메모 API를 먼저 확인하세요.")
        val tasks = todoist.tasks()
        return roles.flatMap { gauge ->
            rule(gauge.game).filter { it.metric == gauge.metric }.map { binding ->
                val matching=tasks.filter { it.title in binding.titles &&
                    GameRules.all(context).any { game -> game.key == gauge.game && GameRules.matchingTask(game,it.title,it.labels) } }
                val cause = when {
                    !gauge.filled -> "점수 미달"
                    GamePeriods.currentCycle(gauge.game,binding.kind,nowMillis)==null && binding.kind!="endgame" -> "게임 초기화 전/직후"
                    binding.kind=="endgame" && !EndgameRecords.currentPeriod(gauge,nowMillis) -> "현재 시즌 확인 불가"
                    matching.isEmpty() -> "Todoist 일치하는 이름/라벨 없음"
                    matching.size>1 -> "같은 Todoist 작업 여러 개"
                    !RecurrenceWindow.isCurrentOccurrence(
                        matching.first().dueDate, matching.first().dueString,
                        matching.first().isRecurring, RecurrenceWindow.Kind.OTHER, nowMillis
                    ) -> "Todoist 다음 회차/오래된 반복 회차 또는 반복 규칙 확인 필요"
                    else -> "점수 충족 · 현재 회차 검증 후 즉시 완료 가능"
                }
                "${binding.titles.first()} · ${gauge.current}/${gauge.maximum} → $cause"
            }
        }.ifEmpty { listOf("API 점수는 있지만 등록된 자동 완료 규칙이 없습니다.") }
    }

    private data class Rule(val metric: String, val kind: String, val titles: List<String>)

    /** PC/Android 동일한 Todoist 제목 연결표. 수동/미검증 콘텐츠는 자동 완료 규칙에서 제외. */
    private val sharedRules: Map<String, List<Rule>> by lazy {
        val all = org.json.JSONObject(context.assets.open("todoist_bindings.json")
            .bufferedReader(Charsets.UTF_8).use { it.readText() }).getJSONArray("tasks")
        val result = mutableMapOf<String, MutableList<Rule>>()
        for (i in 0 until all.length()) {
            val row = all.getJSONObject(i)
            if (row.optString("status") != "auto") continue
            val kind = row.optString("cadence")
            if (kind !in setOf("daily", "weekly", "endgame")) continue
            val game = row.optString("game")
            val metric = row.optString("metric")
            val title = row.optString("title")
            if (game.isBlank() || metric.isBlank() || title.isBlank()) continue
            val titles = mutableListOf(title)
            row.optJSONArray("aliases")?.let { aliases ->
                for (j in 0 until aliases.length()) {
                    val alias = aliases.optString(j)
                    if (alias.isNotBlank() && alias !in titles) titles.add(alias)
                }
            }
            result.getOrPut(game) { mutableListOf() }.add(Rule(metric, kind, titles))
        }
        result
    }

    private fun rule(game: String): List<Rule> = sharedRules[game] ?: emptyList()

    /** 서버 초기화 전/직후, 미래 Todoist 예정일, 중복 회차는 완료 처리하지 않는다. */
    fun runOnce(todoist: TodoistApi, nowMillis: Long = System.currentTimeMillis()): List<String> {
        val results = mutableListOf<String>()
        // 주의: 일일/주간 초기화는 각 게임의 currentCycle()에서 판정한다.
        // 전역 오전 5시 차단을 두면 나선·혼돈 등의 독립 시즌 종료 처리까지 막는다.
        // 따라서 엔드 콘텐츠는 API가 명시한 현재 시즌/기간 기준으로 별도 판단한다.

        data class Candidate(val gauge: AccountGauge, val rule: Rule, val identity: String)
        val ready = mutableListOf<Candidate>()
        for (g in snapshots()) {
            if (!g.filled) continue
            for (binding in rule(g.game).filter { it.metric == g.metric }) {
                val id = when (binding.kind) {
                    "daily", "weekly" -> GamePeriods.currentCycle(g.game,binding.kind,nowMillis)
                    "endgame" -> g.periodKey?.takeIf { EndgameRecords.currentPeriod(g,nowMillis) }
                    else -> null
                } ?: continue
                ready.add(Candidate(g,binding,"${g.game}:${g.account}:${g.metric}:$id"))
            }
        }
        if (ready.isEmpty()) return results
        // API 요청을 최적화하기 위해 Todoist 전체 작업 목록을 1회만 가져온다.
        val tasks = todoist.tasks()
        val gameRules = GameRules.all(context).associateBy { it.key }
        for ((g, rule, key) in ready) {
            val gameRule = gameRules[g.game] ?: continue
            val matching = tasks.filter { task ->
                task.title in rule.titles && GameRules.matchingTask(gameRule,task.title,task.labels)
            }
            // 동일한 이름의 작업이 여러 개면 임의로 선택하지 않는다.
            if (matching.size != 1) continue
            val task = matching.first()
            // 주간/월간/N일 일정도 Todoist의 *현재 회차*에 속할 때만 자동 완료한다.
            // 반복 시작일이 지나 오래된 회차를 지금 완료하면 다음 회차가 건너뛰어질 수 있다.
            if (!RecurrenceWindow.isCurrentOccurrence(task.dueDate, task.dueString,
                    task.isRecurring, RecurrenceWindow.Kind.OTHER, nowMillis)) continue
            val doneId = "closed:$key:${task.id}"
            if (prefs.getBoolean(doneId,false)) continue
            val occurrence = when(rule.kind) {
                "endgame" -> "endgame:" + (g.periodKey ?: continue)
                "weekly" -> key.substringAfter(":${g.metric}:")
                else -> key.substringAfterLast(':')
            }
            CompletionDispatch.run(
                { todoist.completeForCycle(task.id,occurrence) },
                { prefs.edit().putBoolean(doneId,true).apply() },
                { CompletionNotifications.show(context, task.title, doneId) }
            )
            results.add("${task.title} 완료 (회차 $occurrence)")
        }
        return results
    }
}
