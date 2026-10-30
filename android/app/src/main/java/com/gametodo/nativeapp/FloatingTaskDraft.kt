package com.gametodo.nativeapp

import java.time.LocalDate
import java.util.UUID

/** One explicit user action; the same identity is retained across network retries. */
data class FloatingTaskDraft(val title: String, val date: String, val repeat: String,
    val project: String, val section: String, val label: String, val requestId: String = UUID.randomUUID().toString()) {
    fun validate() {
        require(title.isNotBlank() && title.length<=500) {"할 일 이름을 1~500자로 입력해 주세요"}
        require(runCatching {LocalDate.parse(date)}.isSuccess) {"날짜를 선택해 주세요"}
        require(repeat.length<=150 && !repeat.contains('\n')) {"반복 규칙을 150자 이내로 입력해 주세요"}
        require(project.isNotBlank() && section.isNotBlank()) {"프로젝트와 섹션을 선택해 주세요"}
        require(label.isNotBlank()) {"연결된 게임 라벨이 필요합니다"}
        require(runCatching {UUID.fromString(requestId)}.isSuccess) {"추가 요청을 다시 열어 주세요"}
    }
}
