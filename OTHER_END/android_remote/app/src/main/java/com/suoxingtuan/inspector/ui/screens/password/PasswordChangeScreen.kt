package com.suoxingtuan.inspector.ui.screens.password

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.ui.theme.*
import kotlinx.coroutines.delay

@Composable
fun PasswordChangeScreen(
    onNavigateBack: () -> Unit
) {
    var step by remember { mutableIntStateOf(1) }
    // Step 1
    var smsCode by remember { mutableStateOf("") }
    var countdown by remember { mutableIntStateOf(0) }
    // Step 2
    var newPassword by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }
    var showNewPw by remember { mutableStateOf(false) }
    var showConfirmPw by remember { mutableStateOf(false) }

    val scope = rememberCoroutineScope()

    // Countdown timer
    LaunchedEffect(countdown) {
        if (countdown > 0) { delay(1000); countdown-- }
    }

    // Strength calculation
    val (strengthLabel, strengthPercent, strengthColor) = remember(newPassword) {
        derivedPasswordStrength(newPassword)
    }

    Column(Modifier.fillMaxSize().background(BgPage)) {
        // Nav bar
        Row(
            Modifier.fillMaxWidth().padding(start = 19.dp).height(35.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(Modifier.size(35.dp).clip(RoundedCornerShape(50)).clickable { onNavigateBack() }, contentAlignment = Alignment.Center) {
                Text("‹", fontSize = 28.sp, color = TextPrimary, fontWeight = FontWeight.Light, modifier = Modifier.offset(y = (-2).dp))
            }
            Text("修改密码", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = TextPrimary, modifier = Modifier.padding(start = 8.dp))
        }

        Column(Modifier.padding(horizontal = 17.dp)) {
            if (step == 1) {
                // Step 1: SMS verification
                Text("验证身份", fontSize = 14.sp, color = TextTertiary, modifier = Modifier.padding(start = 4.dp, top = 10.dp, bottom = 8.dp))

                Column(
                    Modifier
                        .fillMaxWidth()
                        .shadow(4.dp, RoundedCornerShape(12.dp))
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color.White)
                ) {
                    // Phone row
                    Row(
                        Modifier.fillMaxWidth().padding(15.dp).border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp)),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text("当前绑定手机号", fontSize = 14.sp, color = TextPrimary)
                        Text("138****1234", fontSize = 14.sp, color = TextTertiary)
                    }
                    // SMS row
                    Row(
                        Modifier.fillMaxWidth().padding(12.dp, 15.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        BasicTextField(
                            value = smsCode,
                            onValueChange = { if (it.length <= 6) smsCode = it.filter { c -> c.isDigit() } },
                            modifier = Modifier
                                .weight(1f)
                                .height(42.dp)
                                .clip(RoundedCornerShape(8.dp))
                                .background(BgModule)
                                .padding(horizontal = 12.dp),
                            textStyle = androidx.compose.ui.text.TextStyle(fontSize = 14.sp, color = TextPrimary),
                            cursorBrush = SolidColor(Color.Black),
                            singleLine = true,
                            decorationBox = { inner ->
                                Box { if (smsCode.isEmpty()) Text("请输入6位验证码", fontSize = 14.sp, color = TextPlaceholder); inner() }
                            }
                        )
                        Spacer(Modifier.width(10.dp))
                        Box(
                            Modifier
                                .height(42.dp)
                                .clip(RoundedCornerShape(8.dp))
                                .background(if (countdown > 0) Color(0xFFB5B5B5) else BrandBlue)
                                .clickable(enabled = countdown == 0) { countdown = 60 }
                                .padding(horizontal = 14.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                if (countdown > 0) "${countdown}s" else "获取验证码",
                                fontSize = 13.sp, fontWeight = FontWeight.Medium, color = Color.White
                            )
                        }
                    }
                    Text("验证码会以弹窗方式展示，模拟真实短信发送",
                        fontSize = 11.sp, color = AccentOrange,
                        modifier = Modifier.padding(start = 15.dp, bottom = 12.dp))
                }

                // Next button
                val canNext = smsCode.length >= 6
                Box(
                    Modifier
                        .fillMaxWidth()
                        .padding(top = 23.dp)
                        .height(50.dp)
                        .shadow(8.dp, RoundedCornerShape(18.dp))
                        .clip(RoundedCornerShape(18.dp))
                        .background(if (canNext) Color(0xFF171717) else Color(0xFFDADADA))
                        .clickable(enabled = canNext) { step = 2 },
                    contentAlignment = Alignment.Center
                ) {
                    Text("下一步", fontSize = 16.sp, fontWeight = FontWeight.SemiBold,
                        color = if (canNext) Color.White else Color(0xFFB5B5B5))
                }
            } else {
                // Step 2: Set new password
                Text("设置新密码", fontSize = 14.sp, color = TextTertiary, modifier = Modifier.padding(start = 4.dp, top = 10.dp, bottom = 8.dp))

                Column(
                    Modifier
                        .fillMaxWidth()
                        .shadow(4.dp, RoundedCornerShape(12.dp))
                        .clip(RoundedCornerShape(12.dp))
                        .background(Color.White)
                ) {
                    // New password
                    Column(
                        Modifier.fillMaxWidth().padding(horizontal = 15.dp, vertical = 13.dp)
                            .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp))
                    ) {
                        Text("新密码", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary,
                            modifier = Modifier.padding(bottom = 8.dp))
                        Row(
                            Modifier.fillMaxWidth().height(42.dp).clip(RoundedCornerShape(8.dp)).background(BgModule),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            BasicTextField(
                                value = newPassword,
                                onValueChange = { if (it.length <= 32) newPassword = it },
                                modifier = Modifier.weight(1f).padding(horizontal = 12.dp),
                                textStyle = androidx.compose.ui.text.TextStyle(fontSize = 14.sp, color = TextPrimary),
                                cursorBrush = SolidColor(Color.Black),
                                singleLine = true,
                                visualTransformation = if (showNewPw) VisualTransformation.None else PasswordVisualTransformation(),
                                decorationBox = { inner ->
                                    Box { if (newPassword.isEmpty()) Text("请输入新密码（至少8位）", fontSize = 14.sp, color = TextPlaceholder); inner() }
                                }
                            )
                            Box(Modifier.size(38.dp, 42.dp).clickable { showNewPw = !showNewPw }, contentAlignment = Alignment.Center) {
                                Text(if (showNewPw) "👁" else "👁‍🗨", fontSize = 16.sp)
                            }
                        }
                    }

                    // Strength bar
                    if (newPassword.isNotEmpty()) {
                        Row(
                            Modifier.fillMaxWidth().padding(horizontal = 15.dp, vertical = 6.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(Modifier.weight(1f).height(4.dp).clip(RoundedCornerShape(2.dp)).background(BgModule)) {
                                Box(Modifier.fillMaxHeight().fillMaxWidth(strengthPercent / 100f)
                                    .clip(RoundedCornerShape(2.dp)).background(strengthColor))
                            }
                            Spacer(Modifier.width(8.dp))
                            Text(strengthLabel, fontSize = 12.sp, fontWeight = FontWeight.Medium, color = strengthColor)
                        }
                    }

                    // Confirm password
                    Column(Modifier.fillMaxWidth().padding(horizontal = 15.dp, vertical = 13.dp)) {
                        Text("确认密码", fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary,
                            modifier = Modifier.padding(bottom = 8.dp))
                        Row(
                            Modifier.fillMaxWidth().height(42.dp).clip(RoundedCornerShape(8.dp)).background(BgModule),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            BasicTextField(
                                value = confirmPassword,
                                onValueChange = { if (it.length <= 32) confirmPassword = it },
                                modifier = Modifier.weight(1f).padding(horizontal = 12.dp),
                                textStyle = androidx.compose.ui.text.TextStyle(fontSize = 14.sp, color = TextPrimary),
                                cursorBrush = SolidColor(Color.Black),
                                singleLine = true,
                                visualTransformation = if (showConfirmPw) VisualTransformation.None else PasswordVisualTransformation(),
                                decorationBox = { inner ->
                                    Box { if (confirmPassword.isEmpty()) Text("请再次输入新密码", fontSize = 14.sp, color = TextPlaceholder); inner() }
                                }
                            )
                            Box(Modifier.size(38.dp, 42.dp).clickable { showConfirmPw = !showConfirmPw }, contentAlignment = Alignment.Center) {
                                Text(if (showConfirmPw) "👁" else "👁‍🗨", fontSize = 16.sp)
                            }
                        }
                    }
                    if (confirmPassword.isNotEmpty() && newPassword != confirmPassword) {
                        Text("两次密码输入不一致", fontSize = 12.sp, color = Error,
                            modifier = Modifier.padding(start = 15.dp, bottom = 10.dp))
                    }
                }

                // Submit button
                val canSubmit = newPassword.length >= 8 && newPassword == confirmPassword && strengthLabel != "弱"
                Box(
                    Modifier
                        .fillMaxWidth()
                        .padding(top = 23.dp)
                        .height(50.dp)
                        .shadow(8.dp, RoundedCornerShape(18.dp))
                        .clip(RoundedCornerShape(18.dp))
                        .background(if (canSubmit) Color(0xFF171717) else Color(0xFFDADADA))
                        .clickable(enabled = canSubmit) { onNavigateBack() },
                    contentAlignment = Alignment.Center
                ) {
                    Text("确认修改", fontSize = 16.sp, fontWeight = FontWeight.SemiBold,
                        color = if (canSubmit) Color.White else Color(0xFFB5B5B5))
                }
            }
        }
    }
}

private fun derivedPasswordStrength(pw: String): Triple<String, Float, Color> {
    if (pw.isEmpty()) return Triple("", 0f, Color(0xFFDA1E28))
    val hasNum = Regex("\\d").containsMatchIn(pw)
    val hasLetter = Regex("[a-zA-Z]").containsMatchIn(pw)
    val hasSpecial = Regex("[!@#\$%^&*()_+\\-=\\[\\]{};':\"\\\\|,.<>/?]").containsMatchIn(pw)
    val len = pw.length

    return if ((hasNum && !hasLetter && !hasSpecial) || (!hasNum && hasLetter && !hasSpecial)) {
        if (len < 8) Triple("弱", 25f, Color(0xFFDA1E28))
        else Triple("中", 50f, Color(0xFFF2994A))
    } else if (hasNum && hasLetter && !hasSpecial) {
        if (len >= 10) Triple("强", 75f, Color(0xFF24A148))
        else Triple("中", 55f, Color(0xFFF2994A))
    } else if (hasNum && hasLetter && hasSpecial && len >= 10) {
        Triple("强", 100f, Color(0xFF24A148))
    } else {
        Triple("弱", 30f, Color(0xFFDA1E28))
    }
}
