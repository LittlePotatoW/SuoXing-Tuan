package com.suoxingtuan.inspector.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

// Custom colors not in Material3 scheme
@Immutable
data class AppColors(
    val brandBlue: Color = BrandBlue,
    val brandBlueHover: Color = BrandBlueHover,
    val primaryBlack: Color = PrimaryBlack,
    val accentOrange: Color = AccentOrange,
    val accentMint: Color = AccentMint,
    val success: Color = Success,
    val bgModule: Color = BgModule,
    val bgWarm: Color = BgWarm,
    val bgCool: Color = BgCool,
    val bgMask: Color = BgMask,
    val bgGlass: Color = Color.White.copy(alpha = 0.88f),
    val textTertiary: Color = TextTertiary,
    val textPlaceholder: Color = TextPlaceholder,
    val borderLight: Color = BorderLight,
    val borderStrong: Color = BorderStrong,
    val borderActive: Color = BorderActive,
    val shadowWeak: Color = Color.Black.copy(alpha = 0.04f),
    val shadowStandard: Color = Color.Black.copy(alpha = 0.06f),
    val shadowFloat: Color = Color.Black.copy(alpha = 0.12f)
)

val LocalAppColors = androidx.compose.runtime.staticCompositionLocalOf {
    AppColors()
}

private val LightColorScheme = lightColorScheme(
    primary = BrandBlue,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFD6E2FF),
    onPrimaryContainer = Color(0xFF001A41),
    secondary = Color(0xFF545F70),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFD8E3F8),
    onSecondaryContainer = Color(0xFF111C2B),
    tertiary = AccentOrange,
    onTertiary = Color.White,
    error = Error,
    onError = Color.White,
    background = BgPage,
    onBackground = TextPrimary,
    surface = BgCard,
    onSurface = TextPrimary,
    onSurfaceVariant = TextSecondary,
    surfaceVariant = BgModule,
    outline = BorderDefault,
    outlineVariant = BorderLight,
    inverseSurface = Color(0xFF2F3033),
    inverseOnSurface = Color(0xFFF1F0F4)
)

@Composable
fun SuoXingTuAnTheme(
    content: @Composable () -> Unit
) {
    MaterialTheme(
        colorScheme = LightColorScheme,
        typography = AppTypography,
        content = content
    )
}
