@file:Suppress("DEPRECATION")

package com.verlox.carinakeprix.app

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

object CarinaServerConfig {
  private const val PREFS = "carina_server_config"
  private const val KEY_SERVER_URL = "server_url"

  private fun prefs(context: Context) =
    EncryptedSharedPreferences.create(
      context,
      PREFS,
      MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
      EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
      EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

  fun getServerUrl(context: Context): String? =
    prefs(context).getString(KEY_SERVER_URL, null)?.trim()?.ifBlank { null }

  fun saveServerUrl(context: Context, url: String) {
    prefs(context).edit().putString(KEY_SERVER_URL, url.trim()).apply()
  }

  fun healthCheckUrl(context: Context): String? =
    getServerUrl(context)?.trimEnd('/')?.plus("/api/health")
}
