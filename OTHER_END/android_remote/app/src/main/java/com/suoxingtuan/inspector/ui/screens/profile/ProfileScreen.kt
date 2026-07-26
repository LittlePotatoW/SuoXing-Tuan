package com.suoxingtuan.inspector.ui.screens.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.ui.components.AppIcon
import com.suoxingtuan.inspector.ui.theme.*

@Composable
fun ProfileScreen(
    onNavigateToEdit: () -> Unit,
    onNavigateToRecords: () -> Unit,
    onNavigateToNotification: () -> Unit,
    onNavigateToSettings: () -> Unit,
    onNavigateToFeedback: () -> Unit,
    onNavigateToTeam: () -> Unit,
    onLogout: () -> Unit
) {
    val scrollState = rememberScrollState()

    // Mock data
    val profile = remember { mutableStateMapOf("nickname" to "张伟", "intro" to "隧道巡检工程师", "status" to "online") }
    val teamMembers = remember {
        mutableStateListOf(
            mapOf("id" to "1", "name" to "张伟", "role" to "owner", "status" to "online"),
            mapOf("id" to "2", "name" to "李明", "role" to "member", "status" to "online"),
            mapOf("id" to "3", "name" to "王强", "role" to "member", "status" to "busy"),
            mapOf("id" to "4", "name" to "赵丽", "role" to "member", "status" to "offline"),
            mapOf("id" to "5", "name" to "陈峰", "role" to "member", "status" to "online")
        )
    }
    var notifyCount by remember { mutableIntStateOf(3) }
    var showAddMember by remember { mutableStateOf(false) }
    var searchPhone by remember { mutableStateOf("") }

    val statusInfo = when (profile["status"]) {
        "online" -> Triple("online", "在线", AccentMint)
        "busy" -> Triple("busy", "忙碌", AccentOrange)
        else -> Triple("offline", "离线", TextTertiary)
    }

    Column(Modifier.fillMaxSize().background(BgPage)) {
        // Nav bar
        Row(
            Modifier.fillMaxWidth().padding(start = 23.dp).height(35.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text("我的", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = TextPrimary)
        }

        Column(
            Modifier.verticalScroll(scrollState).padding(start = 19.dp, end = 19.dp, top = 15.dp)
        ) {
            // User card
            Column(
                Modifier
                    .fillMaxWidth()
                    .shadow(8.dp, RoundedCornerShape(16.dp))
                    .clip(RoundedCornerShape(16.dp))
                    .background(Color.White)
                    .padding(19.dp)
            ) {
                // Main row: avatar + info + edit
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
                    // Avatar
                    Box(Modifier.size(61.dp)) {
                        Box(
                            Modifier.size(61.dp).clip(CircleShape)
                                .background(Brush.linearGradient(listOf(Color(0xFFE0E7FF), Color(0xFFC7D2FE)))),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(profile["nickname"]?.firstOrNull()?.toString() ?: "张",
                                fontSize = 27.sp, fontWeight = FontWeight.SemiBold, color = BrandBlue)
                        }
                        // Camera badge
                        Box(
                            Modifier
                                .align(Alignment.BottomEnd).offset(x = 2.dp, y = 2.dp)
                                .size(21.dp).clip(CircleShape)
                                .background(BrandBlue).border(2.dp, SolidColor(Color.White), CircleShape),
                            contentAlignment = Alignment.Center
                        ) { AppIcon("camera", Modifier.size(10.dp), tint = Color.White) }
                    }

                    Spacer(Modifier.width(13.dp))

                    // User info
                    Column(Modifier.weight(1f)) {
                        Text(profile["nickname"] ?: "", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = TextPrimary, lineHeight = 22.sp)
                        Text(profile["intro"] ?: "", fontSize = 14.sp, color = TextSecondary, modifier = Modifier.padding(top = 4.dp))
                        Row(
                            Modifier.padding(top = 10.dp), verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Row(
                                Modifier.clip(RoundedCornerShape(12.dp))
                                    .background(if (statusInfo.first == "busy") Color(0xFFFFFBEB) else BgModule)
                                    .padding(horizontal = 9.dp, vertical = 3.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Box(Modifier.size(6.dp).clip(CircleShape).background(statusInfo.third))
                                Spacer(Modifier.width(4.dp))
                                Text(statusInfo.second, fontSize = 14.sp, color = statusInfo.third)
                            }
                            Text("15:38 已同步", fontSize = 14.sp, color = TextTertiary)
                        }
                    }

                    // Edit arrow
                    Box(Modifier.size(29.dp).clip(CircleShape).clickable { onNavigateToEdit() }, contentAlignment = Alignment.Center) {
                        AppIcon("chevron-right", Modifier.size(16.dp), tint = TextTertiary)
                    }
                }

                // Stats row
                Row(
                    Modifier.fillMaxWidth().padding(top = 17.dp)
                        .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp)),
                    horizontalArrangement = Arrangement.SpaceEvenly
                ) {
                    StatItem("今日任务", "2", "个", BrandBlue)
                    StatItem("负责区段", "隧道 B 区", null, Color(0xFF7C5CED))
                    OnlineStatItem("在线时长", "2", "h", "36", "m", AccentMint)
                }
            }

            Spacer(Modifier.height(24.dp))

            // Team section
            Row(
                Modifier.fillMaxWidth().padding(start = 4.dp, bottom = 8.dp),
                horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically
            ) {
                Text("我的团队", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                Row(verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.clickable { onNavigateToTeam() }) {
                    Text("${teamMembers.size} 位成员", fontSize = 14.sp, color = TextTertiary)
                    Text(" ›", fontSize = 16.sp, color = TextTertiary)
                }
            }

            Row(
                Modifier
                    .fillMaxWidth()
                    .shadow(6.dp, RoundedCornerShape(16.dp))
                    .clip(RoundedCornerShape(16.dp))
                    .background(Color.White)
                    .padding(horizontal = 19.dp, vertical = 15.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                // Show first 2 members
                teamMembers.take(2).forEach { m ->
                    MemberAvatar(m["name"] ?: "", m["role"] ?: "", m["status"] ?: "")
                }
                if (teamMembers.size > 2) {
                    Box(
                        Modifier.size(31.dp).clip(CircleShape).background(BgModule).border(2.dp, SolidColor(Color.White), CircleShape),
                        contentAlignment = Alignment.Center
                    ) { Text("+${teamMembers.size - 2}", fontSize = 12.sp, color = TextTertiary) }
                }
                // Add button
                Box(
                    Modifier.size(31.dp).clip(CircleShape)
                        .border(1.dp, SolidColor(Color(0xFFC5CAD6)), CircleShape)
                        .background(Color(0xFFFAFBFF))
                        .clickable { showAddMember = true },
                    contentAlignment = Alignment.Center
                ) { Text("+", fontSize = 18.sp, color = TextTertiary, fontWeight = FontWeight.Light) }
            }

            Spacer(Modifier.height(24.dp))

            // Menu card
            Column(
                Modifier
                    .fillMaxWidth()
                    .shadow(4.dp, RoundedCornerShape(12.dp))
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.White)
            ) {
                MenuRow("file-text", Color(0xFF4F73C2), "检测记录", onClick = onNavigateToRecords)
                MenuRow("bell", Color(0xFFF3B616), "通知", badge = notifyCount.toString(), onClick = onNavigateToNotification)
                MenuRow("settings", TextSecondary, "设置", onClick = onNavigateToSettings)
                MenuRow("help-circle", Color(0xFF14B8A6), "帮助与反馈", onClick = onNavigateToFeedback)
                MenuRow("info", Color(0xFF6366F1), "关于我们", last = true)
            }

            Spacer(Modifier.height(24.dp))

            // Logout
            Row(
                Modifier
                    .fillMaxWidth()
                    .shadow(4.dp, RoundedCornerShape(12.dp))
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.White)
                    .clickable { onLogout() }
                    .padding(15.dp),
                horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically
            ) {
                AppIcon("log-out", Modifier.size(18.dp), tint = Error)
                Spacer(Modifier.width(8.dp))
                Text("退出登录", fontSize = 16.sp, color = Error)
            }
            Spacer(Modifier.height(30.dp))
        }
    }

    // Add member dialog
    if (showAddMember) {
        AddMemberDialog(
            phone = searchPhone,
            onPhoneChange = { if (it.length <= 11) searchPhone = it },
            onDismiss = { showAddMember = false },
            onConfirm = { showAddMember = false; searchPhone = "" }
        )
    }
}

