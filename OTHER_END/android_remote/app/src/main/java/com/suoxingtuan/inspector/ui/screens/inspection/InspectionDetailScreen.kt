package com.suoxingtuan.inspector.ui.screens.inspection

import androidx.compose.animation.animateContentSize
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.ui.components.AppIcon
import com.suoxingtuan.inspector.ui.theme.*
import com.suoxingtuan.inspector.data.model.RiskLevel
import com.suoxingtuan.inspector.data.model.IssueStatus

@Composable
fun InspectionDetailScreen(
    onNavigateBack: () -> Unit,
    date: String = "2026-07-11"
) {
    val branches = remember {
        mutableStateListOf("tunnel_left", "tunnel_right", "station", "ventilation")
    }
    val issues = remember {
        mapOf(
            "tunnel_left" to listOf(
                Issue("1", "tunnel_left", "K12+350处衬砌裂缝（纵向）", "隧道B区 K12+350", RiskLevel.high, IssueStatus.pending),
                Issue("2", "tunnel_left", "K12+350处排水孔堵塞", "隧道B区 K12+350", RiskLevel.medium, IssueStatus.pending)
            ),
            "tunnel_right" to listOf(
                Issue("3", "tunnel_right", "排水沟堵塞", "隧道B区 K12+420", RiskLevel.medium, IssueStatus.reviewed)
            ),
            "station" to listOf(
                Issue("4", "station", "站台地面破损", "站台B区 3号出入口", RiskLevel.normal, IssueStatus.normal)
            ),
            "ventilation" to emptyList()
        )
    }

    var showMapModal by remember { mutableStateOf(false) }
    var selectedIssue by remember { mutableStateOf<Issue?>(null) }

    Column(Modifier.fillMaxSize().background(BgPage)) {
        // Nav bar
        Row(Modifier.fillMaxWidth().padding(start = 19.dp).height(35.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(35.dp).clip(RoundedCornerShape(50)).clickable { onNavigateBack() }, contentAlignment = Alignment.Center) {
                Text("‹", fontSize = 28.sp, color = TextPrimary, fontWeight = FontWeight.Light, modifier = Modifier.offset(y = (-2).dp))
            }
            Text("巡检详情", fontSize = 20.sp, fontWeight = FontWeight.Bold, color = TextPrimary, modifier = Modifier.padding(start = 8.dp))
        }

        LazyColumn(Modifier.fillMaxSize().padding(horizontal = 19.dp), contentPadding = PaddingValues(top = 10.dp, bottom = 24.dp)) {
            BRANCHES.forEach { branch ->
                val branchIssues = issues[branch.first] ?: emptyList()
                item(key = branch.first) {
                    BranchCard(branch, branchIssues,
                        onMapClick = { issue -> selectedIssue = issue; showMapModal = true })
                }
            }
        }
    }

    if (showMapModal && selectedIssue != null) {
        Box(Modifier.fillMaxSize().background(Color.Black.copy(0.45f)).clickable { showMapModal = false }, contentAlignment = Alignment.Center) {
            Column(
                Modifier.fillMaxWidth(0.85f).clip(RoundedCornerShape(21.dp)).background(Color.White).padding(horizontal = 17.dp, vertical = 19.dp)
            ) {
                Text("缺陷位置详情", fontSize = 17.sp, fontWeight = FontWeight.Medium,
                    textAlign = androidx.compose.ui.text.style.TextAlign.Center, modifier = Modifier.fillMaxWidth().padding(bottom = 15.dp))
                Box(Modifier.fillMaxWidth().height(115.dp).clip(RoundedCornerShape(14.dp)).background(BgCool), contentAlignment = Alignment.Center) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        AppIcon("map-pin", Modifier.size(31.dp), tint = BrandBlue)
                        Text(selectedIssue?.location ?: "", fontSize = 14.sp, color = TextSecondary, modifier = Modifier.padding(top = 8.dp))
                    }
                }
                Row(
                    Modifier.fillMaxWidth().padding(top = 12.dp).clip(RoundedCornerShape(11.dp)).background(Color(0xFFFFF5F5)).border(0.5.dp, SolidColor(Color(0xFFFECACA)), RoundedCornerShape(11.dp)).padding(12.dp),
                    verticalAlignment = Alignment.Top
                ) {
                    Box(Modifier.size(8.dp).clip(CircleShape).background(Error).padding(top = 3.dp))
                    Column(Modifier.padding(start = 8.dp)) {
                        Text("问题描述", fontSize = 11.sp, fontWeight = FontWeight.SemiBold, color = Error)
                        Text(selectedIssue?.title ?: "", fontSize = 14.sp, fontWeight = FontWeight.Medium, color = TextPrimary, lineHeight = 19.sp)
                    }
                }
                Box(Modifier.fillMaxWidth().padding(top = 12.dp).height(42.dp).clip(RoundedCornerShape(18.dp)).background(BgModule).clickable { showMapModal = false }, contentAlignment = Alignment.Center) {
                    Text("关闭", fontSize = 14.sp, color = TextSecondary)
                }
            }
        }
    }
}

