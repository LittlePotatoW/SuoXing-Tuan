/**
 * Profile store — persists user profile data in uni.storage.
 */
import { getStorage, setStorage } from './storage'
import { getUsers } from './userStore'

export interface ProfileData {
  avatar: string // local file path or empty
  nickname: string
  intro: string
  status: 'online' | 'busy' | 'offline'
  gender?: string // '男' | '女' | '不公开'
}

const PROFILE_KEY = 'user_profile'

export const STATUS_OPTIONS = [
  { value: 'online' as const, label: '在线', color: '#4cd964' },
  { value: 'busy' as const, label: '忙碌', color: '#f0ad4e' },
  { value: 'offline' as const, label: '离线', color: '#999' },
]

const DEFAULT_PROFILE: ProfileData = {
  avatar: '',
  nickname: '巡检员',
  intro: '隧道检测工程师',
  status: 'online',
}

export function getProfile(): ProfileData {
  const stored = getStorage<ProfileData>(PROFILE_KEY)
  return stored || { ...DEFAULT_PROFILE }
}

export function saveProfile(data: ProfileData): void {
  setStorage(PROFILE_KEY, data)
}

/** Get status display info for a given status value. */
export function getStatusInfo(status: ProfileData['status']) {
  return STATUS_OPTIONS.find((s) => s.value === status) || STATUS_OPTIONS[0]
}

// ---- Team members + Invitations (持久化 + 邀请制) ----

const TEAM_KEY = 'team_members'
const INVITE_KEY = 'team_invitations'

export interface TeamMember {
  id: string
  name: string
  phone: string
  avatar: string
  status: 'online' | 'offline' | 'busy'
  role: 'owner' | 'member'
}

export interface TeamInvitation {
  id: string
  phone: string
  name: string
  createdAt: string
  status: 'pending' | 'accepted' | 'rejected'
}

const DEFAULT_TEAM: TeamMember[] = [
  { id: '1', name: '张伟', phone: '', avatar: '', status: 'online', role: 'owner' },
  { id: '2', name: '李明', phone: '', avatar: '', status: 'offline', role: 'member' },
]

/** Get display text for team member status — reuses STATUS_OPTIONS data. */
export function getStatusText(status: TeamMember['status']): string {
  return STATUS_OPTIONS.find((s) => s.value === status)?.label || '离线'
}

export function getMemberInitial(name: string): string {
  return name ? name.charAt(0) : '?'
}

// ---- Team Members ----

export function getTeamMembers(): TeamMember[] {
  const saved = getStorage<TeamMember[]>(TEAM_KEY)
  if (saved && saved.length > 0) return saved
  setStorage(TEAM_KEY, DEFAULT_TEAM)
  return [...DEFAULT_TEAM]
}

export function saveTeamMembers(members: TeamMember[]): void {
  setStorage(TEAM_KEY, members)
}

// ---- Invitations ----

export function getInvitations(): TeamInvitation[] {
  return getStorage<TeamInvitation[]>(INVITE_KEY) || []
}

function saveInvitations(list: TeamInvitation[]): void {
  setStorage(INVITE_KEY, list)
}

/** 获取待处理的邀请（pending 状态） */
export function getPendingInvitations(): TeamInvitation[] {
  return getInvitations().filter((i) => i.status === 'pending')
}

/** 发送邀请：验证手机号是否已注册，已注册→创建邀请，未注册→拒绝 */
export function inviteMemberByPhone(phone: string): { success: boolean; message: string } {
  if (!phone || phone.length < 11) {
    return { success: false, message: '请输入正确的11位手机号' }
  }

  // 检查是否已在团队中
  const members = getTeamMembers()
  if (members.some((m) => m.phone === phone)) {
    return { success: false, message: '该成员已在团队中' }
  }

  // 检查是否已有 pending 邀请
  const invites = getInvitations()
  if (invites.some((i) => i.phone === phone && i.status === 'pending')) {
    return { success: false, message: '已向该用户发送过邀请，等待对方确认' }
  }

  // 验证是否已注册
  const users = getUsers()
  const user = users.find((u) => u.phone === phone)
  if (!user) {
    return { success: false, message: '该手机号未注册，无法发送邀请' }
  }

  // 创建邀请
  const invitation: TeamInvitation = {
    id: String(Date.now()),
    phone,
    name: user.nickname,
    createdAt: new Date().toISOString(),
    status: 'pending',
  }
  invites.push(invitation)
  saveInvitations(invites)

  return { success: true, message: `已向 ${user.nickname} 发送组队邀请` }
}

/** 接受邀请：将成员加入团队，更新邀请状态 */
export function acceptInvitation(inviteId: string): TeamMember | null {
  const invites = getInvitations()
  const inv = invites.find((i) => i.id === inviteId && i.status === 'pending')
  if (!inv) return null

  inv.status = 'accepted'
  saveInvitations(invites)

  const members = getTeamMembers()
  const newMember: TeamMember = {
    id: String(Date.now()),
    name: inv.name,
    phone: inv.phone,
    avatar: '',
    status: 'online',
    role: 'member',
  }
  members.push(newMember)
  saveTeamMembers(members)

  return newMember
}

/** 拒绝邀请 */
export function rejectInvitation(inviteId: string): void {
  const invites = getInvitations()
  const inv = invites.find((i) => i.id === inviteId)
  if (inv) {
    inv.status = 'rejected'
    saveInvitations(invites)
  }
}

