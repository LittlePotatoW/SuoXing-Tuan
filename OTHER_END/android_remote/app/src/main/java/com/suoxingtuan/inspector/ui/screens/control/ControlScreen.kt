package com.suoxingtuan.inspector.ui.screens.control

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.awaitEachGesture
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.center
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay

// ---- Colors (matching project "2") ----
private val DpadBg = Color(0xFF0F0F1A)
private val BtnNormalFill = Color(0xFF1E1E38)
private val BtnNormalStroke = Color(0xFF333355)
private val BtnActiveFill = Color(0xFF3A5090)
private val BtnActiveStroke = Color(0xFF6080CC)
private val BtnText = Color(0xFFCCCCDD)
private val DirGold = Color(0xFFFFD700)
private val DirCyan = Color(0xFF7BC8A4)

// ---- HTTP Sender ----
private val executor = java.util.concurrent.Executors.newSingleThreadExecutor()
private const val CAR_HOST = "192.168.4.1:8080"

private fun sendHttp(cmd: String) {
    executor.execute {
        try {
            val url = java.net.URL("http://$CAR_HOST/$cmd")
            val c = url.openConnection() as java.net.HttpURLConnection
            c.requestMethod = "GET"
            c.connectTimeout = 100
            c.readTimeout = 100
            c.connect()
            c.responseCode
            c.inputStream.close()
        } catch (_: Exception) {}
    }
}

