package com.suoxingtuan.inspector.ui.screens.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.ui.components.AppIcon
import com.suoxingtuan.inspector.ui.theme.*

@Composable
fun ProfileEditScreen(
    onNavigateBack: () -> Unit
) {
    var nickname by remember { mutableStateOf("张伟") }
    var intro by remember { mutableStateOf("隧道巡检工程师") }
    var gender by remember { mutableStateOf("男") }
    var status by remember { mutableStateOf("online") }
    var showGenderPicker by remember { mutableStateOf(false) }
    var showStatusPicker by remember { mutableStateOf(false) }

    val genders = listOf("男", "女", "不公开")
    val statusOptions = listOf(
        Triple("online", "在线", Color(0xFF7BC8A4)),
        Triple("busy", "忙碌", Color(0xFFF2994A)),
        Triple("offline", "离线", Color(0xFF8E8E8E))
    )
    val currentStatus = statusOptions.first { it.first == status }

    Column(
        Modifier.fillMaxSize().background(BgPage).verticalScroll(rememberScrollState())
    ) {
        // Avatar section
        Column(
            Modifier.fillMaxWidth().padding(top = 29.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Box(Modifier.size(77.dp).clip(CircleShape).background(BgModule), contentAlignment = Alignment.Center) {
                AppIcon("user", Modifier.size(27.dp), tint = TextPrimary)
                // Camera badge
                Box(
                    Modifier
                        .align(Alignment.BottomEnd)
                        .offset(x = 2.dp, y = 2.dp)
                        .size(23.dp)
                        .clip(CircleShape)
                        .background(Color(0xFF171717))
                        .border(2.dp, SolidColor(Color.White), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    AppIcon("camera", Modifier.size(12.dp), tint = Color.White)
                }
            }
            Text("点击更换头像", fontSize = 12.sp, color = TextTertiary, modifier = Modifier.padding(top = 9.dp))
        }

        // Form card
        Column(
            Modifier
                .fillMaxWidth()
                .padding(top = 23.dp, start = 23.dp, end = 23.dp)
                .shadow(6.dp, RoundedCornerShape(21.dp))
                .clip(RoundedCornerShape(21.dp))
                .background(Color.White)
                .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(21.dp))
        ) {
            // Nickname
            FormRow("昵称", border = true) {
                androidx.compose.foundation.text.BasicTextField(
                    value = nickname,
                    onValueChange = { if (it.length <= 12) nickname = it },
                    modifier = Modifier.fillMaxWidth().weight(1f),
                    textStyle = androidx.compose.ui.text.TextStyle(fontSize = 14.sp, color = TextPrimary, textAlign = TextAlign.End),
                    cursorBrush = SolidColor(Color.Black),
                    singleLine = true,
                    decorationBox = { inner ->
                        Box(contentAlignment = Alignment.CenterEnd) { if (nickname.isEmpty()) Text("请输入昵称", fontSize = 14.sp, color = TextPlaceholder, textAlign = TextAlign.End, modifier = Modifier.fillMaxWidth()); inner() }
                    }
                )
            }
            // Phone (readonly)
            FormRow("手机号", border = true) {
                Text("138****1234", fontSize = 14.sp, color = TextTertiary)
            }
            // Gender
            FormRow("性别", border = true, onClick = { showGenderPicker = true }) {
                Text(gender, fontSize = 14.sp, color = TextPrimary)
                Text("›", fontSize = 20.sp, color = Color(0xFFDADADA), modifier = Modifier.padding(start = 4.dp))
            }
            // Intro
            FormRow("简介", border = true) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    androidx.compose.foundation.text.BasicTextField(
                        value = intro,
                        onValueChange = { if (it.length <= 30) intro = it },
                        modifier = Modifier.weight(1f),
                        textStyle = androidx.compose.ui.text.TextStyle(fontSize = 14.sp, color = TextPrimary, textAlign = TextAlign.End),
                        cursorBrush = SolidColor(Color.Black),
                        singleLine = true,
                        decorationBox = { inner ->
                            Box(contentAlignment = Alignment.CenterEnd) { if (intro.isEmpty()) Text("一句话介绍自己", fontSize = 14.sp, color = TextPlaceholder, textAlign = TextAlign.End, modifier = Modifier.fillMaxWidth()); inner() }
                        }
                    )
                    Text("${intro.length}/30", fontSize = 11.sp, color = TextPlaceholder, modifier = Modifier.padding(start = 6.dp))
                }
            }
            // Status
            FormRow("状态", border = false, onClick = { showStatusPicker = true }) {
                Box(
                    Modifier
                        .size(7.dp)
                        .clip(CircleShape)
                        .background(currentStatus.third)
                        .padding(end = 5.dp)
                )
                Text(currentStatus.second, fontSize = 14.sp, color = TextPrimary, modifier = Modifier.padding(start = 5.dp))
                Text("›", fontSize = 20.sp, color = Color(0xFFDADADA), modifier = Modifier.padding(start = 4.dp))
            }
        }

        // Save button
        Box(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 23.dp, vertical = 23.dp)
                .height(50.dp)
                .shadow(8.dp, RoundedCornerShape(18.dp))
                .clip(RoundedCornerShape(18.dp))
                .background(Color(0xFF171717))
                .clickable { onNavigateBack() },
            contentAlignment = Alignment.Center
        ) {
            Text("保存", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
        }
    }

    // Gender bottom sheet
    if (showGenderPicker) {
        BottomSheetPicker(
            title = "选择性别",
            options = genders.map { it to (it == gender) },
            onSelect = { gender = it; showGenderPicker = false },
            onDismiss = { showGenderPicker = false }
        )
    }

    // Status bottom sheet
    if (showStatusPicker) {
        BottomSheetPicker(
            title = "选择状态",
            options = statusOptions.map { "${it.second}" to (it.first == status) },
            onSelect = { label ->
                status = statusOptions.first { it.second == label }.first
                showStatusPicker = false
            },
            onDismiss = { showStatusPicker = false }
        )
    }
}

