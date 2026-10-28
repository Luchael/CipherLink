package com.gametodo.nativeapp

/** Read-only presentation of the shared Todoist bindings, without enabling providers. */
object TaskSupport {
    data class Entry(
        val game: String, val title: String, val cadence: String,
        val metric: String, val status: String, val note: String,
    )

    val groups = listOf("일일", "주간", "월간", "N일 주기")
    const val autoDescription = "연결·현재 회차·점수 확인 후 자동 감지"
    const val serverGuidance = "한국 서버가 있으면 한국 서버, 없으면 글로벌 Asia를 사용합니다. 출처 확인 없이 서버를 바꾸지 않습니다."
    const val mobileGuidance = "휴대폰에서 독립적으로 동기화·플로팅을 사용하며 PC를 계속 켜둘 필요는 없습니다.\n" +
        "Android 자동 확인은 절전·네트워크 상태에 따라 늦어질 수 있어 정확한 시각을 보장하지 않습니다.\n" +
        "설정의 「설치된 게임 앱 선택해서 연결」에서 실제 설치된 한국판/글로벌판 앱을 연결하세요."
    const val bannerGuidance = "가챠 일정은 위 할 일과 별도로 관리합니다.\n" +
        "원신·스타레일·젠레스 존 제로·엔드필드·림버스·명조: 한국어 PickupCal 경로 연결 대상이며 실제 일정 응답은 아직 미검증입니다.\n" +
        "스텔라 소라: 비공식 Ennead KR API의 한국어 한정 캐릭터 모집을 사용합니다. 리버스: 1999는 출처 조사 중이며 자동 등록은 보류합니다.\n" +
        "출처·서버·시작·종료 시각을 확인한 현재 캐릭터 픽업만 등록합니다."

    fun group(entry: Entry): String = when {
        entry.cadence == "daily" -> "일일"
        entry.cadence == "weekly" -> "주간"
        entry.cadence == "monthly" || entry.metric in setOf("theater", "spiral") -> "월간"
        entry.cadence in setOf("endgame", "rotation") -> "N일 주기"
        else -> throw IllegalArgumentException("작업 주기 확인 필요")
    }

    fun description(entry: Entry): String = when {
        entry.status == "auto" -> autoDescription + if (entry.note.isBlank()) "" else " · ${entry.note}"
        entry.status == "conditional" && entry.game == "arknights" ->
            "수동 확인 · Android 계정 조회 미지원 · PC에서 사용자가 허용한 23:59 KST 하루 1회 조회만 가능. 게임 접속이 종료될 수 있습니다."
        else -> "수동 확인 · " + entry.note.ifBlank { "개인 진행도 완료 증거 미확인" }
    }

    fun report(entries: List<Entry>): String = buildString {
        appendLine(serverGuidance)
        appendLine(mobileGuidance)
        appendLine("이 분류는 안내용입니다. 기존 Todoist 제목·날짜·반복·하위 작업을 변경하지 않습니다.")
        for (section in groups) {
            appendLine("\n$section")
            for (entry in entries.filter { group(it) == section }) {
                appendLine("• ${entry.title}\n  ${description(entry)}")
            }
        }
        appendLine("\n$bannerGuidance")
    }
}
