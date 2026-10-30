package com.gametodo.nativeapp

import org.json.JSONArray
import org.json.JSONObject

/** The exact payload used by creation and by its retry; contains no authentication. */
object FloatingTaskRequest {
    fun command(draft:FloatingTaskDraft):JSONObject {
        draft.validate()
        val due=JSONObject().put("date",draft.date)
        if(draft.repeat.isNotBlank()) due.put("string",draft.repeat).put("is_recurring",true).put("lang","ko")
        val args=JSONObject().put("content",draft.title.trim()).put("labels",JSONArray(listOf(draft.label)))
            .put("project_id",draft.project).put("section_id",draft.section).put("due",due)
        return JSONObject().put("type","item_add")
            .put("uuid",SharedCommandIds.uuid5("item_add","floating-task:"+draft.requestId))
            .put("temp_id",SharedCommandIds.uuid5("floating-temp",draft.requestId)).put("args",args)
    }
}