@Composable
private fun FormRow(
    label: String, border: Boolean = true,
    onClick: (() -> Unit)? = null,
    content: @Composable RowScope.() -> Unit
) {
    val mod = if (onClick != null) Modifier.clickable { onClick() } else Modifier
    Row(
        Modifier
            .fillMaxWidth()
            .then(mod)
            .padding(horizontal = 17.dp, vertical = 13.dp)
            .then(if (border) Modifier.border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp)) else Modifier),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary,
            modifier = Modifier.padding(end = 12.dp))
        Row(
            Modifier.weight(1f), horizontalArrangement = Arrangement.End,
            verticalAlignment = Alignment.CenterVertically
        ) { content() }
    }
}

@Composable
private fun BottomSheetPicker(
    title: String, options: List<Pair<String, Boolean>>,
    onSelect: (String) -> Unit, onDismiss: () -> Unit
) {
    Box(
        Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.45f))
            .clickable { onDismiss() },
        contentAlignment = Alignment.BottomCenter
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(topStart = 29.dp, topEnd = 29.dp))
                .background(Color.White)
                .padding(start = 23.dp, end = 23.dp, top = 17.dp, bottom = 19.dp)
        ) {
            Text(title, fontSize = 16.sp, fontWeight = FontWeight.Bold, color = TextPrimary,
                textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().padding(bottom = 12.dp))
            options.forEach { (label, selected) ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .clip(RoundedCornerShape(14.dp))
                        .then(if (selected) Modifier.background(BgModule) else Modifier)
                        .clickable { onSelect(label) }
                        .padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(label, fontSize = 14.sp, color = TextPrimary, fontWeight = FontWeight.Medium,
                        modifier = Modifier.weight(1f))
                    if (selected) AppIcon("check", Modifier.size(16.dp), tint = BrandBlue)
                }
            }
            Box(
                Modifier
                    .fillMaxWidth()
                    .padding(top = 8.dp)
                    .clip(RoundedCornerShape(18.dp))
                    .background(BgModule)
                    .clickable { onDismiss() }
                    .padding(12.dp),
                contentAlignment = Alignment.Center
            ) {
                Text("取消", fontSize = 14.sp, color = TextSecondary)
            }
        }
    }
}
