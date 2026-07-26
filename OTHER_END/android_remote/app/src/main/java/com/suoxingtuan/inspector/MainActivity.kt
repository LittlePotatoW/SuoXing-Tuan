package com.suoxingtuan.inspector

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.suoxingtuan.inspector.navigation.BottomTab
import com.suoxingtuan.inspector.navigation.Screen
import com.suoxingtuan.inspector.ui.components.AppBottomBar
import com.suoxingtuan.inspector.ui.screens.login.LoginScreen
import com.suoxingtuan.inspector.ui.screens.home.HomeScreen
import com.suoxingtuan.inspector.ui.screens.feedback.FeedbackScreen
import com.suoxingtuan.inspector.ui.screens.notification.NotificationScreen
import com.suoxingtuan.inspector.ui.screens.password.PasswordChangeScreen
import com.suoxingtuan.inspector.ui.screens.profile.ProfileEditScreen
import com.suoxingtuan.inspector.ui.screens.profile.ProfileScreen
import com.suoxingtuan.inspector.ui.screens.settings.SettingsScreen
import com.suoxingtuan.inspector.ui.screens.control.ControlScreen
import com.suoxingtuan.inspector.ui.screens.inspection.InspectionDetailScreen
import com.suoxingtuan.inspector.ui.screens.inspection.InspectionListScreen
import com.suoxingtuan.inspector.ui.screens.records.RecordsScreen
import com.suoxingtuan.inspector.ui.screens.task.TaskDetailScreen
import com.suoxingtuan.inspector.ui.screens.team.TeamScreen
import com.suoxingtuan.inspector.ui.theme.SuoXingTuAnTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            SuoXingTuAnTheme {
                SuoXingTuAnApp()
            }
        }
    }
}

@Composable
fun SuoXingTuAnApp() {
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route ?: Screen.Login.route

    // Show bottom bar only on main tabs
    val showBottomBar = currentRoute in BottomTab.entries.map { it.route }

    Scaffold(
        modifier = Modifier.fillMaxSize(),
        bottomBar = {
            if (showBottomBar) {
                AppBottomBar(
                    currentRoute = currentRoute,
                    onTabSelected = { tab ->
                        navController.navigate(tab.route) {
                            popUpTo(navController.graph.findStartDestination().id) {
                                saveState = true
                            }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                )
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Home.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(Screen.Login.route) {
                LoginScreen(
                    onLoginSuccess = {
                        navController.navigate(Screen.Home.route) {
                            popUpTo(Screen.Login.route) { inclusive = true }
                        }
                    }
                )
            }
            composable(Screen.Home.route) {
                HomeScreen(
                    onNavigateToControl = {
                        navController.navigate(Screen.Control.route)
                    },
                    onNavigateToTask = { id ->
                        navController.navigate(Screen.TaskDetail.createRoute(id))
                    }
                )
            }
            composable(Screen.Control.route) {
                ControlScreen(onNavigateBack = { navController.popBackStack() })
            }
            composable(Screen.InspectionList.route) {
                InspectionListScreen(
                    onNavigateToDetail = { date ->
                        navController.navigate(Screen.InspectionDetail.createRoute(date))
                    }
                )
            }
            composable(Screen.InspectionDetail.route) { backStackEntry ->
                val date = backStackEntry.arguments?.getString("id") ?: "2026-07-11"
                InspectionDetailScreen(onNavigateBack = { navController.popBackStack() }, date = date)
            }
            composable(Screen.Profile.route) {
                ProfileScreen(
                    onNavigateToEdit = { navController.navigate(Screen.ProfileEdit.route) },
                    onNavigateToRecords = { navController.navigate(Screen.Records.route) },
                    onNavigateToNotification = { navController.navigate(Screen.Notification.route) },
                    onNavigateToSettings = { navController.navigate(Screen.Settings.route) },
                    onNavigateToFeedback = { navController.navigate(Screen.Feedback.route) },
                    onNavigateToTeam = { navController.navigate(Screen.Team.route) },
                    onLogout = {
                        navController.navigate(Screen.Login.route) {
                            popUpTo(0) { inclusive = true }
                        }
                    }
                )
            }
            composable(Screen.ProfileEdit.route) {
                ProfileEditScreen(onNavigateBack = { navController.popBackStack() })
            }
            composable(Screen.PasswordChange.route) {
                PasswordChangeScreen(onNavigateBack = { navController.popBackStack() })
            }
            composable(Screen.Notification.route) {
                NotificationScreen(
                    onNavigateBack = { navController.popBackStack() },
                    onNavigateToTask = { navController.navigate(Screen.TaskDetail.createRoute("0")) },
                    onNavigateToInspection = { navController.navigate(Screen.InspectionList.route) }
                )
            }
            composable(Screen.Records.route) {
                RecordsScreen(onNavigateBack = { navController.popBackStack() })
            }
            composable(Screen.Settings.route) {
                SettingsScreen(
                    onNavigateBack = { navController.popBackStack() },
                    onNavigateToProfileEdit = { navController.navigate(Screen.ProfileEdit.route) },
                    onNavigateToPasswordChange = { navController.navigate(Screen.PasswordChange.route) },
                    onLogout = {
                        navController.navigate(Screen.Login.route) {
                            popUpTo(0) { inclusive = true }
                        }
                    }
                )
            }
            composable(Screen.Feedback.route) {
                FeedbackScreen(onNavigateBack = { navController.popBackStack() })
            }
            composable(Screen.TaskDetail.route) { backStackEntry ->
                val id = backStackEntry.arguments?.getString("id") ?: "0"
                TaskDetailScreen(onNavigateBack = { navController.popBackStack() }, taskId = id)
            }
            composable(Screen.Team.route) {
                TeamScreen(onNavigateBack = { navController.popBackStack() })
            }
        }
    }
}

@Composable
fun PlaceholderScreen(title: String) {
    androidx.compose.foundation.layout.Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = androidx.compose.ui.Alignment.Center
    ) {
        androidx.compose.material3.Text(
            text = title,
            style = androidx.compose.material3.MaterialTheme.typography.headlineMedium
        )
    }
}
