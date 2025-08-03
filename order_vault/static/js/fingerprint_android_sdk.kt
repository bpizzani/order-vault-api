package com.rediim.sdk

import android.content.Context
import android.content.SharedPreferences
import android.util.DisplayMetrics
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.util.Locale
import java.util.TimeZone
import java.util.UUID
import android.os.Build
import com.thumbmarkjs.thumbmark_android.Thumbmark

object RediimFingerprint {

    interface Callback {
        fun onSuccess(visitorId: String, localSessionId: String)
        fun onError(error: String)
    }

    fun sendFingerprint(
        context: Context,
        apiKey: String,
        clientId: String,
        userId: Int?,
        callback: Callback
    ) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val prefs = context.getSharedPreferences("rediim_sdk_prefs", Context.MODE_PRIVATE)
                var storedId = prefs.getString("rediim_fingerprint", null)
                val sessionId = getOrCreateSessionId(prefs)

                if (!storedId.isNullOrBlank()) {
                    withContext(Dispatchers.Main) {
                        callback.onSuccess(storedId, sessionId)
                    }
                    return@launch
                }

                val deviceInfo = collectDeviceInfo(context, sessionId)
                val tb_fingerprint = Thumbmark.id(context).toString()

                val json = JSONObject(deviceInfo)
                val body = json.toString().toRequestBody("application/json".toMediaTypeOrNull())
                val request = Request.Builder()
                    .url("https://api.rediim.com/api/fingerprint")
                    .post(body)
                    .addHeader("Content-Type", "application/json")
                    .addHeader("X-API-KEY", apiKey)
                    .addHeader("X-CLIENT-ID", clientId)
                    .addHeader("user_identifier_client", userId?.toString() ?: "")
                    .build()

                val response = OkHttpClient().newCall(request).execute()
                val responseData = response.body?.string()

                if (response.isSuccessful && responseData != null) {
                    val responseJson = JSONObject(responseData)
                    //val visitorId = responseJson.optString("visitorId")
                    val visitorId = tb_fingerprint
                    prefs.edit().putString("rediim_fingerprint", visitorId).apply()
                    withContext(Dispatchers.Main) {
                        callback.onSuccess(visitorId, sessionId)
                    }
                } else {
                    withContext(Dispatchers.Main) {
                        callback.onError("API error: ${response.code} ${response.message}")
                    }
                }
            } catch (e: Exception) {
                Log.e("RediimSDK", "Error sending fingerprint", e)
                withContext(Dispatchers.Main) {
                    callback.onError(e.message ?: "Unknown error")
                }
            }
        }
    }

    private fun getOrCreateSessionId(prefs: SharedPreferences): String {
        var id = prefs.getString("local_session_id", null)
        if (id == null) {
            id = UUID.randomUUID().toString()
            prefs.edit().putString("local_session_id", id).apply()
        }
        return id
    }

    private fun collectDeviceInfo(context: Context, sessionId: String): Map<String, Any?> {
        val dm: DisplayMetrics = context.resources.displayMetrics
        return mapOf(
            "userAgent" to System.getProperty("http.agent"),
            "platform" to "Android",
            "screenRes" to "${dm.widthPixels}x${dm.heightPixels}",
            "colorDepth" to 32,
            "timezone" to TimeZone.getDefault().id,
            "languages" to Locale.getDefault().toString(),
            "hardwareConcurrency" to Runtime.getRuntime().availableProcessors(),
            "cookiesEnabled" to false,
            "touchSupport" to true,
            "sessionStorage" to false,
            "webGLFingerprint" to "not_applicable",
            "canvasFingerprint" to "not_applicable",
            "cookies" to "",
            "sessionId" to sessionId,
            "bot_framework" to false,
            "local_session_id" to sessionId,
            "device" to Build.DEVICE,
            "model" to Build.MODEL,
            "manufacturer" to Build.MANUFACTURER,
            "brand" to Build.BRAND,
            "product" to Build.PRODUCT,
            "board" to Build.BOARD,
            "hardware" to Build.HARDWARE,
            "bootloader" to Build.BOOTLOADER,
            "fingerprint" to Build.FINGERPRINT,  // Android build fingerprint (not your app's)
            "radioVersion" to Build.getRadioVersion(),
        )
    }
}
