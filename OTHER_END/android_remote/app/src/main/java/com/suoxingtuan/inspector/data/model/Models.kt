package com.suoxingtuan.inspector.data.model

import androidx.compose.ui.graphics.Color

// ---- Auth ----
data class StoredUser(
    val phone: String,
    val password: String,
    val nickname: String,
    val createdAt: String
)

data class AuthResult(val success: Boolean, val message: String)

// ---- Robot State ----
data class RobotState(
    val connected: Boolean = false,
    val mode: String = "simulation",
    val roomId: String = "car001",
    val peerId: String = "",
    val robotId: String = "A-03",
    val latitude: Double = 39.9923,
    val longitude: Double = 116.3265,
    val speedKmh: Double = 0.0,
    val heading: Double = 0.0,
    val altitude: Double = 50.0,
    val satellites: Int = 0,
    val fix: Int = 0,
    val locSrc: String = "gps",
    val enc1: Int = 0,
    val enc2: Int = 0,
    val steer: Int = 150,
    val battery: Int = 85,
    val signal: String = "强",
    val status: String = "running",
    val mileage: Double = 2.8,
    val controlDirection: String = "",
    val controlSpeed: Double = 0.0,
    val path: List<LatLng> = listOf(
        LatLng(39.9908, 116.3248),
        LatLng(39.9923, 116.3265),
        LatLng(39.9941, 116.3282),
        LatLng(39.9935, 116.3301)
    ),
    val nextPoint: String = "K12+450"
)

data class LatLng(val latitude: Double, val longitude: Double)

// ---- Task ----
data class TaskData(
    val id: String = "TD-2026-0711-001",
    val name: String = "隧道B区巡检",
    val area: String = "隧道B区 (K12+200 ~ K12+800)",
    val planStart: String = "2026-07-11 14:00",
    val planEnd: String = "2026-07-11 16:00",
    val status: String = "running",
    val progress: Int = 65,
    val doneDist: Double = 0.39,
    val totalDist: Double = 0.6,
    val robotPos: String = "K12+456",
    val robotBattery: Int = 78,
    val robotSpeed: Double = 1.2,
    val robotStatus: String = "运行中",
    val nextPoint: String = "消防通道 #2",
    val timeRemaining: String = "01:28:36",
    val issues: List<TaskIssue> = listOf(
        TaskIssue("i1", "裂缝宽度超标 3mm", "K12+350 拱顶", "#EF4444", "2026-07-11"),
        TaskIssue("i2", "渗漏水痕迹", "K12+400 侧墙", "#F2994A", "2026-07-11"),
        TaskIssue("i3", "扣件松动", "K12+420 左轨", "#8E8E8E", "2026-07-11")
    )
)

data class TaskIssue(
    val id: String, val title: String, val location: String,
    val riskColor: String, val date: String
)

// ---- Inspection ----
enum class RiskLevel(val label: String, val color: Color) {
    high("高", Color(0xFFDA1E28)),
    medium("中", Color(0xFFF2994A)),
    normal("低", Color(0xFF24A148))
}

enum class IssueStatus(val label: String, val bg: Color, val textColor: Color) {
    pending("待处理", Color(0xFFFFF7ED), Color(0xFFC2410C)),
    reviewed("已复核", Color(0xFFECFDF5), Color(0xFF059669)),
    high_risk("高风险", Color(0xFFFEF2F2), Color(0xFFDC2626)),
    normal("正常", Color(0xFFF1F1F1), Color(0xFF5F5F5F))
}

data class InspectionIssue(
    val id: String, val branch: String, val title: String,
    val location: String, val date: String, val risk: RiskLevel,
    val status: IssueStatus, val createdAt: String
)

data class DateGroup(val date: String, val issues: List<InspectionIssue>)

data class BranchDef(val key: String, val name: String, val icon: String)

// ---- Profile ----
data class ProfileData(
    val avatar: String = "",
    val nickname: String = "巡检员",
    val intro: String = "隧道检测工程师",
    val status: String = "online",
    val gender: String = "不公开"
)

data class TeamMember(
    val id: String, val name: String, val phone: String,
    val avatar: String, val status: String, val role: String
)

data class TeamInvitation(
    val id: String, val phone: String, val name: String,
    val createdAt: String, val status: String
)

// ---- SMS ----
data class SmsRecord(val code: String, val expireTime: Long, val phone: String)
data class SmsResult(val success: Boolean, val message: String)

// ---- Risk & Status config ----
data class RiskConfig(val label: String, val color: String)
data class StatusConfig(val label: String, val bg: String, val color: String)
data class StatusOption(val value: String, val label: String, val color: String)