@Composable
fun ControlScreen(
    onNavigateBack: () -> Unit
) {
    // D-Pad state
    var motorUp by remember { mutableStateOf(false) }
    var motorDown by remember { mutableStateOf(false) }
    var steerLeft by remember { mutableStateOf(false) }
    var steerRight by remember { mutableStateOf(false) }
    var detectMode by remember { mutableStateOf(false) }
    var connected by remember { mutableStateOf(false) }
    var lastCmd by remember { mutableStateOf("") }

    fun buildCmd(): String {
        val motor = when {
            motorUp -> "up"
            motorDown -> "down"
            else -> "m0"
        }
        val steer = when {
            steerLeft -> "left"
            steerRight -> "right"
            else -> "s0"
        }
        return "$motor,$steer"
    }

    fun sendState() {
        if (!connected) return
        val cmd = buildCmd()
        if (cmd != lastCmd || cmd != "m0,s0") {
            lastCmd = cmd
            sendHttp(cmd)
        }
    }

    fun stopAll() {
        motorUp = false; motorDown = false; steerLeft = false; steerRight = false
        lastCmd = "m0,s0"
        sendHttp("m0,s0")
    }

    // Keep-alive: resend every 200ms while holding a direction
    LaunchedEffect(motorUp, motorDown, steerLeft, steerRight, connected) {
        while (connected && (motorUp || motorDown || steerLeft || steerRight)) {
            sendState()
            delay(200)
        }
        if (!motorUp && !motorDown && !steerLeft && !steerRight && lastCmd != "m0,s0") {
            lastCmd = "m0,s0"
            sendHttp("m0,s0")
        }
    }

    // ---- UI ----
    Column(
        Modifier.fillMaxSize().background(DpadBg).padding(top = 8.dp)
    ) {
        // Header
        Row(
            Modifier.fillMaxWidth().padding(start = 15.dp, end = 15.dp).height(44.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Box(
                Modifier.size(42.dp).clip(CircleShape).background(Color.White.copy(0.07f))
                    .clickable { stopAll(); onNavigateBack() },
                contentAlignment = Alignment.Center
            ) { Text("‹", fontSize = 28.sp, color = Color.White, fontWeight = FontWeight.Thin) }
            Spacer(Modifier.weight(1f))
            Text("遥控小车", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color.White)
            Spacer(Modifier.weight(1f))
            Spacer(Modifier.size(42.dp))
        }

        // Direction text
        Text(
            text = when {
                motorUp && steerLeft -> "前进 + 左转"
                motorUp && steerRight -> "前进 + 右转"
                motorDown && steerLeft -> "后退 + 左转"
                motorDown && steerRight -> "后退 + 右转"
                motorUp -> "前进"
                motorDown -> "后退"
                steerLeft -> "左转"
                steerRight -> "右转"
                else -> "就绪"
            },
            color = if (motorUp || motorDown || steerLeft || steerRight) DirGold else DirCyan,
            fontSize = 16.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp)
        )

        // D-Pad
        Box(
            Modifier.fillMaxWidth().weight(1f).padding(horizontal = 20.dp),
            contentAlignment = Alignment.Center
        ) {
            DPadCanvas(
                onDirectionChange = { up, down, left, right ->
                    motorUp = up; motorDown = down; steerLeft = left; steerRight = right
                },
                modifier = Modifier.size(280.dp)
            )
        }

        // Trim buttons
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 14.dp).padding(bottom = 6.dp),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            TrimButton("◀") { if (connected) sendHttp("trim_l") }
            TrimButton("⊙") { if (connected) sendHttp("trim_0") }
            TrimButton("▶") { if (connected) sendHttp("trim_r") }
        }

        // Detect mode toggle
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 14.dp).padding(bottom = 6.dp),
            horizontalArrangement = Arrangement.Center
        ) {
            Box(
                Modifier.clip(RoundedCornerShape(8.dp))
                    .background(if (detectMode) BtnActiveFill else Color.White.copy(0.06f))
                    .border(0.5.dp, SolidColor(if (detectMode) BtnActiveStroke else Color.White.copy(0.12f)), RoundedCornerShape(8.dp))
                    .clickable {
                        detectMode = !detectMode
                        if (connected) sendHttp(if (detectMode) "slow" else "fast")
                    }.padding(horizontal = 20.dp, vertical = 8.dp)
            ) {
                Text(if (detectMode) "检测模式 (慢速)" else "正常模式 (快速)", color = Color.White.copy(0.7f), fontSize = 13.sp)
            }
        }

        // Connect button
        Box(
            Modifier.fillMaxWidth().padding(horizontal = 14.dp).padding(bottom = 14.dp)
                .height(46.dp).clip(RoundedCornerShape(10.dp))
                .background(if (connected) Color(0xFF2E7D32) else Color(0xFF466CAC))
                .clickable {
                    connected = !connected
                    if (!connected) stopAll()
                    else sendState()
                },
            contentAlignment = Alignment.Center
        ) {
            Text(
                if (connected) "已连接 ✓" else "连接小车",
                color = Color.White, fontSize = 16.sp, fontWeight = FontWeight.SemiBold
            )
        }

        if (connected) {
            Text(
                "已连接 $CAR_HOST",
                color = Color(0xFF666666), fontSize = 11.sp,
                textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth().padding(bottom = 4.dp)
            )
        }
    }
}