@Composable
private fun BranchCard(
    branch: Triple<String, String, String>,
    issues: List<Issue>,
    onMapClick: (Issue) -> Unit
) {
    var expanded by remember { mutableStateOf(true) }

    Column(
        Modifier.fillMaxWidth().padding(bottom = 12.dp)
            .shadow(6.dp, RoundedCornerShape(21.dp)).clip(RoundedCornerShape(21.dp)).background(Color.White)
            .border(0.5.dp, SolidColor(BorderLight), RoundedCornerShape(21.dp))
    ) {
        Row(
            Modifier.fillMaxWidth().clickable { expanded = !expanded }.padding(horizontal = 15.dp, vertical = 13.dp),
            horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                AppIcon(branch.third, Modifier.size(18.dp), tint = TextPrimary)
                Spacer(Modifier.width(8.dp))
                Text(branch.second, fontSize = 16.sp, fontWeight = FontWeight.Medium, color = TextPrimary)
                if (issues.isNotEmpty()) {
                    Box(Modifier.padding(start = 6.dp).clip(RoundedCornerShape(16.dp)).background(AccentOrange).padding(horizontal = 8.dp, vertical = 3.dp)) {
                        Text("${issues.size}", fontSize = 11.sp, color = Color.White)
                    }
                }
            }
            Text("›", fontSize = 22.sp, color = Color(0xFFDADADA), fontWeight = FontWeight.Light,
                modifier = Modifier.rotate(if (expanded) 90f else 0f))
        }

        if (expanded) {
            Column(
                Modifier.fillMaxWidth().padding(horizontal = 15.dp).padding(bottom = 12.dp).animateContentSize()
            ) {
                if (issues.isEmpty()) {
                    Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                        AppIcon("check", Modifier.size(18.dp), tint = AccentMint)
                        Text("未发现问题", fontSize = 14.sp, color = AccentMint, modifier = Modifier.padding(start = 6.dp))
                    }
                } else {
                    issues.forEach { issue ->
                        Row(
                            Modifier.fillMaxWidth().padding(vertical = 10.dp).clip(RoundedCornerShape(12.dp)).background(BgPage).padding(horizontal = 12.dp, vertical = 10.dp),
                            verticalAlignment = Alignment.Top
                        ) {
                            Box(Modifier.size(8.dp).clip(CircleShape).background(issue.risk.color).padding(top = 3.dp))
                            Column(Modifier.weight(1f).padding(start = 7.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(issue.title, fontSize = 14.sp, color = TextPrimary, maxLines = 1, overflow = TextOverflow.Ellipsis, modifier = Modifier.weight(1f))
                                    Box(Modifier.clip(RoundedCornerShape(10.dp)).background(issue.status.bg).padding(horizontal = 8.dp, vertical = 3.dp)) {
                                        Text(issue.status.label, fontSize = 10.sp, color = issue.status.textColor)
                                    }
                                }
                                Row(Modifier.padding(top = 4.dp), verticalAlignment = Alignment.CenterVertically) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        AppIcon("map-pin", Modifier.size(13.dp), tint = TextTertiary)
                                        Text(issue.location, fontSize = 12.sp, color = TextTertiary, modifier = Modifier.padding(start = 3.dp))
                                    }
                                    Spacer(Modifier.weight(1f))
                                    Box(Modifier.clip(RoundedCornerShape(22.dp)).background(BgModule).clickable { onMapClick(issue) }.padding(horizontal = 12.dp, vertical = 6.dp)) {
                                        Text("查看位置", fontSize = 12.sp, color = BrandBlue, fontWeight = FontWeight.Medium)
                                    }
                                }
                            }
                        }
                        if (issues.last() != issue) Spacer(Modifier.height(7.dp))
                    }
                }
            }
        }
    }
}
