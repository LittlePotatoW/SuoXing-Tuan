package com.suoxingtuan.inspector.ui.screens.team

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.ui.components.AppIcon
import com.suoxingtuan.inspector.ui.theme.*

data class TeamMember(
    val id: String, val name: String, val role: String,
    val status: String, val phone: String = ""
)

data class TeamInvitation(
    val id: String, val name: String, val phone: String
)

@Composable
fun TeamScreen(
    onNavigateBack: () -> Unit
) {
    val members = remember {
        mutableStateListOf(
            TeamMember("1", "张伟", "owner", "online", "13800000001"),
            TeamMember("2", "李明", "member", "online"),
            TeamMember("3", "王强", "member", "busy"),
            TeamMember("4", "赵丽", "member", "offline"),
            TeamMember("5", "陈峰", "member", "online")
        )
    }
    val invites = remember {
        mutableStateListOf(TeamInvitation("i1", "新成员", "13900000000"))
    }
    var showAdd by remember { mutableStateOf(false) }
    var newPhone by remember { mutableStateOf("") }
    var actionTarget by remember { mutableStateOf<TeamMember?>(null) }

    val onlineCount = members.count { it.status == "online" }

    Column(Modifier.fillMaxSize().background(BgPage)) {
        // Nav bar
        Row(
            Modifier.fillMaxWidth().padding(start = 19.dp).height(35.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(Modifier.size(35.dp).clip(RoundedCornerShape(50)).clickable { onNavigateBack() },
                contentAlignment = Alignment.Center) {
                Text("‹", fontSize = 28.sp, color = TextPrimary, fontWeight = FontWeight.Light, modifier = Modifier.offset(y = (-2).dp))
            }
            Text("团队成员", fontSize = 18.sp, fontWeight = FontWeight.Medium, color = TextPrimary, modifier = Modifier.padding(start = 6.dp))
            Spacer(Modifier.weight(1f))
            Box(Modifier.size(35.dp).clip(CircleShape).clickable { showAdd = true }, contentAlignment = Alignment.Center) {
                AppIcon("plus-circle", Modifier.size(18.dp), tint = Color(0xFF3B82F6))
            }
        }

        // Stats
        Row(
            Modifier.fillMaxWidth().padding(start = 21.dp, top = 10.dp, bottom = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text("共 ${members.size} 人", fontSize = 14.sp, color = TextPrimary)
            Text("$onlineCount 人在线", fontSize = 12.sp, color = TextTertiary)
        }

        LazyColumn(
            Modifier.fillMaxSize().padding(horizontal = 17.dp),
            contentPadding = PaddingValues(bottom = 24.dp)
        ) {
            // Pending invites
            if (invites.isNotEmpty()) {
                item {
                    Text("待处理邀请（${invites.size}）", fontSize = 12.sp, color = TextTertiary,
                        modifier = Modifier.padding(start = 4.dp, bottom = 6.dp))
                }
                items(invites, key = { it.id }) { inv ->
                    InviteCard(inv)
                }
            }

            // Members
            items(members, key = { it.id }) { m ->
                MemberCard(
                    member = m,
                    onMoreClick = { actionTarget = m }
                )
            }
        }
    }

    // Add dialog
    if (showAdd) {
        AlertDialog(
            onDismissRequest = { showAdd = false },
            title = { Text("添加成员", Modifier.fillMaxWidth(), textAlign = androidx.compose.ui.text.style.TextAlign.Center) },
            text = {
                OutlinedTextField(value = newPhone, onValueChange = { if (it.length <= 11) newPhone = it },
                    placeholder = { Text("请输入成员手机号") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            },
            confirmButton = { TextButton(onClick = { showAdd = false; newPhone = "" }) { Text("确认添加") } },
            dismissButton = { TextButton(onClick = { showAdd = false }) { Text("取消") } }
        )
    }

    // Action sheet
    if (actionTarget != null) {
        AlertDialog(
            onDismissRequest = { actionTarget = null },
            title = null,
            text = {
                Column {
                    TextButton(onClick = { actionTarget = null }) { Text("查看资料") }
                    TextButton(onClick = {
                        members.removeAll { it.id == actionTarget?.id }
                        actionTarget = null
                    }) { Text("移除成员", color = Error) }
                    TextButton(onClick = { actionTarget = null }) { Text("取消", color = TextSecondary) }
                }
            },
            confirmButton = {}
        )
    }
}

@Composable
private fun InviteCard(inv: TeamInvitation) {
    Row(
        Modifier.fillMaxWidth().padding(bottom = 7.dp)
            .shadow(2.dp, RoundedCornerShape(12.dp))
            .clip(RoundedCornerShape(12.dp))
            .background(Color.White.copy(alpha = 0.75f))
            .padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(Modifier.size(35.dp).clip(CircleShape)
            .background(Brush.linearGradient(listOf(Color(0xFFFFF7ED), Color(0xFFFFEDD5)))),
            contentAlignment = Alignment.Center) {
            Text(inv.name.first().toString(), fontSize = 16.sp, color = Color(0xFF202332))
        }
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(inv.name, fontSize = 14.sp, color = TextPrimary)
            Text("${inv.phone.take(3)}****${inv.phone.takeLast(4)}", fontSize = 11.sp, color = TextSecondary)
        }
        Text("等待确认", fontSize = 10.sp, color = Color(0xFFC2410C),
            modifier = Modifier.background(Color(0xFFFFF7ED), RoundedCornerShape(8.dp)).padding(horizontal = 7.dp, vertical = 2.dp))
    }
}

@Composable
private fun MemberCard(member: TeamMember, onMoreClick: () -> Unit) {
    val statusColor = when (member.status) {
        "online" -> AccentMint; "busy" -> AccentOrange; else -> Color(0xFFB8BDC8)
    }
    val statusText = when (member.status) {
        "online" -> "在线"; "busy" -> "忙碌"; else -> "离线"
    }

    Row(
        Modifier.fillMaxWidth().padding(bottom = 7.dp)
            .shadow(2.dp, RoundedCornerShape(12.dp))
            .clip(RoundedCornerShape(12.dp))
            .background(Color.White)
            .padding(horizontal = 14.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(Modifier.size(35.dp).clip(CircleShape)
            .background(Brush.linearGradient(listOf(Color(0xFFEEF0FF), Color(0xFFDCD8FF)))),
            contentAlignment = Alignment.Center) {
            Text(member.name.first().toString(), fontSize = 16.sp, color = Color(0xFF202332))
        }
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(member.name, fontSize = 14.sp, color = TextPrimary)
                Spacer(Modifier.width(6.dp))
                if (member.role == "owner") {
                    Text("负责人", fontSize = 10.sp, color = Color(0xFF5B68C8),
                        modifier = Modifier.background(Color(0xFFEEF1FF), RoundedCornerShape(8.dp)).padding(horizontal = 7.dp, vertical = 2.dp))
                } else {
                    Text("成员", fontSize = 10.sp, color = TextTertiary,
                        modifier = Modifier.background(BorderLight, RoundedCornerShape(8.dp)).padding(horizontal = 7.dp, vertical = 2.dp))
                }
            }
            Row(Modifier.padding(top = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(6.dp).clip(CircleShape).background(statusColor))
                Spacer(Modifier.width(4.dp))
                Text(statusText, fontSize = 11.sp, color = TextSecondary)
            }
        }
        Box(Modifier.size(27.dp).clip(CircleShape).clickable { onMoreClick() }, contentAlignment = Alignment.Center) {
            AppIcon("more-horizontal", Modifier.size(14.dp), tint = Color(0xFF9CA3AF))
        }
    }
}
