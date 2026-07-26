package com.suoxingtuan.inspector.ui.screens.login

import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.foundation.layout.offset
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.focus.onFocusChanged
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.R
import com.suoxingtuan.inspector.data.repository.AuthRepository
import androidx.compose.ui.graphics.graphicsLayer
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

// Colors from original login page SCSS
private val InputBg = Color(0xFFFAFAFA)
private val InputBorder = Color(0xFFE0E0E0)
private val InputFocusBorder = Color.Black
private val InputFocusGlow = Color(0x0F000000)
private val PlaceholderColor = Color(0xFFB0B0B0)
private val InputTextColor = Color(0xFF111111)
private val BtnBg = Color.Black

@Composable
fun LoginScreen(
    onLoginSuccess: () -> Unit
) {
    var phone by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var confirmPassword by remember { mutableStateOf("") }
    var errorMsg by remember { mutableStateOf("") }
    var isRegister by remember { mutableStateOf(false) }
    var isSubmitting by remember { mutableStateOf(false) }

    val scope = rememberCoroutineScope()

    // Background gradient animation (8s cycle)
    val bgAnim = rememberInfiniteTransition(label = "bg")
    val bgX by bgAnim.animateFloat(0f, 1f, infiniteRepeatable(tween(8000, easing = EaseInOut), RepeatMode.Reverse), label = "bgX")
    val bgY by bgAnim.animateFloat(0f, 1f, infiniteRepeatable(tween(8000, easing = EaseInOut), RepeatMode.Reverse), label = "bgY")

    // Card entrance
    var showCard by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { showCard = true }
    val cardAlpha by animateFloatAsState(if (showCard) 1f else 0f, tween(600, easing = EaseOut), label = "cardIn")
    val cardY by animateDpAsState(if (showCard) 0.dp else 20.dp, tween(600, easing = EaseOut), label = "cardUp")

    // Float
    val floatAnim = rememberInfiniteTransition(label = "float")
    val floatY by floatAnim.animateFloat(0f, -3f, infiniteRepeatable(tween(2000, easing = EaseInOut), RepeatMode.Reverse), label = "floatY")

    // Helper to reset form
    fun reset() { phone = ""; password = ""; confirmPassword = ""; errorMsg = "" }

    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        // Animated gradient background
        Box(
            Modifier
                .fillMaxSize()
                .background(
                    Brush.linearGradient(
                        colors = listOf(
                            Color(0xFFE8F4FD), Color(0xFFF5F7FA),
                            Color(0xFFFFF8F0), Color(0xFFE8F8F5), Color(0xFFE0F7FA)
                        ),
                        start = androidx.compose.ui.geometry.Offset(bgX * 2000f, bgY * 2000f),
                        end = androidx.compose.ui.geometry.Offset((1f - bgX) * 2000f, (1f - bgY) * 2000f)
                    )
                )
        )

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 23.dp),
            horizontalAlignment = Alignment.Start,
            verticalArrangement = Arrangement.Center
        ) {
            // Illustration (floating)
            androidx.compose.foundation.Image(
                painter = painterResource(R.drawable.login_illustration),
                contentDescription = null,
                modifier = Modifier
                    .width(202.dp)
                    .offset(x = (-5).dp, y = floatY.dp)
                    .padding(bottom = 15.dp),
                contentScale = ContentScale.FillWidth
            )

            // White card
            Column(
                Modifier
                    .fillMaxWidth()
                    .graphicsLayer { alpha = cardAlpha }
                    .offset(y = cardY)
                    .shadow(8.dp, RoundedCornerShape(15.dp), ambientColor = Color.Black.copy(0.06f), spotColor = Color.Black.copy(0.06f))
                    .clip(RoundedCornerShape(15.dp))
                    .background(Color.White)
                    .padding(start = 21.dp, end = 21.dp, top = 27.dp, bottom = 23.dp)
            ) {
                // Phone input
                LoginTextField(
                    value = phone,
                    onValueChange = { if (it.length <= 11) phone = it },
                    placeholder = if (isRegister) "请输入手机号" else "请输入账号",
                    keyboardType = KeyboardType.Phone
                )
                Spacer(Modifier.height(12.dp))

                // Password input
                LoginTextField(
                    value = password,
                    onValueChange = { password = it },
                    placeholder = if (isRegister) "请设置密码（至少6位）" else "请输入密码",
                    keyboardType = KeyboardType.Password,
                    isPassword = true
                )

                // Confirm password (register only)
                if (isRegister) {
                    Spacer(Modifier.height(12.dp))
                    LoginTextField(
                        value = confirmPassword,
                        onValueChange = { confirmPassword = it },
                        placeholder = "请再次输入密码",
                        keyboardType = KeyboardType.Password,
                        isPassword = true
                    )
                }

                // Error
                if (errorMsg.isNotEmpty()) {
                    Text(
                        text = errorMsg,
                        fontSize = 12.sp,
                        color = Color(0xFFDA1E28),
                        modifier = Modifier.padding(bottom = 6.dp)
                    )
                }

                if (!isRegister) {
                    // Login button
                    Box(
                        Modifier
                            .fillMaxWidth()
                            .padding(top = 12.dp)
                            .height(48.dp)
                            .graphicsLayer { alpha = if (phone.isNotBlank() && password.isNotBlank() && !isSubmitting) 1f else 0.35f }
                            .clip(RoundedCornerShape(24.dp))
                            .background(BtnBg)
                            .clickable(enabled = phone.isNotBlank() && password.isNotBlank() && !isSubmitting) {
                                scope.launch { submitLogin(phone, password) { msg, ok -> errorMsg = msg; isSubmitting = false; if (ok) onLoginSuccess() }; isSubmitting = true }
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            if (isSubmitting) "登录中..." else "登录",
                            fontSize = 14.sp, color = Color.White
                        )
                    }

                    // Footer
                    Row(
                        Modifier.fillMaxWidth().padding(top = 23.dp),
                        Arrangement.Center, Alignment.CenterVertically
                    ) {
                        Text("忘记密码", fontSize = 12.sp, color = Color(0xFF999999),
                            modifier = Modifier.clickable(interactionSource = remember { MutableInteractionSource() }, indication = null) { isRegister = true; reset() })
                        Text(" | ", fontSize = 12.sp, color = Color(0xFFCCCCCC))
                        Text("注册账号", fontSize = 12.sp, color = Color(0xFF999999),
                            modifier = Modifier.clickable(interactionSource = remember { MutableInteractionSource() }, indication = null) { isRegister = true; reset() })
                    }
                } else {
                    // Register button
                    val canReg = phone.isNotBlank() && password.isNotBlank() && confirmPassword.isNotBlank() && !isSubmitting
                    Box(
                        Modifier
                            .fillMaxWidth()
                            .padding(top = 12.dp)
                            .height(48.dp)
                            .graphicsLayer { alpha = if (canReg) 1f else 0.35f }
                            .clip(RoundedCornerShape(24.dp))
                            .background(BtnBg)
                            .clickable(enabled = canReg) {
                                scope.launch { submitRegister(phone, password, confirmPassword) { msg, ok -> errorMsg = msg; isSubmitting = false; if (ok) reset() }; isSubmitting = true }
                            },
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            if (isSubmitting) "注册中..." else "注册",
                            fontSize = 14.sp, color = Color.White
                        )
                    }
                    // Back link
                    Text("← 返回登录", fontSize = 12.sp, color = Color(0xFF999999), textAlign = TextAlign.Center,
                        modifier = Modifier.fillMaxWidth().padding(top = 12.dp)
                            .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null) { isRegister = false; reset() })
                }
            }

            // Agreement
            Text(
                "登录即表示同意《用户协议》和《隐私政策》",
                fontSize = 11.sp, color = Color(0xFFAAAAAA), textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth().padding(top = 13.dp)
            )
        }
    }
}

