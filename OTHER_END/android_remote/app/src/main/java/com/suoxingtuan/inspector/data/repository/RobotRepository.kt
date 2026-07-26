package com.suoxingtuan.inspector.data.repository

import com.suoxingtuan.inspector.data.model.LatLng
import com.suoxingtuan.inspector.data.model.RobotState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Robot state — module-level reactive singleton (mirrors robotStore.ts) */
object RobotRepository {
    const val MS_TO_KMH = 3.6

    private val _state = MutableStateFlow(RobotState())
    val state: StateFlow<RobotState> = _state.asStateFlow()

    fun updateLocation(lat: Double, lng: Double, cog: Double? = null, spdKmh: Double? = null) {
        _state.value = _state.value.copy(
            latitude = lat, longitude = lng,
            heading = cog ?: _state.value.heading,
            speedKmh = spdKmh ?: _state.value.speedKmh,
            controlSpeed = if (spdKmh != null) (spdKmh / MS_TO_KMH).let { String.format("%.2f", it).toDouble() } else _state.value.controlSpeed
        )
    }

    fun updateTelemetry(enc1: Int, enc2: Int, steer: Int) {
        _state.value = _state.value.copy(enc1 = enc1, enc2 = enc2, steer = steer)
    }

    fun updateStatus(
        battery: Int? = null, signal: String? = null, status: String? = null,
        mileage: Double? = null, fix: Int? = null, satellites: Int? = null, locSrc: String? = null
    ) {
        var s = _state.value
        battery?.let { s = s.copy(battery = it) }
        signal?.let { s = s.copy(signal = it) }
        status?.let { s = s.copy(status = it) }
        mileage?.let { s = s.copy(mileage = it) }
        fix?.let { s = s.copy(fix = it) }
        satellites?.let { s = s.copy(satellites = it) }
        locSrc?.let { s = s.copy(locSrc = it) }
        _state.value = s
    }

    fun setMode(mode: String) { _state.value = _state.value.copy(mode = mode) }
    fun setConnected(v: Boolean) { _state.value = _state.value.copy(connected = v) }

    fun currentState(): RobotState = _state.value

    fun updateControlDirection(dir: String, speedKmh: Double = 0.0) {
        _state.value = _state.value.copy(controlDirection = dir, controlSpeed = speedKmh, speedKmh = speedKmh)
    }

    fun updatePeerId(peerId: String) {
        _state.value = _state.value.copy(peerId = peerId)
    }

    fun updateControlSpeed(speed: Double) {
        _state.value = _state.value.copy(controlSpeed = speed)
    }

    fun setRoomId(roomId: String) {
        _state.value = _state.value.copy(roomId = roomId)
    }
}
