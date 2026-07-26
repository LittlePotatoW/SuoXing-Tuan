package com.suoxingtuan.inspector.ui.screens.notification

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.ui.components.AppIcon
import com.suoxingtuan.inspector.ui.theme.*

// Message model
data class Message(
    val id: String, val type: String, val title: String, val desc: String,
    val time: String, var read: Boolean, var state: String? = null
)

@Composable
fun NotificationScreen(
    onNavigateBack: () -> Unit,
    onNavigateToTask: () -> Unit,
    onNavigateToInspection: () -> Unit
) {
    var activeTab by remember { mutableStateOf("all") }
    val tabs = listOf("all" to "全部", "task" to "任务通知", "invite" to "团队邀请", "alert" to "告警提醒", "system" to "系统公告")

    val messages = remember {
        mutableStateListOf(
            Message("1", "task", "新巡检任务已派发", "隧道B区巡检任务，计划今日 14:00 执行，请准时前往。", "10分钟前", false),
            Message("i1", "invite", "组队邀请", "张伟 邀请您加入 隧道巡检A组", "25分钟前", false, "pending"),
            Message("2", "alert", "小车电量低于 20%", "巡检车 A-03 电量仅剩 18%，请及时充电以保证下次任务正常执行。", "32分钟前", false),
            Message("3", "task", "任务执行完成", "隧道B区巡检任务已于 11:45 完成，发现 4 项问题，请查看报告。", "1小时前", false),
            Message("4", "system", "三维模型已更新", "隧道B区三维重建模型已更新至 v2.3，新增 K12+300 至 K12+500 区段数据。", "2小时前", true),
            Message("i2", "invite", "组队邀请", "李明 邀请您加入 设备检修组", "昨天", true, "accepted"),
            Message("5", "alert", "信号连接异常", "巡检车 A-03 在 K12+420 处信号中断超过 30 秒，已自动切换至本地控制模式。", "3小时前", true),
            Message("i3", "invite", "组队邀请", "王强 邀请您加入 应急响应组", "2天前", true, "rejected")
        )
    }

    val filtered = remember(activeTab, messages.toList()) {
        if (activeTab == "all") messages.toList() else messages.filter { it.type == activeTab }
    }

    fun markAllRead() { messages.forEach { it.read = true } }

    Column(Modifier.fillMaxSize().background(BgPage)) {
        // Nav bar
        Row(
            Modifier.fillMaxWidth().padding(start = 19.dp).height(35.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(Modifier.size(35.dp).clip(RoundedCornerShape(50)).clickable { onNavigateBack() }, contentAlignment = Alignment.Center) {
                Text("‹", fontSize = 28.sp, color = TextPrimary, fontWeight = FontWeight.Light, modifier = Modifier.offset(y = (-2).dp))
            }
            Text("通知", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = TextPrimary, modifier = Modifier.padding(start = 8.dp))
            Spacer(Modifier.weight(1f))
            Text("全部已读", fontSize = 14.sp, color = BrandBlue,
                modifier = Modifier.clickable { markAllRead() })
        }

        // Tabs
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 17.dp, vertical = 10.dp),
            horizontalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            tabs.forEach { (key, label) ->
                val active = activeTab == key
                Box(
                    Modifier
                        .clip(RoundedCornerShape(20.dp))
                        .background(if (active) BrandBlue else Color.White)
                        .border(0.5.dp, SolidColor(if (active) BrandBlue else BorderLight), RoundedCornerShape(20.dp))
                        .clickable { activeTab = key }
                        .padding(horizontal = 12.dp, vertical = 7.dp)
                ) {
                    Text(label, fontSize = 14.sp, color = if (active) Color.White else TextSecondary)
                }
            }
        }

        // List
        LazyColumn(
            Modifier.fillMaxSize().padding(horizontal = 17.dp),
            contentPadding = PaddingValues(bottom = 24.dp)
        ) {
            if (filtered.isEmpty()) {
                item {
                    Column(Modifier.fillMaxWidth().padding(top = 96.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        AppIcon("bell", Modifier.size(31.dp), tint = Color(0xFFD1D5DB))
                        Text("暂无通知", fontSize = 14.sp, color = TextTertiary, modifier = Modifier.padding(top = 12.dp))
                    }
                }
            }
            items(filtered, key = { it.id }) { msg ->
                MessageCard(
                    msg = msg,
                    onAccept = {
                        val m = messages.find { it.id == msg.id }; if (m != null) { m.state = "accepted"; m.read = true }
                    },
                    onReject = {
                        val m = messages.find { it.id == msg.id }; if (m != null) { m.state = "rejected"; m.read = true }
                    },
                    onClick = {
                        val m = messages.find { it.id == msg.id }; m?.read = true
                        when (msg.type) {
                            "task" -> { msg.read = true; onNavigateToTask() }
                            "alert" -> { msg.read = true; onNavigateToInspection() }
                        }
                    }
                )
            }
        }
    }
}

