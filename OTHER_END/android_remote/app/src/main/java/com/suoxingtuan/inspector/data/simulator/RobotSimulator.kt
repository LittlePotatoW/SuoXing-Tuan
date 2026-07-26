package com.suoxingtuan.inspector.data.simulator

import com.suoxingtuan.inspector.data.model.LatLng
import com.suoxingtuan.inspector.data.repository.RobotRepository
import kotlinx.coroutines.*
import kotlin.math.*

/**
 * Robot GPS simulator — mirrors robotSimulator.ts.
 * Auto mode: follows polyline path. Manual mode: 8-direction free movement.
 */
object RobotSimulator {
    private const val M_PER_DEG_LAT = 111000.0
    private const val TICK_MS = 1000L
    private const val DEFAULT_AUTO_SPEED_MS = 1.5
    private const val ENCODER_PULSE_RATE = 65
    private const val STEER_CENTER = 150
    private const val BATTERY_MIN = 5

    private val HEADING_ANGLES = mapOf(
        "forward" to 0, "backward" to 180, "left" to 270, "right" to 90,
        "forward_left" to 315, "forward_right" to 45,
        "backward_left" to 225, "backward_right" to 135
    )

    private var timer: Job? = null
    private val scope = CoroutineScope(Dispatchers.Default + SupervisorJob())
    private var pathIndex = 0
    private var forward = true
    private var progress = 0.0
    private var elapsed = 0
    private var pulseCount = 0

    private fun distMeters(a: LatLng, b: LatLng): Double {
        val dLat = (b.latitude - a.latitude) * M_PER_DEG_LAT
        val dLng = (b.longitude - a.longitude) * M_PER_DEG_LAT * cos((a.latitude + b.latitude) / 2 * (PI / 180))
        return sqrt(dLat * dLat + dLng * dLng)
    }

    private fun interpolate(a: LatLng, b: LatLng, t: Double): LatLng {
        return LatLng(a.latitude + (b.latitude - a.latitude) * t, a.longitude + (b.longitude - a.longitude) * t)
    }

    private suspend fun tick() {
        elapsed++
        val rs = RobotRepository.currentState()
        if (rs.controlDirection.isNotEmpty()) tickManual() else tickAuto()
        tickTelemetry()
        tickBattery()
    }

    private fun tickManual() {
        val rs = RobotRepository.currentState()
        val dir = rs.controlDirection
        val head = HEADING_ANGLES[dir] ?: 0
        val rad = head * PI / 180
        val speedMs = rs.controlSpeed
        val dist = speedMs
        val cosLat = cos(rs.latitude * PI / 180)

        val dLat = dist * cos(rad) / M_PER_DEG_LAT
        val dLng = dist * sin(rad) / (M_PER_DEG_LAT * cosLat)
        RobotRepository.updateLocation(rs.latitude + dLat, rs.longitude + dLng, head.toDouble(), speedMs * RobotRepository.MS_TO_KMH)
        RobotRepository.updateStatus(mileage = rs.mileage + dist / 1000, fix = 3, satellites = 12, locSrc = "gps")
        pulseCount += (speedMs * 100).toInt()
        RobotRepository.updateTelemetry(pulseCount, pulseCount + (0..5).random(), STEER_CENTER)
    }

    private fun tickAuto() {
        val rs = RobotRepository.currentState()
        val path = rs.path
        if (path.size < 2) return
        val nextIndex = if (forward) pathIndex + 1 else pathIndex - 1
        if (nextIndex < 0 || nextIndex >= path.size) { forward = !forward; pathIndex = if (forward) 0 else path.size - 1; return }
        val from = path[pathIndex]; val to = path[nextIndex]
        val segDist = distMeters(from, to)
        val speedMs = if (rs.controlDirection.isNotEmpty()) rs.controlSpeed else DEFAULT_AUTO_SPEED_MS
        val stepRatio = if (segDist > 0) speedMs / segDist else 0.0
        progress += stepRatio
        if (progress >= 1) { progress = 0.0; pathIndex = nextIndex }
        val pos = interpolate(from, to, minOf(progress, 1.0))
        val rawHeading = (atan2((to.longitude - from.longitude) * (if (forward) 1 else -1), (to.latitude - from.latitude) * (if (forward) 1 else -1)) * 180 / PI + 90)
        val heading = ((rawHeading % 360) + 360) % 360
        RobotRepository.updateLocation(pos.latitude, pos.longitude, heading, speedMs * RobotRepository.MS_TO_KMH)
        RobotRepository.updateStatus(mileage = rs.mileage + speedMs / 1000)
    }

    private fun tickTelemetry() {
        val rs = RobotRepository.currentState()
        pulseCount += (rs.controlSpeed * ENCODER_PULSE_RATE).toInt()
        val enc1 = pulseCount
        val isLeft = rs.controlDirection.contains("left"); val isRight = rs.controlDirection.contains("right")
        val enc2 = pulseCount + (if (isLeft) -20 else if (isRight) 20 else (0..5).random())
        val steer = if (isLeft) 120 else if (isRight) 180 else STEER_CENTER
        RobotRepository.updateTelemetry(enc1, enc2, steer)
        if (elapsed % 30 == 0) {
            val signals = listOf("强", "强", "强", "中", "弱")
            RobotRepository.updateStatus(signal = signals.random())
        }
    }

    private fun tickBattery() {
        val rs = RobotRepository.currentState()
        if (elapsed % 60 == 0 && rs.battery > BATTERY_MIN) RobotRepository.updateStatus(battery = rs.battery - 1)
    }

    fun start() {
        if (timer != null) return
        val rs = RobotRepository.currentState()
        RobotRepository.setConnected(true)
        RobotRepository.setMode("simulation")
        RobotRepository.updateStatus(status = "running")
        RobotRepository.updateControlSpeed(DEFAULT_AUTO_SPEED_MS)
        pathIndex = 0; progress = 0.0; forward = true; elapsed = 0
        timer = scope.launch {
            while (isActive) { tick(); delay(TICK_MS) }
        }
    }

    fun stop() {
        timer?.cancel(); timer = null
        RobotRepository.setConnected(false)
        RobotRepository.updateControlSpeed(0.0)
        RobotRepository.updateStatus(status = "online")
        RobotRepository.updateTelemetry(0, 0, 150)
    }

    fun setDirection(dir: String) {
        val rs = RobotRepository.currentState()
        if (dir == "stop" || dir.isEmpty()) {
            RobotRepository.updateControlDirection("", 0.0)
            RobotRepository.updateTelemetry(pulseCount, pulseCount, 150)
        } else {
            val speed = 0.8 + Math.random() * 0.6
            RobotRepository.updateControlDirection(dir, speed * 3.6)
        }
    }
}
