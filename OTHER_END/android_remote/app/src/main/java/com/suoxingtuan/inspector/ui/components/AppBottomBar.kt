package com.suoxingtuan.inspector.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.suoxingtuan.inspector.navigation.BottomTab
import com.suoxingtuan.inspector.ui.theme.BorderLight

@Composable
fun AppBottomBar(
    currentRoute: String,
    onTabSelected: (BottomTab) -> Unit,
    modifier: Modifier = Modifier
) {
    Box(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 6.dp)
            .height(63.dp)
            .shadow(
                elevation = 8.dp,
                shape = RoundedCornerShape(topStart = 17.dp, topEnd = 17.dp)
            )
            .background(
                color = Color.White.copy(alpha = 0.95f),
                shape = RoundedCornerShape(topStart = 17.dp, topEnd = 17.dp)
            )
            .border(
                width = 0.5.dp,
                color = BorderLight,
                shape = RoundedCornerShape(topStart = 17.dp, topEnd = 17.dp)
            )
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 8.dp),
            horizontalArrangement = Arrangement.SpaceEvenly
        ) {
            BottomTab.entries.forEach { tab ->
                val isActive = currentRoute == tab.route
                BottomTabItem(
                    tab = tab,
                    isActive = isActive,
                    onClick = { onTabSelected(tab) }
                )
            }
        }
    }
}

@Composable
private fun BottomTabItem(
    tab: BottomTab,
    isActive: Boolean,
    onClick: () -> Unit
) {
    val activeColor = Color(0xFF466CAC)
    val inactiveColor = Color(0xFF9AA2AD)
    val activeTextColor = Color(0xFF111111)
    val inactiveTextColor = Color(0xFF8E8E8E)

    Column(
        modifier = Modifier
            .clickable(
                interactionSource = remember { MutableInteractionSource() },
                indication = null,
                onClick = onClick
            )
            .padding(top = 2.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(2.dp)
    ) {
        AppIcon(
            name = tab.icon,
            modifier = Modifier.size(22.dp),
            tint = if (isActive) activeColor else inactiveColor
        )
        Text(
            text = tab.label,
            fontSize = 10.sp,
            fontWeight = FontWeight.Medium,
            color = if (isActive) activeTextColor else inactiveTextColor,
            lineHeight = 12.sp
        )
    }
}