// ---- Multi-touch D-Pad ----
@Composable
private fun DPadCanvas(
    onDirectionChange: (up: Boolean, down: Boolean, left: Boolean, right: Boolean) -> Unit,
    modifier: Modifier = Modifier
) {
    var activeMask by remember { mutableIntStateOf(0) }

    fun update(mask: Int) {
        if (mask != activeMask) {
            activeMask = mask
            onDirectionChange(
                (mask and 1) != 0, (mask and 2) != 0, (mask and 4) != 0, (mask and 8) != 0
            )
        }
    }

    Box(modifier = modifier.pointerInput(Unit) {
        awaitEachGesture {
            val ptrPositions = mutableMapOf<Long, Pair<Float, Float>>()
            var running = true
            do {
                val event = awaitPointerEvent()
                for (ch in event.changes) {
                    if (ch.pressed) ptrPositions[ch.id.value] = ch.position.x to ch.position.y
                    else ptrPositions.remove(ch.id.value)
                    ch.consume()
                }
                if (event.changes.all { !it.pressed }) running = false

                var mask = 0
                val cx = size.width / 2f; val cy = size.height / 2f
                val hw = size.width / 3.5f
                for ((_, pos) in ptrPositions) {
                    if (pos.second < cy - hw * 0.5f) mask = mask or 1
                    if (pos.second > cy + hw * 0.5f) mask = mask or 2
                    if (pos.first < cx - hw * 0.5f) mask = mask or 4
                    if (pos.first > cx + hw * 0.5f) mask = mask or 8
                }
                update(mask)
            } while (running)
            update(0)
        }
    }) {
        val up = (activeMask and 1) != 0; val down = (activeMask and 2) != 0
        val left = (activeMask and 4) != 0; val right = (activeMask and 8) != 0

        // D-Pad drawn on Canvas, text labels overlaid
        DPadCanvasDraw(up, down, left, right, Modifier.fillMaxSize())
        DPadLabel("▲", up, Alignment.TopCenter, Modifier.fillMaxSize())
        DPadLabel("▼", down, Alignment.BottomCenter, Modifier.fillMaxSize())
        DPadLabel("◀", left, Alignment.CenterStart, Modifier.fillMaxSize())
        DPadLabel("▶", right, Alignment.CenterEnd, Modifier.fillMaxSize())
    }
}

@Composable
private fun DPadCanvasDraw(up: Boolean, down: Boolean, left: Boolean, right: Boolean, modifier: Modifier) {
    Canvas(modifier) {
        val w = size.width; val cx = w / 2f; val cy = size.height / 2f
        val hw = w / 3.5f; val bw = w / 3f; val br = 10f
        drawBtn(cx - bw / 2, cy - hw - bw / 2, bw, bw, br, up)
        drawBtn(cx - bw / 2, cy + hw - bw / 2, bw, bw, br, down)
        drawBtn(cx - hw - bw / 2, cy - bw / 2, bw, bw, br, left)
        drawBtn(cx + hw - bw / 2, cy - bw / 2, bw, bw, br, right)
    }
}

private fun DrawScope.drawBtn(
    left: Float, top: Float, width: Float, height: Float, cornerRadius: Float, active: Boolean
) {
    val fill = if (active) BtnActiveFill else BtnNormalFill
    val stroke = if (active) BtnActiveStroke else BtnNormalStroke
    val path = Path().apply {
        addRoundRect(androidx.compose.ui.geometry.RoundRect(left, top, left + width, top + height, cornerRadius, cornerRadius))
    }
    drawPath(path, fill, style = Fill)
    drawPath(path, stroke, style = Stroke(3f, cap = StrokeCap.Round))
}

@Composable
private fun DPadLabel(text: String, active: Boolean, alignment: Alignment, modifier: Modifier) {
    Box(modifier, contentAlignment = alignment) {
        Canvas(Modifier.size(90.dp)) {
            val cx = size.width / 2; val cy = size.height / 2
            val fill = if (active) BtnActiveFill else BtnNormalFill
            val stroke = if (active) BtnActiveStroke else BtnNormalStroke
            val path = Path().apply {
                addRoundRect(androidx.compose.ui.geometry.RoundRect(0f, 0f, size.width, size.height, 10f, 10f))
            }
            drawPath(path, fill, style = Fill)
            drawPath(path, stroke, style = Stroke(3f, cap = StrokeCap.Round))
        }
        Text(text, color = BtnText, fontSize = 32.sp, fontWeight = FontWeight.Bold)
    }
}

// ---- Trim Button ----
@Composable
private fun TrimButton(label: String, onClick: () -> Unit) {
    Box(
        Modifier.size(44.dp).clip(RoundedCornerShape(10.dp))
            .background(Color.White.copy(0.06f))
            .border(0.5.dp, SolidColor(Color.White.copy(0.12f)), RoundedCornerShape(10.dp))
            .clickable { onClick() },
        contentAlignment = Alignment.Center
    ) {
        Text(label, color = Color.White.copy(0.7f), fontSize = 18.sp)
    }
}
