package com.suoxingtuan.inspector.navigation

sealed class Screen(val route: String) {
    data object Login : Screen("login")
    data object Home : Screen("home")
    data object Control : Screen("control")
    data object InspectionList : Screen("inspection")
    data object InspectionDetail : Screen("inspection/{id}") {
        fun createRoute(id: String) = "inspection/$id"
    }
    data object Profile : Screen("profile")
    data object ProfileEdit : Screen("profile/edit")
    data object PasswordChange : Screen("password/change")
    data object Notification : Screen("notification")
    data object Records : Screen("records")
    data object Settings : Screen("settings")
    data object Feedback : Screen("feedback")
    data object TaskDetail : Screen("task/{id}") {
        fun createRoute(id: String) = "task/$id"
    }
    data object Team : Screen("team")
}

// Bottom tab destinations
enum class BottomTab(val route: String, val label: String, val icon: String) {
    Inspection("inspection", "巡检", "clipboard"),
    Home("home", "首页", "home"),
    Profile("profile", "我的", "user")
}
