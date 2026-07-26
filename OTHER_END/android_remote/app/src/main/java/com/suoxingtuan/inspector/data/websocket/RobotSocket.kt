package com.suoxingtuan.inspector.data.websocket

import com.suoxingtuan.inspector.data.repository.RobotRepository
import kotlinx.coroutines.*
import okhttp3.*
import java.util.concurrent.TimeUnit

/**
 * WebSocket communication layer — mirrors robotSocket.ts.
 * Protocol: room-based relay server at host:port/phone?room=<roomId>
 */
object RobotSocket {
    private const val MAX_RECONNECT = 5
    private var webSocket: WebSocket? = null
    private var reconnectAttempts = 0
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var pingJob: Job? = null
    private var reconnectJob: Job? = null

    // Direction map (8 directions)
    val DIR_MAP = mapOf(
        "forward" to "up", "backward" to "down", "left" to "left", "right" to "right",
        "forward_left" to "up_left", "forward_right" to "up_right",
        "backward_left" to "down_left", "backward_right" to "down_right"
    )

    fun connect(host: String) {
        val room = RobotRepository.currentState().roomId
        val protocol = if (host.startsWith("ws://") || host.startsWith("wss://")) "" else "ws://"
        val url = "$protocol$host/phone?room=$room"

        RobotRepository.setMode("realtime")
        val client = OkHttpClient.Builder().readTimeout(0, TimeUnit.MILLISECONDS).build()
        val request = Request.Builder().url(url).build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(ws: WebSocket, response: Response) {
                RobotRepository.setConnected(true)
                reconnectAttempts = 0
                startPing(ws)
            }
            override fun onMessage(ws: WebSocket, text: String) {
                handleMessage(text)
            }
            override fun onFailure(ws: WebSocket, t: Throwable, response: Response?) {
                println("[WS] error: ${t.message}")
            }
            override fun onClosed(ws: WebSocket, code: Int, reason: String) {
                RobotRepository.setConnected(false)
                webSocket = null
                stopPing()
                attemptReconnect(host)
            }
        })
    }

    fun disconnect() {
        stopPing()
        reconnectJob?.cancel()
        webSocket?.close(1000, "user disconnect")
        webSocket = null
        RobotRepository.setConnected(false)
    }

    fun sendCommand(dir: String) {
        val apiDir = if (dir == "stop") "stop" else (DIR_MAP[dir] ?: dir)
        val msg = """{"type":"ctrl","dir":"$apiDir","peerId":"${RobotRepository.currentState().peerId}","ts":${System.currentTimeMillis()}}"""
        webSocket?.send(msg)
    }

    private fun sendPing(ws: WebSocket) {
        ws.send("""{"type":"ping","peerId":"${RobotRepository.currentState().peerId}"}""")
    }

    fun sendLocConfig(interval: Int = 2000) {
        val msg = """{"type":"loc_cfg","peerId":"${RobotRepository.currentState().peerId}","interval":$interval,"src":["gps"]}"""
        webSocket?.send(msg)
    }

    private fun startPing(ws: WebSocket) {
        stopPing()
        pingJob = scope.launch {
            while (isActive) { sendPing(ws); delay(2000) }
        }
    }

    private fun stopPing() { pingJob?.cancel(); pingJob = null }

    private fun attemptReconnect(host: String) {
        if (reconnectAttempts >= MAX_RECONNECT) return
        reconnectAttempts++
        val delay = minOf(1000L * (1L shl reconnectAttempts), 30000L)
        reconnectJob = scope.launch { delay(delay); connect(host) }
    }

    private fun handleMessage(text: String) {
        try {
            val msg = org.json.JSONObject(text)
            when (msg.optString("type")) {
                "sys" -> handleSys(msg)
                "loc" -> handleLoc(msg)
                "tele" -> handleTele(msg)
            }
        } catch (_: Exception) {}
    }

    private fun handleSys(msg: org.json.JSONObject) {
        when (msg.optInt("code")) {
            1001 -> { RobotRepository.updatePeerId(msg.optString("peerId")); sendLocConfig(2000) }
            1002 -> RobotRepository.updateStatus(status = "offline")
        }
    }

    private fun handleLoc(msg: org.json.JSONObject) {
        val lat = if (msg.has("lat")) msg.optDouble("lat") else null
        val lon = if (msg.has("lon")) msg.optDouble("lon") else null
        if (lat != null && lon != null) RobotRepository.updateLocation(lat, lon, msg.optDouble("cog").takeIf { msg.has("cog") }, msg.optDouble("spd").takeIf { msg.has("spd") })
        RobotRepository.updateStatus(fix = msg.optInt("fix", 0), satellites = msg.optInt("sat", 0), locSrc = msg.optString("src", "gps"))
    }

    private fun handleTele(msg: org.json.JSONObject) {
        if (msg.has("enc1") && msg.has("enc2") && msg.has("steer"))
            RobotRepository.updateTelemetry(msg.optInt("enc1"), msg.optInt("enc2"), msg.optInt("steer"))
        if (msg.has("bat")) RobotRepository.updateStatus(battery = msg.optInt("bat"))
        if (msg.has("sig")) RobotRepository.updateStatus(signal = msg.optString("sig"))
    }
}
