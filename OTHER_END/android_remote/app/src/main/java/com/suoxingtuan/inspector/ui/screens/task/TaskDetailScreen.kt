package com.suoxingtuan.inspector.ui.screens.task

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import com.suoxingtuan.inspector.data.model.RiskLevel
import com.suoxingtuan.inspector.data.model.IssueStatus
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.ui.components.AppIcon
import com.suoxingtuan.inspector.ui.theme.*

@Composable
fun TaskDetailScreen(
    onNavigateBack: () -> Unit,
    taskId: String = "0"
) {
    val taskName = "隧道B区巡检"
    val taskStatus = "running" // pending, running, done, cancelled
    val progress = 62
    val distDone = 1.2f
    val distTotal = 1.8f
    val robotPos = "K12+350"
    val robotBattery = 78
    val robotSpeed = 1.2f
    val robotStatus = "online"

    val statusConfig = when (taskStatus) {
        "pending" -> Triple("待执行", Color(0xFFFFF7ED), Color(0xFFC2410C))
        "running" -> Triple("执行中", Color(0xFFEFF6FF), Color(0xFF1D4ED8))
        "done" -> Triple("已完成", Color(0xFFECFDF5), Color(0xFF047857))
        else -> Triple("已取消", Color(0xFFF3F4F6), Color(0xFF6B7280))
    }

    Column(Modifier.fillMaxSize().background(BgPage)) {
        // Nav bar
        Row(Modifier.fillMaxWidth().padding(start = 19.dp).height(35.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(35.dp).clip(RoundedCornerShape(50)).clickable { onNavigateBack() }, contentAlignment = Alignment.Center) {
                Text("‹", fontSize = 28.sp, color = TextPrimary, fontWeight = FontWeight.Light, modifier = Modifier.offset(y = (-2).dp))
            }
            Text("任务详情", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = TextPrimary, modifier = Modifier.padding(start = 8.dp))
        }

        Column(Modifier.verticalScroll(rememberScrollState()).padding(horizontal = 17.dp)) {
            // Status badge
            Box(
                Modifier.fillMaxWidth().padding(vertical = 10.dp).clip(RoundedCornerShape(20.dp))
                    .background(statusConfig.second).padding(vertical = 5.dp),
                contentAlignment = Alignment.Center
            ) { Text(statusConfig.first, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = statusConfig.third) }

            // Info card
            val infoCardMod = Modifier.fillMaxWidth().padding(bottom = 10.dp).shadow(4.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp)).background(Color.White).padding(15.dp)
            Column(infoCardMod) {
                Text("基本信息", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary, modifier = Modifier.padding(bottom = 10.dp))
                InfoRow("任务编号", "TD-2026-0711-001")
                InfoRow("任务名称", taskName)
                InfoRow("检测区域", "隧道B区")
                InfoRow("计划时间", "2026-07-11 14:00", last = true)
            }

            // Progress card
            Column(infoCardMod) {
                Text("任务进度", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary, modifier = Modifier.padding(bottom = 10.dp))
                Row(verticalAlignment = Alignment.Bottom) {
                    Text("$progress", fontSize = 26.sp, color = BrandBlue, fontWeight = FontWeight.SemiBold)
                    Text("%", fontSize = 16.sp, color = BrandBlue, modifier = Modifier.padding(bottom = 2.dp))
                }
                Box(Modifier.fillMaxWidth().padding(vertical = 8.dp).height(6.dp).clip(RoundedCornerShape(3.dp)).background(BorderLight)) {
                    Box(Modifier.fillMaxHeight().fillMaxWidth(progress / 100f).clip(RoundedCornerShape(3.dp)).background(BrandBlue))
                }
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("已完成", fontSize = 14.sp, color = TextTertiary)
                    Text("${distDone}km / ${distTotal}km", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                }
            }

            // Robot status
            Column(infoCardMod) {
                Text("机器人状态", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary, modifier = Modifier.padding(bottom = 10.dp))
                Row(Modifier.fillMaxWidth()) {
                    RobotStatusItem("当前位置", robotPos, Modifier.weight(1f))
                    RobotStatusItem("电量", "$robotBattery%", Modifier.weight(1f), valueColor = AccentMint)
                }
                Row(Modifier.fillMaxWidth().padding(top = 7.dp)) {
                    RobotStatusItem("速度", "${robotSpeed} m/s", Modifier.weight(1f))
                    RobotStatusItem("状态", "在线", Modifier.weight(1f), valueColor = AccentMint)
                }
            }

            // Related issues
            Column(infoCardMod) {
                Text("关联问题", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary, modifier = Modifier.padding(bottom = 8.dp))
                listOf(
                    Triple(RiskLevel.high, "K12+350处衬砌裂缝", IssueStatus.pending),
                    Triple(RiskLevel.medium, "排水沟堵塞", IssueStatus.reviewed)
                ).forEach { (risk, title, status) ->
                    Row(
                        Modifier.fillMaxWidth().padding(vertical = 7.dp).border(0.5.dp, SolidColor(Color(0xFFF5F5F5)), RoundedCornerShape(0.dp)),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(Modifier.size(8.dp).clip(CircleShape).background(risk.color))
                        Text(title, fontSize = 14.sp, color = TextPrimary, modifier = Modifier.weight(1f).padding(start = 7.dp))
                        Text(status.label, fontSize = 10.sp, color = status.textColor,
                            modifier = Modifier.clip(RoundedCornerShape(10.dp)).background(status.bg).padding(horizontal = 8.dp, vertical = 3.dp))
                    }
                }
            }
            Spacer(Modifier.height(70.dp))
        }

        // Bottom action bar
        Row(
            Modifier.fillMaxWidth()
                .background(Color.White).border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp))
                .padding(horizontal = 17.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            ActionButton("暂停", Color(0xFFFFF7ED), Color(0xFFC2410C)) {}
            ActionButton("结束", Color(0xFFFEF2F2), Color(0xFFDC2626)) {}
            Box(Modifier.weight(1f).height(42.dp).clip(RoundedCornerShape(8.dp)).background(BrandBlue).clickable { },
                contentAlignment = Alignment.Center) { Text("查看报告", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = Color.White) }
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String, last: Boolean = false) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 7.dp).then(if (!last) Modifier.border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp)) else Modifier),
        horizontalArrangement = Arrangement.SpaceBetween
    ) { Text(label, fontSize = 14.sp, color = TextSecondary); Text(value, fontSize = 14.sp, color = TextPrimary, textAlign = androidx.compose.ui.text.style.TextAlign.End) }
}

@Composable
private fun RobotStatusItem(label: String, value: String, modifier: Modifier, valueColor: Color = TextPrimary) {
    Column(modifier.padding(vertical = 7.dp)) {
        Text(label, fontSize = 14.sp, color = TextTertiary)
        Text(value, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = valueColor)
    }
}

@Composable
private fun RowScope.ActionButton(label: String, bg: Color, textColor: Color, onClick: () -> Unit) {
    Box(
        Modifier.weight(1f).height(42.dp).clip(RoundedCornerShape(8.dp)).background(bg).border(0.5.dp, SolidColor(textColor.copy(0.3f)), RoundedCornerShape(8.dp)).clickable { onClick() },
        contentAlignment = Alignment.Center
    ) { Text(label, fontSize = 16.sp, color = textColor) }
}
