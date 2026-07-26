package com.suoxingtuan.inspector.util

import com.suoxingtuan.inspector.data.model.LatLng
import kotlin.math.*

/**
 * WGS-84 → GCJ-02 coordinate conversion.
 * Robot GPS reports WGS-84; Tencent Map needs GCJ-02.
 */
object CoordConvert {
    private const val PI = Math.PI
    private const val A = 6378245.0
    private const val EE = 0.00669342162296594323

    private fun transformLat(x: Double, y: Double): Double {
        var ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * sqrt(abs(x))
        ret += ((20.0 * sin(6.0 * x * PI) + 20.0 * sin(2.0 * x * PI)) * 2.0) / 3.0
        ret += ((20.0 * sin(y * PI) + 40.0 * sin((y / 3.0) * PI)) * 2.0) / 3.0
        ret += ((160.0 * sin((y / 12.0) * PI) + 320.0 * sin((y * PI) / 30.0)) * 2.0) / 3.0
        return ret
    }

    private fun transformLng(x: Double, y: Double): Double {
        var ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * sqrt(abs(x))
        ret += ((20.0 * sin(6.0 * x * PI) + 20.0 * sin(2.0 * x * PI)) * 2.0) / 3.0
        ret += ((20.0 * sin(x * PI) + 40.0 * sin((x / 3.0) * PI)) * 2.0) / 3.0
        ret += ((150.0 * sin((x / 12.0) * PI) + 300.0 * sin((x / 30.0) * PI)) * 2.0) / 3.0
        return ret
    }

    private fun outOfChina(lat: Double, lng: Double): Boolean {
        return lng < 72.004 || lng > 137.8347 || lat < 0.8293 || lat > 55.8271
    }

    fun wgs84ToGcj02(lat: Double, lng: Double): LatLng {
        if (outOfChina(lat, lng)) return LatLng(lat, lng)
        var dLat = transformLat(lng - 105.0, lat - 35.0)
        var dLng = transformLng(lng - 105.0, lat - 35.0)
        val radLat = (lat / 180.0) * PI
        var magic = sin(radLat)
        magic = 1 - EE * magic * magic
        val sqrtMagic = sqrt(magic)
        dLat = (dLat * 180.0) / (((A * (1 - EE)) / (magic * sqrtMagic)) * PI)
        dLng = (dLng * 180.0) / ((A / sqrtMagic) * cos(radLat) * PI)
        return LatLng(lat + dLat, lng + dLng)
    }

    fun convertPathToGcj02(points: List<LatLng>): List<LatLng> {
        return points.map { wgs84ToGcj02(it.latitude, it.longitude) }
    }
}
