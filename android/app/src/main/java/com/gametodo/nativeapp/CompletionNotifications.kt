package com.gametodo.nativeapp

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build

object CompletionNotifications {
    private const val CHANNEL = "cipherlink_completed_tasks_v1"
    fun show(context: Context, title: String, occurrence: String) {
        if (Build.VERSION.SDK_INT >= 33 && context.checkSelfPermission(
                Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) return
        val manager = context.getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel(CHANNEL, "Todoist 완료 알림",
            NotificationManager.IMPORTANCE_HIGH).apply {
            description = "완료가 승인된 할 일의 이름을 팝업으로 표시합니다."
            lockscreenVisibility = Notification.VISIBILITY_PRIVATE
        })
        val open = PendingIntent.getActivity(context, 0, Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val notification = Notification.Builder(context, CHANNEL)
            .setSmallIcon(android.R.drawable.checkbox_on_background)
            .setContentTitle("할 일 완료: $title")
            .setContentText("Todoist에서 완료 처리했습니다.")
            .setStyle(Notification.BigTextStyle().bigText("$title\nTodoist에서 완료 처리했습니다."))
            .setVisibility(Notification.VISIBILITY_PRIVATE)
            .setContentIntent(open).setAutoCancel(true).setOnlyAlertOnce(true).build()
        manager.notify(occurrence.hashCode(), notification)
    }
}
