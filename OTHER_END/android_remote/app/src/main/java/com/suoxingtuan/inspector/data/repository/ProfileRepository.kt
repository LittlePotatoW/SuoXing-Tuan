package com.suoxingtuan.inspector.data.repository

import com.suoxingtuan.inspector.data.local.Preferences
import com.suoxingtuan.inspector.data.model.*

/**
 * Profile + Team repository — mirrors profileStore.ts.
 */
object ProfileRepository {
    private const val PROFILE_KEY = "user_profile"
    private const val TEAM_KEY = "team_members"
    private const val INVITE_KEY = "team_invitations"

    val STATUS_OPTIONS = listOf(
        StatusOption("online", "在线", "#4cd964"),
        StatusOption("busy", "忙碌", "#f0ad4e"),
        StatusOption("offline", "离线", "#999")
    )

    private val DEFAULT_PROFILE = ProfileData()

    private val DEFAULT_TEAM = listOf(
        TeamMember("1", "张伟", "", "", "online", "owner"),
        TeamMember("2", "李明", "", "", "offline", "member")
    )

    // ---- Profile ----

    fun getProfile(): ProfileData = Preferences.getObject<ProfileData>(PROFILE_KEY) ?: DEFAULT_PROFILE
    fun saveProfile(data: ProfileData) = Preferences.setObject(PROFILE_KEY, data)

    fun getStatusInfo(status: String): StatusOption =
        STATUS_OPTIONS.find { it.value == status } ?: STATUS_OPTIONS[0]
    fun getStatusText(status: String): String =
        STATUS_OPTIONS.find { it.value == status }?.label ?: "离线"

    // ---- Team ----

    fun getTeamMembers(): List<TeamMember> {
        val saved = Preferences.getObject<List<TeamMember>>(TEAM_KEY)
        return if (saved.isNullOrEmpty()) { Preferences.setObject(TEAM_KEY, DEFAULT_TEAM); DEFAULT_TEAM } else saved
    }

    fun saveTeamMembers(members: List<TeamMember>) = Preferences.setObject(TEAM_KEY, members)

    // ---- Invitations ----

    fun getInvitations(): List<TeamInvitation> =
        Preferences.getObject<List<TeamInvitation>>(INVITE_KEY) ?: emptyList()

    private fun saveInvitations(list: List<TeamInvitation>) = Preferences.setObject(INVITE_KEY, list)

    fun getPendingInvitations(): List<TeamInvitation> =
        getInvitations().filter { it.status == "pending" }

    fun inviteMemberByPhone(phone: String): AuthResult {
        if (phone.length < 11) return AuthResult(false, "请输入正确的11位手机号")
        val members = getTeamMembers()
        if (members.any { it.phone == phone }) return AuthResult(false, "该成员已在团队中")
        val invites = getInvitations()
        if (invites.any { it.phone == phone && it.status == "pending" }) return AuthResult(false, "已向该用户发送过邀请")
        val users = AuthRepository.getUsers()
        val user = users.find { it.phone == phone } ?: return AuthResult(false, "该手机号未注册，无法发送邀请")
        val newInvite = TeamInvitation(
            System.currentTimeMillis().toString(), phone, user.nickname,
            java.time.Instant.now().toString(), "pending"
        )
        val updated = invites.toMutableList().apply { add(newInvite) }
        saveInvitations(updated)
        return AuthResult(true, "已向 ${user.nickname} 发送组队邀请")
    }

    fun acceptInvitation(inviteId: String): TeamMember? {
        val invites = getInvitations()
        val inv = invites.find { it.id == inviteId && it.status == "pending" } ?: return null
        val updatedInvites = invites.map { if (it.id == inviteId) it.copy(status = "accepted") else it }
        saveInvitations(updatedInvites)
        val members = getTeamMembers().toMutableList()
        val newMember = TeamMember(
            System.currentTimeMillis().toString(), inv.name, inv.phone,
            "", "online", "member"
        )
        members.add(newMember)
        saveTeamMembers(members)
        return newMember
    }

    fun rejectInvitation(inviteId: String) {
        val invites = getInvitations().map { if (it.id == inviteId) it.copy(status = "rejected") else it }
        saveInvitations(invites)
    }
}