@Composable
private fun LoginTextField(
    value: String, onValueChange: (String) -> Unit, placeholder: String,
    keyboardType: KeyboardType = KeyboardType.Text, isPassword: Boolean = false
) {
    var focused by remember { mutableStateOf(false) }
    val borderColor = if (focused) InputFocusBorder else InputBorder
    val glowMod = if (focused) Modifier.shadow(2.dp, RoundedCornerShape(8.dp), ambientColor = InputFocusGlow, spotColor = InputFocusGlow) else Modifier

    BasicTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = Modifier
            .fillMaxWidth()
            .height(46.dp)
            .then(glowMod)
            .clip(RoundedCornerShape(8.dp))
            .border(0.5.dp, SolidColor(borderColor), RoundedCornerShape(8.dp))
            .background(InputBg, RoundedCornerShape(8.dp))
            .padding(horizontal = 13.dp)
            .onFocusChanged { focused = it.isFocused },
        singleLine = true,
        textStyle = androidx.compose.ui.text.TextStyle(
            fontSize = 14.sp, color = InputTextColor
        ),
        cursorBrush = SolidColor(Color.Black),
        keyboardOptions = KeyboardOptions(keyboardType = keyboardType),
        visualTransformation = if (isPassword) PasswordVisualTransformation() else VisualTransformation.None,
        decorationBox = { innerTextField ->
            Box {
                if (value.isEmpty()) {
                    Text(placeholder, fontSize = 14.sp, color = PlaceholderColor)
                }
                innerTextField()
            }
        }
    )
}

private suspend fun submitLogin(phone: String, password: String, cb: (String, Boolean) -> Unit) {
    val result = AuthRepository.login(phone, password)
    cb(result.message, result.success)
}

private suspend fun submitRegister(phone: String, password: String, confirm: String, cb: (String, Boolean) -> Unit) {
    if (password != confirm) { cb("两次输入的密码不一致", false); return }
    val result = AuthRepository.register(phone, password)
    cb(result.message, result.success)
}