@Composable
private fun MessageCard(
    msg: Message,
    onAccept: () -> Unit,
    onReject: () -> Unit,
    onClick: () -> Unit
) {
    val iconName = when (msg.type) { "task" -> "clipboard"; "alert" -> "alert-triangle"; "system" -> "info"; else -> "user-plus" }
    val iconColor = when (msg.type) { "task" -> Color(0xFF3B82F6); "alert" -> Color(0xFFEF4444); "system" -> Color(0xFF8B5CF6); else -> Color(0xFF8B5CF6) }
    val iconBg = when (msg.type) { "task" -> Color(0xFFEFF6FF); "alert" -> Color(0xFFFEF2F2); "system" -> Color(0xFFF5F3FF); else -> Color(0xFFF5F3FF) }

    Column(
        Modifier
            .fillMaxWidth()
            .padding(bottom = 8.dp)
            .shadow(4.dp, RoundedCornerShape(12.dp))
            .clip(RoundedCornerShape(12.dp))
            .background(Color.White)
            .clickable { onClick() }
            .padding(14.dp)
    ) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
            // Icon
            Box(
                Modifier.size(31.dp).clip(RoundedCornerShape(8.dp)).background(iconBg),
                contentAlignment = Alignment.Center
            ) { AppIcon(iconName, Modifier.size(17.dp), tint = iconColor) }
            Spacer(Modifier.width(10.dp))

            Column(Modifier.weight(1f)) {
                // Title row
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(msg.title, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary,
                        maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f, fill = false))
                    if (!msg.read && msg.state == null) {
                        Box(Modifier.size(7.dp).clip(CircleShape).background(BrandBlue).padding(start = 6.dp))
                    }
                    if (msg.state == "accepted") {
                        Text("已接受", fontSize = 12.sp, color = Color(0xFF059669),
                            modifier = Modifier.background(Color(0xFFECFDF5), RoundedCornerShape(8.dp)).padding(horizontal = 7.dp, vertical = 2.dp))
                    }
                    if (msg.state == "rejected") {
                        Text("已拒绝", fontSize = 12.sp, color = Color(0xFF9CA3AF),
                            modifier = Modifier.background(Color(0xFFF3F4F6), RoundedCornerShape(8.dp)).padding(horizontal = 7.dp, vertical = 2.dp))
                    }
                }

                // Desc
                Text(msg.desc, fontSize = 14.sp, color = TextSecondary, lineHeight = 20.sp,
                    maxLines = 2, overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.padding(vertical = 4.dp))

                // Time
                Text(msg.time, fontSize = 14.sp, color = TextTertiary)

                // Invite actions
                if (msg.type == "invite" && msg.state == "pending") {
                    Row(Modifier.fillMaxWidth().padding(top = 8.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Box(
                            Modifier.weight(1f).height(31.dp).clip(RoundedCornerShape(10.dp)).background(BrandBlue).clickable { onAccept() },
                            contentAlignment = Alignment.Center
                        ) { Text("接受", fontSize = 14.sp, color = Color.White) }
                        Box(
                            Modifier.weight(1f).height(31.dp).clip(RoundedCornerShape(10.dp)).background(BorderLight).clickable { onReject() },
                            contentAlignment = Alignment.Center
                        ) { Text("拒绝", fontSize = 14.sp, color = TextSecondary) }
                    }
                }
            }

            if (msg.type != "invite") {
                AppIcon("chevron-right", Modifier.size(11.dp).padding(top = 4.dp), tint = Color(0xFFD1D5DB))
            }
        }
    }
}
