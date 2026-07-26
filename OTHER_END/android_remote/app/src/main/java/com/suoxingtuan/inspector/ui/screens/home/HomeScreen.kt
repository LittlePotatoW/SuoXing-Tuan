package com.suoxingtuan.inspector.ui.screens.home

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.ui.components.AppIcon
import com.suoxingtuan.inspector.ui.theme.*
import com.suoxingtuan.inspector.data.repository.RobotRepository
import com.suoxingtuan.inspector.data.repository.TaskRepository

@Composable
fun HomeScreen(
    onNavigateToControl: () -> Unit,
    onNavigateToTask: (String) -> Unit
) {
    val scrollState = rememberScrollState()

    // Real robot state
    val robotState by RobotRepository.state.collectAsState()
    val task = TaskRepository.currentTask

    // Connection pulse animation
    val pulseAnim = rememberInfiniteTransition(label = "conn")
    val pulseAlpha by pulseAnim.animateFloat(0.5f, 1f, infiniteRepeatable(tween(1200, easing = FastOutSlowInEasing), RepeatMode.Reverse), label = "pulse")

    // Derived from real state
    val batteryLevel = robotState.battery
    val controlSpeed = robotState.speedKmh
    val mileage = robotState.mileage
    val taskName = task.name
    val taskProgress = task.progress
    val robotStatusText = if (robotState.connected) robotState.mode else "未连接"
    val robotStatusColor = if (robotState.connected) Success else TextTertiary

    Column(Modifier.fillMaxSize().background(BgPage)) {
        // Nav bar
        Column(
            Modifier.fillMaxWidth().padding(start = 23.dp).padding(top = 4.dp)
        ) {
            Text("智能巡检", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = TextPrimary, lineHeight = 24.sp)
            Text("巡检机器人管理平台", fontSize = 12.sp, color = TextTertiary, lineHeight = 16.sp)
        }

        Column(Modifier.verticalScroll(scrollState).padding(bottom = 16.dp)) {
            // Connection status bar
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 17.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Box(
                    modifier = Modifier
                        .size(7.dp).clip(CircleShape)
                        .background(Success.copy(alpha = pulseAlpha))
                        .shadow(5.dp, CircleShape, ambientColor = Success.copy(0.5f), spotColor = Success.copy(0.5f))
                )
                Spacer(Modifier.width(6.dp))
                Text(if (robotState.connected) "已连接 — ${robotState.mode}模式" else "未连接", fontSize = 11.sp, color = if (robotState.connected) Success else TextTertiary)
            }

            // Map placeholder card
            Box(
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 17.dp)
                    .height(326.dp)
                    .shadow(6.dp, RoundedCornerShape(12.dp))
                    .clip(RoundedCornerShape(12.dp))
                    .background(BgCool),
                contentAlignment = Alignment.Center
            ) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    AppIcon("map", Modifier.size(48.dp), tint = BrandBlue.copy(0.3f))
                    Text("地图视图", fontSize = 14.sp, color = TextTertiary, modifier = Modifier.padding(top = 8.dp))
                }
            }

            // Dashboard (2-column grid)
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 17.dp, vertical = 12.dp),
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                // Left: Vehicle card
                Column(
                    Modifier
                        .weight(1f)
                        .shadow(4.dp, RoundedCornerShape(12.dp))
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color.White)
                        .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(12.dp))
                        .padding(15.dp)
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("巡检车 A-03", fontSize = 15.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary, modifier = Modifier.weight(1f))
                        Row(Modifier.clip(RoundedCornerShape(8.dp)).background(Color(0xFFECFDF5)).padding(horizontal = 6.dp, vertical = 2.dp), verticalAlignment = Alignment.CenterVertically) {
                            Box(Modifier.size(5.dp).clip(CircleShape).background(Success))
                            Text("运行中", fontSize = 10.sp, color = Success, modifier = Modifier.padding(start = 3.dp))
                        }
                    }
                    // Rover image placeholder
                    Box(Modifier.fillMaxWidth().padding(vertical = 8.dp).height(108.dp).clip(RoundedCornerShape(8.dp)).background(BgModule), contentAlignment = Alignment.Center) {
                        androidx.compose.foundation.Image(
                            painter = androidx.compose.ui.res.painterResource(com.suoxingtuan.inspector.R.drawable.rover),
                            contentDescription = null, modifier = Modifier.fillMaxWidth().height(108.dp)
                        )
                    }
                    Row(Modifier.fillMaxWidth().border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp)).padding(top = 4.dp), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            AppIcon("tool", Modifier.size(14.dp), tint = Color(0xFF9AA3AD)); Text("自动中", fontSize = 12.sp, color = TextSecondary, modifier = Modifier.padding(start = 3.dp))
                        }
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            AppIcon("gauge", Modifier.size(14.dp), tint = Color(0xFF9AA3AD)); Text("${controlSpeed} m/s", fontSize = 12.sp, color = TextSecondary, modifier = Modifier.padding(start = 3.dp))
                        }
                    }
                }

                // Right: Status card
                Column(
                    Modifier
                        .weight(1f)
                        .shadow(4.dp, RoundedCornerShape(12.dp))
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color.White)
                        .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(12.dp))
                        .padding(15.dp)
                ) {
                    Text("设备状态", fontSize = 15.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary, modifier = Modifier.padding(bottom = 8.dp))
                    StatusRow("battery", Color(0xFF88C37B), "电量状态", "$batteryLevel%", "正常")
                    StatusRow("signal", Color(0xFF5D90DF), "网络状态", robotState.signal, if (robotState.connected) "已连接" else "未连接")
                    StatusRow("radio", AccentMint, "环境状态", "良好")
                    StatusRow("crosshair", BrandBlue, "行驶里程", "${mileage}km")
                }
            }

            // Task card
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 17.dp)
                    .shadow(4.dp, RoundedCornerShape(12.dp))
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.White)
                    .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(12.dp))
                    .clickable { onNavigateToTask("0") }
                    .padding(horizontal = 12.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column(Modifier.weight(1f)) {
                    Text("当前任务", fontSize = 13.sp, color = TextTertiary)
                    Text(taskName, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary, modifier = Modifier.padding(top = 2.dp))
                    Spacer(Modifier.height(8.dp))
                    // Progress bar
                    Box(Modifier.fillMaxWidth().height(6.dp).clip(RoundedCornerShape(3.dp)).background(BorderLight)) {
                        Box(Modifier.fillMaxHeight().fillMaxWidth(taskProgress / 100f).clip(RoundedCornerShape(6.dp)).background(BrandBlue))
                    }
                    Text("$taskProgress%", fontSize = 12.sp, color = BrandBlue, modifier = Modifier.padding(top = 4.dp))
                }
                Text("›", fontSize = 24.sp, color = TextTertiary, fontWeight = FontWeight.Light, modifier = Modifier.padding(start = 8.dp))
            }

            // Enter control button
            Box(
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 17.dp, vertical = 12.dp)
                    .height(50.dp)
                    .shadow(4.dp, RoundedCornerShape(8.dp))
                    .clip(RoundedCornerShape(8.dp))
                    .background(BrandBlue)
                    .clickable { onNavigateToControl() },
                contentAlignment = Alignment.Center
            ) {
                Text("进入遥控", fontSize = 18.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
            }

            Spacer(Modifier.height(8.dp))
        }
    }
}

@Composable
private fun StatusRow(icon: String, iconColor: Color, label: String, value: String, sub: String = "") {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 8.dp).border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp)),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(Modifier.size(21.dp).clip(CircleShape).background(BgModule), contentAlignment = Alignment.Center) {
            AppIcon(icon, Modifier.size(17.dp), tint = iconColor)
        }
        Spacer(Modifier.width(8.dp))
        Column {
            Text(label, fontSize = 14.sp, color = TextTertiary)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(value, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                if (sub.isNotEmpty()) Text(sub, fontSize = 12.sp, color = TextTertiary)
            }
        }
    }
}
