package com.verlox.carinakeprix.app

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import java.net.HttpURLConnection
import java.net.URL

class CarinaOnboardingActivity : AppCompatActivity() {
  override fun onCreate(savedInstanceState: Bundle?) {
    super.onCreate(savedInstanceState)
    setContentView(R.layout.activity_carina_onboarding)

    val input = findViewById<EditText>(R.id.serverUrlInput)
    val status = findViewById<TextView>(R.id.connectionStatus)
    val testButton = findViewById<Button>(R.id.testConnectionButton)
    val continueButton = findViewById<Button>(R.id.continueButton)

    testButton.setOnClickListener {
      val url = input.text?.toString()?.trim().orEmpty()
      if (url.isEmpty()) {
        status.text = "Enter your keprix server URL."
        return@setOnClickListener
      }
      CarinaServerConfig.saveServerUrl(this, url)
      val health = CarinaServerConfig.healthCheckUrl(this)
      if (health == null) {
        status.text = "Invalid URL."
        return@setOnClickListener
      }
      Thread {
        val ok = try {
          val connection = URL(health).openConnection() as HttpURLConnection
          connection.requestMethod = "GET"
          connection.connectTimeout = 5000
          connection.responseCode in 200..299
        } catch (_: Exception) {
          false
        }
        runOnUiThread {
          if (ok) {
            status.text = "Connected. Server URL saved."
            continueButton.isEnabled = true
          } else {
            status.text = "Connection failed."
            continueButton.isEnabled = false
          }
        }
      }.start()
    }

    continueButton.setOnClickListener {
      startActivity(Intent(this, MainActivity::class.java))
      finish()
    }
  }
}
