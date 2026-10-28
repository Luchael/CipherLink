package com.gametodo.nativeapp

import java.io.IOException
import java.net.SocketTimeoutException
import java.util.concurrent.TimeoutException

/** Fixed error categories and bounded protocol numbers only; no remote error text. */
object SafeFailure {
    private val http = Regex("\\bHTTP[ =:]+([1-5][0-9]{2})\\b")
    private val provider = Regex("\\b(retcode|SKPORT code)=(-?[0-9]{1,9})\\b")

    fun describe(error: Exception): String {
        val kind = when (error) {
            is SocketTimeoutException, is TimeoutException -> "시간 초과"
            is IOException -> "네트워크 오류"
            is SecurityException -> "권한 오류"
            is IllegalArgumentException -> "입력·응답 형식 오류"
            else -> "조회 오류"
        }
        val message = error.message.orEmpty()
        val status = http.find(message)?.groupValues?.get(1)?.let { "HTTP $it" }
        val code = provider.find(message)?.let { match ->
            match.groupValues[2].toIntOrNull()?.let { "${match.groupValues[1]}=$it" }
        }
        val numbers = listOfNotNull(status, code).joinToString(" · ")
        return kind + if (numbers.isEmpty()) "" else " ($numbers)"
    }
}
