package com.suoxingtuan.inspector.ui.theme

import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

/**
 * Convert uni-app rpx to Android dp.
 * uni-app: 750rpx = screen width
 * Android: screenWidthDp ≈ 360 (varies by device)
 *
 * Formula: dp = rpx * screenWidthDp / 750
 */
@Composable
fun rpx(value: Float): Dp {
    val screenWidthDp = LocalConfiguration.current.screenWidthDp
    return (value * screenWidthDp / 750f).dp
}

@Composable
fun rpx(value: Int): Dp = rpx(value.toFloat())

// Common sizes from uni.scss converted from rpx → dp (approx at 360dp screen)
// These are for convenience when you need a quick value

// Spacing (4px grid)
val SpaceXs = 2.dp      //  8rpx
val SpaceSm = 4.dp      // 16rpx
val SpaceBase = 6.dp    // 24rpx
val SpaceMd = 8.dp      // 32rpx
val SpaceLg = 10.dp     // 40rpx
val SpaceXl = 12.dp     // 48rpx
val Space2xl = 16.dp    // 64rpx
val Space3xl = 20.dp    // 80rpx

// Radii
val RadiusSm = 2.dp     //  8rpx
val RadiusBase = 4.dp   // 16rpx
val RadiusMd = 5.dp     // 20rpx
val RadiusLg = 6.dp     // 24rpx
val RadiusXl = 8.dp     // 32rpx
val RadiusPill = 999.dp // 999rpx (pill/capsule)

// Button height
val BtnHeightPrimary = 25.dp  // 104rpx
val BtnHeightSmall = 22.dp    //  88rpx