@Composable
private fun RowScope.StatItem(label: String, value: String, unit: String?, iconColor: Color) {
    Column(Modifier.weight(1f)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(29.dp).clip(RoundedCornerShape(10.dp)).background(BgModule), contentAlignment = Alignment.Center) {
                AppIcon("clipboard", Modifier.size(15.dp), tint = iconColor)
            }
            Spacer(Modifier.width(10.dp))
            Column {
                Text(label, fontSize = 14.sp, color = TextSecondary)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(value, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                    if (unit != null) Text(unit, fontSize = 14.sp, color = TextSecondary)
                }
            }
        }
    }
}

@Composable
private fun RowScope.OnlineStatItem(label: String, h: String, hUnit: String, m: String, mUnit: String, color: Color) {
    Column(Modifier.weight(1f)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(29.dp).clip(RoundedCornerShape(10.dp)).background(BgModule), contentAlignment = Alignment.Center) {
                AppIcon("gauge", Modifier.size(15.dp), tint = color)
            }
            Spacer(Modifier.width(10.dp))
            Column {
                Text(label, fontSize = 14.sp, color = TextSecondary)
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(h, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                    Text(hUnit, fontSize = 14.sp, color = TextSecondary)
                    Text(m, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                    Text(mUnit, fontSize = 14.sp, color = TextSecondary)
                }
            }
        }
    }
}

