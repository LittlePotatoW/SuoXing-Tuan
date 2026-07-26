package com.suoxingtuan.inspector.ui.screens.inspection

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.ui.components.AppIcon
import com.suoxingtuan.inspector.ui.theme.*
import com.suoxingtuan.inspector.data.model.RiskLevel
import com.suoxingtuan.inspector.data.model.IssueStatus

data class Issue(
    val id: String, val branch: String, val title: String,
    val location: String, val risk: RiskLevel, val status: IssueStatus
)
data class DateGroup(val date: String, val issues: List<Issue>)

val BRANCHES = listOf(
    Triple("tunnel_left", "左线隧道", "layers"),
    Triple("tunnel_right", "右线隧道", "layers"),
    Triple("station", "站台区", "map-pin"),
    Triple("ventilation", "通风井", "tool")
)

@Composable
fun InspectionListScreen(
    onNavigateToDetail: (String) -> Unit
) {
    var searchText by remember { mutableStateOf("") }
    val todayFull = "2026年7月21日 星期三"
    var showAddModal by remember { mutableStateOf(false) }

    // Mock data
    val groups = remember {
        mutableStateListOf(
            DateGroup("2026-07-11", listOf(
                Issue("1", "tunnel_left", "K12+350处衬砌裂缝（纵向）", "隧道B区 K12+350", RiskLevel.high, IssueStatus.pending),
                Issue("2", "tunnel_right", "排水沟堵塞", "隧道B区 K12+420", RiskLevel.medium, IssueStatus.reviewed),
                Issue("3", "station", "站台地面破损", "站台B区 3号出入口", RiskLevel.normal, IssueStatus.normal),
                Issue("4", "ventilation", "通风井防护网松动", "隧道B区 K13+050", RiskLevel.medium, IssueStatus.pending)
            )),
            DateGroup("2026-07-10", listOf(
                Issue("5", "tunnel_left", "K13+100处渗水", "隧道A区 K13+100", RiskLevel.medium, IssueStatus.pending)
            ))
        )
    }

    val filteredGroups = remember(searchText, groups.toList()) {
        if (searchText.isBlank()) groups.toList()
        else groups.mapNotNull { g ->
            val filtered = g.issues.filter { it.title.contains(searchText, true) || it.location.contains(searchText, true) }
            if (filtered.isEmpty()) null else DateGroup(g.date, filtered)
        }
    }

    Column(Modifier.fillMaxSize().background(BgPage)) {
        // Nav bar
        Row(
            Modifier.fillMaxWidth().padding(start = 23.dp).height(35.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(todayFull, fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
            Row(
                Modifier
                    .clip(RoundedCornerShape(22.dp))
                    .background(BrandBlue)
                    .clickable { showAddModal = true }
                    .padding(horizontal = 14.dp, vertical = 7.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                AppIcon("plus-circle", Modifier.size(14.dp), tint = Color.White)
                Spacer(Modifier.width(5.dp))
                Text("添加", fontSize = 13.sp, color = Color.White)
            }
        }

        // Search bar
        Row(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 19.dp, vertical = 8.dp)
                .height(38.dp)
                .clip(RoundedCornerShape(22.dp))
                .background(Color.White)
                .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(22.dp))
                .padding(horizontal = 14.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            AppIcon("search", Modifier.size(16.dp), tint = TextTertiary)
            Spacer(Modifier.width(8.dp))
            BasicTextField(
                value = searchText, onValueChange = { searchText = it },
                modifier = Modifier.weight(1f).height(38.dp),
                textStyle = androidx.compose.ui.text.TextStyle(fontSize = 14.sp, color = TextPrimary),
                cursorBrush = SolidColor(Color.Black), singleLine = true,
                decorationBox = { inner -> Box { if (searchText.isEmpty()) Text("搜索问题或位置...", fontSize = 14.sp, color = TextPlaceholder); inner() } }
            )
            if (searchText.isNotEmpty()) {
                Box(Modifier.size(20.dp).clip(CircleShape).background(BgModule).clickable { searchText = "" }, contentAlignment = Alignment.Center) {
                    Text("✕", fontSize = 11.sp, color = TextTertiary, fontWeight = FontWeight.SemiBold)
                }
            }
        }

        // List
        LazyColumn(Modifier.fillMaxSize().padding(horizontal = 19.dp), contentPadding = PaddingValues(bottom = 16.dp)) {
            if (filteredGroups.isEmpty()) {
                item {
                    Column(Modifier.fillMaxWidth().padding(top = 77.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        Box(Modifier.size(58.dp).clip(CircleShape).background(BgModule), contentAlignment = Alignment.Center) {
                            AppIcon("clipboard", Modifier.size(27.dp), tint = TextTertiary)
                        }
                        Text(if (searchText.isEmpty()) "暂无巡检记录" else "未找到匹配记录", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = TextSecondary, modifier = Modifier.padding(top = 8.dp))
                        Text(if (searchText.isEmpty()) "点击右上角「添加」创建第一条记录" else "换个关键词试试", fontSize = 13.sp, color = TextTertiary, modifier = Modifier.padding(top = 4.dp))
                    }
                }
            }
            items(filteredGroups, key = { it.date }) { group ->
                DateGroupCard(group, onClick = { onNavigateToDetail(group.date) })
            }
        }
    }

    // Add modal
    if (showAddModal) {
        AddInspectionModal(onDismiss = { showAddModal = false }, onAdd = { showAddModal = false })
    }
}

@Composable
private fun DateGroupCard(group: DateGroup, onClick: () -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(bottom = 12.dp)
            .shadow(6.dp, RoundedCornerShape(21.dp))
            .clip(RoundedCornerShape(21.dp))
            .background(Color.White)
            .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(21.dp))
    ) {
        // Header
        Row(
            Modifier.fillMaxWidth().clickable { onClick() }.padding(horizontal = 15.dp, vertical = 13.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(group.date.replace("-", "月", ).replaceFirst("2026", "").let { it + "日" }.removePrefix("0"), fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
            Spacer(Modifier.weight(1f))
            Box(Modifier.clip(RoundedCornerShape(16.dp)).background(AccentOrange).padding(horizontal = 10.dp, vertical = 4.dp)) {
                Text("${group.issues.size} 项问题", fontSize = 11.sp, color = Color.White)
            }
            Spacer(Modifier.width(8.dp))
            AppIcon("chevron-right", Modifier.size(14.dp), tint = Color(0xFFDADADA))
        }
        // Body
        Column(
            Modifier.fillMaxWidth().border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(0.dp)).padding(horizontal = 15.dp, vertical = 10.dp)
        ) {
            BRANCHES.forEach { b ->
                val branchIssues = group.issues.filter { it.branch == b.first }
                if (branchIssues.isNotEmpty()) {
                    Row(Modifier.padding(bottom = 7.dp), verticalAlignment = Alignment.CenterVertically) {
                        AppIcon(b.third, Modifier.size(16.dp), tint = BrandBlue)
                        Spacer(Modifier.width(6.dp))
                        Text(b.second, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = TextPrimary)
                        Spacer(Modifier.weight(1f))
                        Box(Modifier.size(21.dp).clip(CircleShape).background(BgModule), contentAlignment = Alignment.Center) {
                            Text("${branchIssues.size}", fontSize = 12.sp, fontWeight = FontWeight.SemiBold, color = TextSecondary)
                        }
                    }
                    branchIssues.forEach { issue ->
                        Row(
                            Modifier.padding(start = 2.dp, top = 9.dp, bottom = 9.dp).border(0.5.dp, SolidColor(Color(0xFFF5F5F5)), RoundedCornerShape(0.dp)),
                            verticalAlignment = Alignment.Top
                        ) {
                            Box(Modifier.size(8.dp).clip(CircleShape).background(issue.risk.color).padding(top = 3.dp))
                            Spacer(Modifier.width(7.dp))
                            Column(Modifier.weight(1f)) {
                                Row(verticalAlignment = Alignment.Top) {
                                    Text(issue.title, fontSize = 14.sp, fontWeight = FontWeight.Medium, color = TextPrimary,
                                        maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                                    Box(Modifier.clip(RoundedCornerShape(10.dp)).background(issue.status.bg).padding(horizontal = 8.dp, vertical = 3.dp)) {
                                        Text(issue.status.label, fontSize = 10.sp, color = issue.status.textColor)
                                    }
                                }
                                Row(Modifier.padding(top = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                                    AppIcon("map-pin", Modifier.size(11.dp), tint = TextTertiary)
                                    Text(issue.location, fontSize = 12.sp, color = TextTertiary, modifier = Modifier.padding(start = 4.dp))
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun AddInspectionModal(onDismiss: () -> Unit, onAdd: () -> Unit) {
    var title by remember { mutableStateOf("") }
    var location by remember { mutableStateOf("") }
    val branchNames = BRANCHES.map { it.second }
    var branchIdx by remember { mutableIntStateOf(0) }
    val riskLevels = RiskLevel.entries
    var riskIdx by remember { mutableIntStateOf(0) }
    val statuses = IssueStatus.entries
    var statusIdx by remember { mutableIntStateOf(0) }

    Box(Modifier.fillMaxSize().background(Color.Black.copy(0.45f)).clickable { onDismiss() }, contentAlignment = Alignment.Center) {
        Column(
            Modifier.fillMaxWidth().padding(23.dp).clip(RoundedCornerShape(21.dp)).background(Color.White).padding(horizontal = 17.dp, vertical = 21.dp)
        ) {
            Text("添加巡检记录", fontSize = 18.sp, fontWeight = FontWeight.SemiBold, textAlign = androidx.compose.ui.text.style.TextAlign.Center,
                modifier = Modifier.fillMaxWidth().padding(bottom = 19.dp))
            // Branch picker - simplified
            Row(Modifier.fillMaxWidth().padding(bottom = 12.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                BRANCHES.forEachIndexed { i, b ->
                    Box(Modifier.clip(RoundedCornerShape(12.dp)).background(if (i == branchIdx) BrandBlue else BgModule)
                        .clickable { branchIdx = i }.padding(horizontal = 10.dp, vertical = 6.dp)) {
                        Text(b.second, fontSize = 13.sp, color = if (i == branchIdx) Color.White else TextPrimary)
                    }
                }
            }
            OutlinedTextField(value = title, onValueChange = { if (it.length <= 50) title = it }, label = { Text("问题描述") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            Spacer(Modifier.height(8.dp))
            OutlinedTextField(value = location, onValueChange = { if (it.length <= 30) location = it }, label = { Text("位置") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
            Spacer(Modifier.height(8.dp))
            // Risk & Status row
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Row(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    riskLevels.forEachIndexed { i, r ->
                        Box(Modifier.clip(RoundedCornerShape(10.dp)).background(if (i == riskIdx) r.color.copy(0.2f) else BgModule)
                            .clickable { riskIdx = i }.padding(horizontal = 8.dp, vertical = 4.dp)) {
                            Text(r.label, fontSize = 12.sp, color = if (i == riskIdx) r.color else TextTertiary)
                        }
                    }
                }
                Row(Modifier.weight(1f), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    statuses.take(3).forEachIndexed { i, s ->
                        Box(Modifier.clip(RoundedCornerShape(10.dp)).background(if (i == statusIdx) s.bg else BgModule)
                            .clickable { statusIdx = i }.padding(horizontal = 8.dp, vertical = 4.dp)) {
                            Text(s.label, fontSize = 12.sp, color = if (i == statusIdx) s.textColor else TextTertiary)
                        }
                    }
                }
            }
            Spacer(Modifier.height(16.dp))
            // Action buttons
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Box(Modifier.weight(1f).height(46.dp).clip(RoundedCornerShape(18.dp)).background(BgModule).clickable { onDismiss() }, contentAlignment = Alignment.Center) {
                    Text("取消", fontSize = 15.sp, fontWeight = FontWeight.SemiBold, color = TextSecondary)
                }
                Box(Modifier.weight(1f).height(46.dp).clip(RoundedCornerShape(18.dp)).background(BrandBlue).clickable { onAdd() }, contentAlignment = Alignment.Center) {
                    Text("确认添加", fontSize = 15.sp, fontWeight = FontWeight.SemiBold, color = Color.White)
                }
            }
        }
    }
}
