package com.suoxingtuan.inspector.ui.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.*
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector

/**
 * Icon component replicating the original AppIcon.vue behavior.
 * Maps 48 feather-style SVG icons to Material Icons Outlined equivalents.
 */
object AppIcons {
    val home: ImageVector get() = Icons.Outlined.Home
    val clipboard: ImageVector get() = Icons.Outlined.ContentPaste
    val user: ImageVector get() = Icons.Outlined.Person
    val mapPin: ImageVector get() = Icons.Outlined.LocationOn
    val crosshair: ImageVector get() = Icons.Outlined.GpsFixed
    val layers: ImageVector get() = Icons.Outlined.Layers
    val target: ImageVector get() = Icons.Outlined.TrackChanges
    val map: ImageVector get() = Icons.Outlined.Map
    val battery: ImageVector get() = Icons.Outlined.BatteryStd
    val signal: ImageVector get() = Icons.Outlined.SignalCellularAlt
    val wifi: ImageVector get() = Icons.Outlined.Wifi
    val radio: ImageVector get() = Icons.Outlined.Radio
    val tool: ImageVector get() = Icons.Outlined.Build
    val gauge: ImageVector get() = Icons.Outlined.Speed
    val camera: ImageVector get() = Icons.Outlined.CameraAlt
    val stopCircle: ImageVector get() = Icons.Outlined.Cancel
    val playCircle: ImageVector get() = Icons.Outlined.PlayCircle
    val plusCircle: ImageVector get() = Icons.Outlined.AddCircle
    val check: ImageVector get() = Icons.Outlined.Check
    val square: ImageVector get() = Icons.Outlined.CropSquare
    val chevronRight: ImageVector get() = Icons.Outlined.ChevronRight
    val chevronDown: ImageVector get() = Icons.Outlined.KeyboardArrowDown
    val chevronUp: ImageVector get() = Icons.Outlined.KeyboardArrowUp
    val chevronLeft: ImageVector get() = Icons.Outlined.ChevronLeft
    val moreHorizontal: ImageVector get() = Icons.Outlined.MoreHoriz
    val arrowUp: ImageVector get() = Icons.Outlined.KeyboardArrowUp
    val arrowDown: ImageVector get() = Icons.Outlined.KeyboardArrowDown
    val arrowLeft: ImageVector get() = Icons.Outlined.KeyboardArrowLeft
    val arrowRight: ImageVector get() = Icons.Outlined.KeyboardArrowRight
    val settings: ImageVector get() = Icons.Outlined.Settings
    val helpCircle: ImageVector get() = Icons.Outlined.Help
    val info: ImageVector get() = Icons.Outlined.Info
    val fileText: ImageVector get() = Icons.Outlined.Description
    val bell: ImageVector get() = Icons.Outlined.Notifications
    val edit: ImageVector get() = Icons.Outlined.Edit
    val alertTriangle: ImageVector get() = Icons.Outlined.Warning
    val hammer: ImageVector get() = Icons.Outlined.Handyman
    val phone: ImageVector get() = Icons.Outlined.Phone
    val messageCircle: ImageVector get() = Icons.Outlined.Message
    val shield: ImageVector get() = Icons.Outlined.Shield
    val search: ImageVector get() = Icons.Outlined.Search
    val logOut: ImageVector get() = Icons.Outlined.Logout
    val archive: ImageVector get() = Icons.Outlined.Archive
    val zap: ImageVector get() = Icons.Outlined.Bolt
    val menu: ImageVector get() = Icons.Outlined.Menu
    val maximize2: ImageVector get() = Icons.Outlined.Fullscreen
    val userPlus: ImageVector get() = Icons.Outlined.PersonAdd
    val trash: ImageVector get() = Icons.Outlined.Delete
}

@Composable
fun AppIcon(
    name: String,
    modifier: Modifier = Modifier,
    tint: Color = Color(0xFF333333)
) {
    val icon = when (name) {
        "home" -> AppIcons.home
        "clipboard" -> AppIcons.clipboard
        "user" -> AppIcons.user
        "map-pin" -> AppIcons.mapPin
        "crosshair" -> AppIcons.crosshair
        "layers" -> AppIcons.layers
        "target" -> AppIcons.target
        "map" -> AppIcons.map
        "battery" -> AppIcons.battery
        "signal" -> AppIcons.signal
        "wifi" -> AppIcons.wifi
        "radio" -> AppIcons.radio
        "tool" -> AppIcons.tool
        "gauge" -> AppIcons.gauge
        "camera" -> AppIcons.camera
        "stop-circle" -> AppIcons.stopCircle
        "play-circle" -> AppIcons.playCircle
        "plus-circle" -> AppIcons.plusCircle
        "check" -> AppIcons.check
        "square" -> AppIcons.square
        "chevron-right" -> AppIcons.chevronRight
        "chevron-down" -> AppIcons.chevronDown
        "chevron-up" -> AppIcons.chevronUp
        "chevron-left" -> AppIcons.chevronLeft
        "more-horizontal" -> AppIcons.moreHorizontal
        "arrow-up" -> AppIcons.arrowUp
        "arrow-down" -> AppIcons.arrowDown
        "arrow-left" -> AppIcons.arrowLeft
        "arrow-right" -> AppIcons.arrowRight
        "settings" -> AppIcons.settings
        "help-circle" -> AppIcons.helpCircle
        "info" -> AppIcons.info
        "file-text" -> AppIcons.fileText
        "bell" -> AppIcons.bell
        "edit" -> AppIcons.edit
        "alert-triangle" -> AppIcons.alertTriangle
        "hammer" -> AppIcons.hammer
        "phone" -> AppIcons.phone
        "message-circle" -> AppIcons.messageCircle
        "shield" -> AppIcons.shield
        "search" -> AppIcons.search
        "log-out" -> AppIcons.logOut
        "archive" -> AppIcons.archive
        "zap" -> AppIcons.zap
        "menu" -> AppIcons.menu
        "maximize-2" -> AppIcons.maximize2
        "user-plus" -> AppIcons.userPlus
        "trash" -> AppIcons.trash
        else -> AppIcons.helpCircle
    }

    Icon(
        imageVector = icon,
        contentDescription = name,
        modifier = modifier,
        tint = tint
    )
}
