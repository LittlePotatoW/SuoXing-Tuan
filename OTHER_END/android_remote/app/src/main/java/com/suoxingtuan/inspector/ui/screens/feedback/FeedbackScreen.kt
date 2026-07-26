package com.suoxingtuan.inspector.ui.screens.feedback

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.ui.components.AppIcon

private val BgPage = Color(0xFFF7F7F7)
private val BorderLight = Color(0xFFE8E8E8)
private val TextPrimary = Color(0xFF111111)
private val TextTertiary = Color(0xFF8E8E8E)
private val Placeholder = Color(0xFFB5B5B5)
private val ArrowColor = Color(0xFFDADADA)
private val ErrorColor = Color(0xFFEF4444)
private val RequireColor = Color(0xFFEF4444)
private val BtnBg = Color(0xFF171717)

@Composable
fun FeedbackScreen(
    onNavigateBack: () -> Unit
) {
    val feedbackTypes = listOf("Bug 报告", "功能建议", "通用反馈", "其他")
    var selectedType by remember { mutableIntStateOf(0) }
    var contact by remember { mutableStateOf("") }
    var content by remember { mutableStateOf("") }
    var errorMsg by remember { mutableStateOf("") }
    var isSubmitting by remember { mutableStateOf(false) }
    val scrollState = rememberScrollState()
    val scope = rememberCoroutineScope()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BgPage)
            .padding(horizontal = 23.dp)
    ) {
        Spacer(Modifier.height(15.dp))

        Column(modifier = Modifier.verticalScroll(scrollState)) {
            // Feedback type picker
            Column(
                Modifier
                    .fillMaxWidth()
                    .padding(vertical = 15.dp)
                    .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp))
            ) {
                Text(
                    "反馈类型", fontSize = 14.sp, fontWeight = FontWeight.SemiBold,
                    color = TextPrimary, modifier = Modifier.padding(bottom = 8.dp)
                )
                // Simple dropdown placeholder - using a clickable row
                Row(
                    Modifier
                        .fillMaxWidth()
                        .height(38.dp)
                        .clickable {
                            selectedType = (selectedType + 1) % feedbackTypes.size
                        },
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(feedbackTypes[selectedType], fontSize = 14.sp, color = TextPrimary)
                    Text("›", fontSize = 22.sp, color = ArrowColor, fontWeight = FontWeight.Light)
                }
            }

            // Contact
            Column(
                Modifier
                    .fillMaxWidth()
                    .padding(vertical = 15.dp)
                    .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp))
            ) {
                Text(
                    "联系方式", fontSize = 14.sp, fontWeight = FontWeight.SemiBold,
                    color = TextPrimary, modifier = Modifier.padding(bottom = 8.dp)
                )
                androidx.compose.foundation.text.BasicTextField(
                    value = contact,
                    onValueChange = { contact = it },
                    modifier = Modifier.fillMaxWidth().height(38.dp),
                    textStyle = androidx.compose.ui.text.TextStyle(fontSize = 14.sp, color = TextPrimary),
                    cursorBrush = SolidColor(Color.Black),
                    singleLine = true,
                    decorationBox = { inner ->
                        Box { if (contact.isEmpty()) Text("手机号或邮箱（选填）", fontSize = 14.sp, color = Placeholder); inner() }
                    }
                )
            }

            // Content
            Column(Modifier.fillMaxWidth().padding(vertical = 15.dp)) {
                Text(
                    "反馈内容 ", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary,
                    modifier = Modifier.padding(bottom = 8.dp)
                )
                Text("*", fontSize = 14.sp, color = RequireColor)

                // Textarea
                Box(
                    Modifier
                        .fillMaxWidth()
                        .height(115.dp)
                        .border(0.5.dp, SolidColor(Color(0xFFBDBDBD)), RoundedCornerShape(12.dp))
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color.White)
                ) {
                    androidx.compose.foundation.text.BasicTextField(
                        value = content,
                        onValueChange = { if (it.length <= 500) content = it },
                        modifier = Modifier.fillMaxSize().padding(12.dp),
                        textStyle = androidx.compose.ui.text.TextStyle(fontSize = 14.sp, color = TextPrimary),
                        cursorBrush = SolidColor(Color.Black),
                        decorationBox = { inner ->
                            Box { if (content.isEmpty()) Text("请描述您的反馈...", fontSize = 14.sp, color = Placeholder); inner() }
                        }
                    )
                }
                Text(
                    "${content.length}/500", fontSize = 12.sp, color = TextTertiary,
                    modifier = Modifier.fillMaxWidth().padding(top = 5.dp),
                    textAlign = androidx.compose.ui.text.style.TextAlign.Right
                )
            }

            // Error
            if (errorMsg.isNotEmpty()) {
                Text(errorMsg, fontSize = 13.sp, color = ErrorColor, modifier = Modifier.padding(top = 10.dp))
            }

            // Submit button
            Box(
                Modifier
                    .fillMaxWidth()
                    .padding(top = 31.dp)
                    .height(50.dp)
                    .graphicsLayer { alpha = if (isSubmitting) 0.3f else 1f }
                    .clip(RoundedCornerShape(18.dp))
                    .background(BtnBg)
                    .clickable(enabled = !isSubmitting) {
                        if (content.isBlank()) { errorMsg = "请填写反馈内容"; return@clickable }
                        isSubmitting = true
                        scope.launch {
                            delay(600)
                            isSubmitting = false
                            content = ""
                            errorMsg = ""
                            onNavigateBack()
                        }
                    },
                contentAlignment = Alignment.Center
            ) {
                Text(
                    if (isSubmitting) "提交中..." else "提交反馈",
                    fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = Color.White
                )
            }
        }
    }
}
