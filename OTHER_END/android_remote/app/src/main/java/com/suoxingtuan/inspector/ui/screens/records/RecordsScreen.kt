package com.suoxingtuan.inspector.ui.screens.records

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
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

data class Record(
    val id: String, val date: String, val area: String, val taskId: String,
    val duration: String, val operator: String, val issuesCount: Int
)

@Composable
fun RecordsScreen(
    onNavigateBack: () -> Unit
) {
    val stats = Triple(47, 128, 91)
    var filterArea by remember { mutableStateOf("") }
    var filterStatus by remember { mutableStateOf("") }
    val areas = listOf("", "隧道A区", "隧道B区", "隧道C区")
    val statusOpts = listOf("", "normal", "abnormal")

    val records = remember {
        listOf(
            Record("1", "2026-07-11 14:00", "隧道B区", "TD-2026-0711-001", "1小时52分", "张伟", 4),
            Record("2", "2026-07-10 09:30", "隧道A区", "TD-2026-0710-003", "2小时05分", "李明", 0),
            Record("3", "2026-07-09 15:00", "隧道B区", "TD-2026-0709-002", "1小时38分", "张伟", 3),
            Record("4", "2026-07-08 10:00", "隧道C区", "TD-2026-0708-005", "2小时12分", "王强", 6),
            Record("5", "2026-07-07 08:30", "隧道A区", "TD-2026-0707-001", "1小时45分", "李明", 1)
        )
    }

    val filtered = remember(records, filterArea, filterStatus) {
        records.filter { r ->
            (filterArea.isEmpty() || r.area == filterArea) &&
            (filterStatus.isEmpty() || (filterStatus == "normal" && r.issuesCount == 0) || (filterStatus == "abnormal" && r.issuesCount > 0))
        }
    }

    Column(Modifier.fillMaxSize().background(BgPage)) {
        // Nav bar
        Row(Modifier.fillMaxWidth().padding(start = 19.dp).height(35.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(35.dp).clip(RoundedCornerShape(50)).clickable { onNavigateBack() }, contentAlignment = Alignment.Center) {
                Text("‹", fontSize = 28.sp, color = TextPrimary, fontWeight = FontWeight.Light, modifier = Modifier.offset(y = (-2).dp))
            }
            Text("检测记录", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = TextPrimary, modifier = Modifier.padding(start = 8.dp))
        }

        // Stats card
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 17.dp, vertical = 10.dp)
                .shadow(4.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp)).background(Color.White).padding(horizontal = 8.dp, vertical = 15.dp),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            StatBlock(stats.first.toString(), "总检测次数")
            Box(Modifier.width(0.5.dp).height(23.dp).background(BorderLight))
            StatBlock(stats.second.toString(), "总发现问题")
            Box(Modifier.width(0.5.dp).height(23.dp).background(BorderLight))
            StatBlock("${stats.third}%", "检出率")
        }

        // Filter row
        Row(Modifier.fillMaxWidth().padding(horizontal = 17.dp, vertical = 0.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Box(Modifier.clip(RoundedCornerShape(20.dp))
                .background(if (filterArea.isNotEmpty()) BrandBlue else Color.White)
                .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(20.dp))
                .clickable { val i = areas.indexOf(filterArea); filterArea = areas[(i + 1) % areas.size] }
                .padding(horizontal = 12.dp, vertical = 7.dp)) {
                Text(filterArea.ifEmpty { "全部区域" }, fontSize = 14.sp, color = if (filterArea.isNotEmpty()) Color.White else TextSecondary)
            }
            Box(Modifier.clip(RoundedCornerShape(20.dp))
                .background(if (filterStatus.isNotEmpty()) BrandBlue else Color.White)
                .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(20.dp))
                .clickable { val i = statusOpts.indexOf(filterStatus); filterStatus = statusOpts[(i + 1) % statusOpts.size] }
                .padding(horizontal = 12.dp, vertical = 7.dp)) {
                Text(when (filterStatus) { "normal" -> "正常"; "abnormal" -> "异常"; else -> "全部状态" }, fontSize = 14.sp, color = if (filterStatus.isNotEmpty()) Color.White else TextSecondary)
            }
            if (filterArea.isNotEmpty() || filterStatus.isNotEmpty()) {
                Text("重置", fontSize = 14.sp, color = BrandBlue, modifier = Modifier.padding(vertical = 7.dp).clickable { filterArea = ""; filterStatus = "" })
            }
        }

        LazyColumn(Modifier.fillMaxSize().padding(horizontal = 17.dp, vertical = 8.dp), contentPadding = PaddingValues(bottom = 24.dp)) {
            items(filtered, key = { it.id }) { rec ->
                RecordCard(rec)
            }
        }
    }
}

@Composable
private fun StatBlock(num: String, label: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(num, fontSize = 22.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
        Text(label, fontSize = 14.sp, color = TextTertiary)
    }
}

@Composable
private fun RecordCard(rec: Record) {
    Column(
        Modifier.fillMaxWidth().padding(bottom = 8.dp)
            .shadow(4.dp, RoundedCornerShape(12.dp)).clip(RoundedCornerShape(12.dp)).background(Color.White)
            .padding(horizontal = 15.dp, vertical = 15.dp)
    ) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text(rec.date, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
            Box(Modifier.clip(RoundedCornerShape(12.dp))
                .background(if (rec.issuesCount > 0) Color(0xFFFEF2F2) else Color(0xFFECFDF5))
                .padding(horizontal = 10.dp, vertical = 4.dp)) {
                Text(if (rec.issuesCount > 0) "${rec.issuesCount} 项问题" else "正常", fontSize = 14.sp,
                    color = if (rec.issuesCount > 0) Error else Success)
            }
        }
        Spacer(Modifier.height(10.dp))
        Row(Modifier.fillMaxWidth()) {
            Column(Modifier.weight(1f)) { Text("检测区域", fontSize = 14.sp, color = TextTertiary); Text(rec.area, fontSize = 14.sp, color = TextPrimary) }
            Column(Modifier.weight(1f)) { Text("任务编号", fontSize = 14.sp, color = TextTertiary); Text(rec.taskId, fontSize = 14.sp, color = TextPrimary) }
        }
        Spacer(Modifier.height(7.dp))
        Row(Modifier.fillMaxWidth()) {
            Column(Modifier.weight(1f)) { Text("检测时长", fontSize = 14.sp, color = TextTertiary); Text(rec.duration, fontSize = 14.sp, color = TextPrimary) }
            Column(Modifier.weight(1f)) { Text("操作员", fontSize = 14.sp, color = TextTertiary); Text(rec.operator, fontSize = 14.sp, color = TextPrimary) }
        }
        Spacer(Modifier.height(10.dp))
        Row(Modifier.fillMaxWidth().border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp)).padding(top = 8.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text(if (rec.issuesCount == 0) "全部正常" else "发现异常", fontSize = 14.sp, color = if (rec.issuesCount == 0) Success else Error)
            AppIcon("chevron-right", Modifier.size(11.dp), tint = Color(0xFFD1D5DB))
        }
    }
}
