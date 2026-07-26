package com.suoxingtuan.inspector.ui.screens.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.ui.components.AppIcon
import com.suoxingtuan.inspector.ui.theme.*

@Composable
fun SettingsScreen(
    onNavigateBack: () -> Unit,
    onNavigateToProfileEdit: () -> Unit,
    onNavigateToPasswordChange: () -> Unit,
    onLogout: () -> Unit
) {
    var notifyMaster by remember { mutableStateOf(true) }
    var taskRemind by remember { mutableStateOf(true) }
    var teamInvite by remember { mutableStateOf(true) }
    var alertPush by remember { mutableStateOf(true) }
    var systemNotice by remember { mutableStateOf(true) }
    var darkMode by remember { mutableStateOf(false) }
    var cacheSize by remember { mutableStateOf("2.3 MB") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
    ) {
        // Nav bar
        Row(
            Modifier
                .fillMaxWidth()
                .padding(start = 19.dp)
                .height(35.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                Modifier.size(35.dp).clip(RoundedCornerShape(50)).clickable { onNavigateBack() },
                contentAlignment = Alignment.Center
            ) {
                Text("‹", fontSize = 28.sp, color = TextPrimary, fontWeight = FontWeight.Light,
                    modifier = Modifier.offset(y = (-2).dp)
                )
            }
            Text("设置", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = TextPrimary,
                modifier = Modifier.padding(start = 8.dp))
        }

        Column(
            Modifier
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 17.dp, vertical = 10.dp)
        ) {
            // 账号与安全
            SettingsSection("账号与安全") {
                SettingsItem("个人资料", onClick = onNavigateToProfileEdit)
                SettingsItem("修改密码", onClick = onNavigateToPasswordChange)
                SettingsItem("账号绑定", hint = "手机号 138****1234", onClick = {})
            }

            // 通知设置
            SettingsSection("通知设置") {
                SwitchItem("消息通知", checked = notifyMaster, onToggle = { notifyMaster = it })
                SwitchItem("任务提醒", checked = taskRemind, onToggle = { taskRemind = it })
                SwitchItem("团队邀请", checked = teamInvite, onToggle = { teamInvite = it })
                SwitchItem("告警推送", checked = alertPush, onToggle = { alertPush = it })
                SwitchItem("系统公告", checked = systemNotice, onToggle = { systemNotice = it }, last = true)
            }

            // 通用设置
            SettingsSection("通用设置") {
                SettingsItem("语言切换", hint = "简体中文", onClick = {})
                SettingsItem("缓存清理", hint = cacheSize, onClick = {
                    cacheSize = "0 KB"
                })
                SwitchItem("深色模式", checked = darkMode, onToggle = { darkMode = it }, last = true)
            }

            // 关于
            SettingsSection("关于") {
                SettingsItem("版本号", hint = "v1.0.0")
                SettingsItem("检查更新", badge = "最新", onClick = {})
                SettingsItem("用户协议", onClick = {})
                SettingsItem("隐私政策", last = true, onClick = {})
            }

            // 退出登录
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(vertical = 8.dp)
                    .shadow(4.dp, RoundedCornerShape(12.dp))
                    .clip(RoundedCornerShape(12.dp))
                    .background(Color.White)
                    .clickable { onLogout() }
                    .padding(15.dp),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically
            ) {
                AppIcon("log-out", Modifier.size(18.dp), tint = Color(0xFFEF4444))
                Spacer(Modifier.width(8.dp))
                Text("退出登录", fontSize = 16.sp, color = Error)
            }
            Spacer(Modifier.height(30.dp))
        }
    }
}

@Composable
private fun SettingsSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(modifier = Modifier.padding(bottom = 24.dp)) {
        Text(title, fontSize = 14.sp, color = TextTertiary, modifier = Modifier.padding(start = 4.dp, bottom = 8.dp))
        Column(
            Modifier
                .shadow(4.dp, RoundedCornerShape(12.dp))
                .clip(RoundedCornerShape(12.dp))
                .background(Color.White)
        ) {
            content()
        }
    }
}

@Composable
private fun SettingsItem(
    label: String, hint: String? = null, badge: String? = null,
    last: Boolean = false, onClick: (() -> Unit)? = null
) {
    val clickMod = if (onClick != null) Modifier.clickable { onClick() } else Modifier
    Row(
        Modifier
            .fillMaxWidth()
            .then(clickMod)
            .padding(15.dp)
            .then(if (!last) Modifier.border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp)) else Modifier),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, fontSize = 16.sp, color = TextPrimary, modifier = Modifier.weight(1f))
        if (badge != null) {
            Text(badge, fontSize = 12.sp, color = Color(0xFF10B981),
                modifier = Modifier
                    .background(Color(0xFFECFDF5), RoundedCornerShape(10.dp))
                    .padding(horizontal = 8.dp, vertical = 2.dp)
            )
        }
        if (hint != null) {
            Text(hint, fontSize = 14.sp, color = TextTertiary)
        }
        if (onClick != null || hint != null || badge != null) {
            Spacer(Modifier.width(8.dp))
            AppIcon("chevron-right", Modifier.size(11.dp), tint = Color(0xFFD1D5DB))
        }
    }
}

@Composable
private fun SwitchItem(
    label: String, checked: Boolean, onToggle: (Boolean) -> Unit, last: Boolean = false
) {
    Row(
        Modifier
            .fillMaxWidth()
            .padding(15.dp)
            .then(if (!last) Modifier.border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp)) else Modifier),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, fontSize = 16.sp, color = TextPrimary, modifier = Modifier.weight(1f))
        Switch(
            checked = checked,
            onCheckedChange = onToggle,
            colors = SwitchDefaults.colors(
                checkedThumbColor = Color.White,
                checkedTrackColor = Color(0xFF3B82F6)
            )
        )
    }
}
