package com.gametodo.nativeapp

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Android Keystore의 AES/GCM 키로 OAuth 토큰 JSON을 암호화하여 저장. */
class SecureTokens(private val context: Context) {
    private val prefs = context.getSharedPreferences("gametodo_secrets", Context.MODE_PRIVATE)
    private val alias = "gametodo_oauth_v1"

    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey(alias, null) as? SecretKey)?.let { return it }
        val gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        gen.init(KeyGenParameterSpec.Builder(alias,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256).build())
        return gen.generateKey()
    }

    @Synchronized fun save(raw: String) = saveNamed("oauth", raw)

    /** 계정별 자격 증명도 동일한 Android Keystore에서 암호화하되, 별도 키로 관리. */
    @Synchronized fun saveNamed(slot: String, raw: String) {
        require(slot.matches(Regex("[a-z0-9_]{1,50}")))
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val blob = cipher.iv + cipher.doFinal(raw.toByteArray(Charsets.UTF_8))
        // commit: refresh_token 회전 직후 중단될 때도 최신 자격 증명을 디스크에 반영.
        check(prefs.edit().putString(slot, Base64.encodeToString(blob, Base64.NO_WRAP)).commit())
    }

    @Synchronized fun load(): String? = loadNamed("oauth")

    @Synchronized fun loadNamed(slot: String): String? {
        require(slot.matches(Regex("[a-z0-9_]{1,50}")))
        val saved = prefs.getString(slot, null) ?: return null
        return try {
            val blob = Base64.decode(saved, Base64.NO_WRAP)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, blob.copyOfRange(0, 12)))
            String(cipher.doFinal(blob.copyOfRange(12, blob.size)), Charsets.UTF_8)
        } catch (_: Exception) { null }
    }

    @Synchronized fun clear() { prefs.edit().remove("oauth").commit() }
    @Synchronized fun clearNamed(slot: String) { prefs.edit().remove(slot).commit() }
}