@Composable
private fun MemberAvatar(name: String, role: String, status: String) {
    val statusColor = when (status) {
        "online" -> AccentMint; "busy" -> AccentOrange; else -> TextTertiary
    }
    Column(
        modifier = Modifier.padding(end = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            Modifier.size(31.dp).clip(CircleShape)
                .background(Brush.linearGradient(listOf(Color(0xFFEEF0FF), Color(0xFFDCD8FF)))),
            contentAlignment = Alignment.Center
        ) { Text(name.first().toString(), fontSize = 15.sp, color = Color(0xFF202332)) }
        Spacer(Modifier.height(4.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(6.dp).clip(CircleShape).background(statusColor))
            if (role == "owner") {
                Text("负责人", fontSize = 12.sp, color = Color(0xFF5B68C8),
                    modifier = Modifier.padding(start = 4.dp)
                        .background(Color(0xFFEEF1FF), RoundedCornerShape(8.dp)).padding(horizontal = 8.dp, vertical = 3.dp))
            }
        }
    }
}

@Composable
private fun MenuRow(
    icon: String, iconTint: Color, label: String,
    badge: String? = null, last: Boolean = false,
    onClick: (() -> Unit)? = null
) {
    Row(
        Modifier
            .fillMaxWidth()
            .then(if (onClick != null) Modifier.clickable { onClick() } else Modifier)
            .padding(15.dp)
            .then(if (!last) Modifier.border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp)) else Modifier),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(Modifier.size(35.dp).clip(RoundedCornerShape(8.dp)).background(BgModule), contentAlignment = Alignment.Center) {
            AppIcon(icon, Modifier.size(18.dp), tint = iconTint)
        }
        Spacer(Modifier.width(12.dp))
        Text(label, fontSize = 16.sp, color = TextPrimary, modifier = Modifier.weight(1f))
        if (badge != null) {
            Box(
                Modifier.clip(RoundedCornerShape(10.dp)).background(Error).padding(horizontal = 5.dp),
                contentAlignment = Alignment.Center
            ) { Text(badge, fontSize = 11.sp, fontWeight = FontWeight.Medium, color = Color.White) }
            Spacer(Modifier.width(8.dp))
        }
        AppIcon("chevron-right", Modifier.size(12.dp), tint = Color(0xFFD1D5DB))
    }
}

@Composable
private fun AddMemberDialog(
    phone: String, onPhoneChange: (String) -> Unit,
    onDismiss: () -> Unit, onConfirm: () -> Unit
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("添加团队成员", Modifier.fillMaxWidth(),
            textAlign = androidx.compose.ui.text.style.TextAlign.Center) },
        text = {
            OutlinedTextField(
                value = phone, onValueChange = onPhoneChange,
                placeholder = { Text("请输入成员手机号") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
        },
        confirmButton = { TextButton(onClick = onConfirm) { Text("确认添加", color = BrandBlue) } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("取消") } }
    )
}
