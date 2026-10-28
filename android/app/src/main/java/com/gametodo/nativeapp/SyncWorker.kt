package com.gametodo.nativeapp

import android.content.Context
import android.content.SharedPreferences
import androidx.work.Constraints
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.NetworkType
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.Worker
import androidx.work.WorkerParameters
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.ExistingWorkPolicy
import androidx.work.WorkInfo
import androidx.work.WorkManager
import java.util.concurrent.TimeUnit

/** PC 없이 자체 자동 동기화. 반복 확인은 사용자가 선택한 ON/OFF 및 간격에 따른다. */
class SyncWorker(context: Context, parameters: WorkerParameters) : Worker(context, parameters) {
    override fun doWork(): Result {
        // 이미 실행 대기 중이던 작업도 OFF 전환 후에는 API 요청을 하지 않는다.
        if (!isEnabled(applicationContext)) return Result.success()
        return try {
            if (!TodoistAuth(applicationContext).isConnected()) return Result.success()
            val api = TodoistApi(applicationContext)
            val now = System.currentTimeMillis()
            MobileBannerSync(applicationContext).run(api, now)
            AccountSync(applicationContext).runOnce(api, now)
            Result.success()
        } catch (_: Exception) {
            // 서비스 오류는 다음 주기에서 다시 확인하되 사용자 데이터를 임의 완료하지 않는다.
            Result.success()
        }
    }

    companion object {
        private const val PERIODIC_KEY = "gametodo_banner_expiry" // 구버전 WorkManager 고유 ID 유지
        private const val LAUNCH_KEY = "gametodo_launch_check"
        private const val STORE = "gametodo_auto_check_settings_v1"
        private const val ENABLED = "enabled"
        private const val INTERVAL = "interval_minutes"
        private fun prefs(context: Context): SharedPreferences =
            context.getSharedPreferences(STORE, Context.MODE_PRIVATE)

        fun hasStoredEnabled(context: Context): Boolean = prefs(context).contains(ENABLED)
        /** 구버전 마이그레이션 중에는 기존 게임 실행 시 1회 확인 동작을 보존한다. */
        fun isEnabled(context: Context): Boolean = prefs(context).getBoolean(ENABLED, true)
        fun intervalMinutes(context: Context): Int =
            AutoCheckIntervals.normalize(prefs(context).getInt(INTERVAL, 15))

        /**
         * 구버전은 설정 상태를 저장하지 않고 WorkManager에만 주기 작업을 등록했다.
         * 기존 예약을 취소하거나 켜버리지 않도록, 최초 설정 화면에서 그 상태를 비동기로 가져온다.
         */
        fun restoreLegacy(context: Context, onReady: (Boolean) -> Unit) {
            if (hasStoredEnabled(context)) { onReady(isEnabled(context)); return }
            val appContext = context.applicationContext
            val manager = WorkManager.getInstance(appContext)
            val future = manager.getWorkInfosForUniqueWork(PERIODIC_KEY)
            future.addListener({
                val existing = try {
                    future.get().any { it.state == WorkInfo.State.ENQUEUED ||
                        it.state == WorkInfo.State.RUNNING || it.state == WorkInfo.State.BLOCKED }
                } catch (_: Exception) { // 상태 조회 오류 때에는 기존 예약을 임의로 끄지 않는다.
                    onReady(isEnabled(appContext))
                    return@addListener
                }
                val stored = prefs(appContext)
                if (!stored.contains(ENABLED)) stored.edit().putBoolean(ENABLED, existing).apply()
                onReady(isEnabled(appContext))
            }, appContext.mainExecutor)
        }

        /** 게임 시작 자동 조회도 OFF면 예약하지 않는다. 수동 '지금 동기화'는 별개. */
        fun checkOnce(context: Context) {
            if (!isEnabled(context)) return
            val request = OneTimeWorkRequestBuilder<SyncWorker>()
                .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
                .build()
            WorkManager.getInstance(context).enqueueUniqueWork(LAUNCH_KEY, ExistingWorkPolicy.KEEP, request)
        }

        fun setInterval(context: Context, minutes: Int) {
            prefs(context).edit().putInt(INTERVAL, AutoCheckIntervals.normalize(minutes)).apply()
            if (isEnabled(context)) setEnabled(context, true)
        }

        fun setEnabled(context: Context, enabled: Boolean) {
            // 먼저 저장하므로 이미 실행 대기 중인 Worker도 새 상태를 따르게 된다.
            prefs(context).edit().putBoolean(ENABLED, enabled).apply()
            val manager = WorkManager.getInstance(context)
            if (!enabled) {
                manager.cancelUniqueWork(PERIODIC_KEY)
                manager.cancelUniqueWork(LAUNCH_KEY)
                return
            }
            val request = PeriodicWorkRequestBuilder<SyncWorker>(
                intervalMinutes(context).toLong(), TimeUnit.MINUTES
            ).setConstraints(Constraints.Builder()
                .setRequiredNetworkType(NetworkType.CONNECTED).build()).build()
            manager.enqueueUniquePeriodicWork(PERIODIC_KEY, ExistingPeriodicWorkPolicy.UPDATE, request)
        }
    }
}
