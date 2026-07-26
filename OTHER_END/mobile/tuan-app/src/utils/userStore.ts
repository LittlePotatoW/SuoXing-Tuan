/**
 * Local user store — persists registered users in uni.storage.
 * In production, this would be replaced by a real backend API.
 */

import { getStorage, setStorage } from './storage'

export interface StoredUser {
  phone: string
  password: string // In production, never store plain-text passwords
  nickname: string
  createdAt: string
}

const USERS_KEY = 'registered_users'

/** Get all registered users from local storage. */
export function getUsers(): StoredUser[] {
  return getStorage<StoredUser[]>(USERS_KEY) || []
}

/** Save the full user list. */
function saveUsers(users: StoredUser[]): void {
  setStorage(USERS_KEY, users)
}

/**
 * Register a new user.
 * Returns { success, message }
 */
export function registerUser(
  phone: string,
  password: string,
): { success: boolean; message: string } {
  // Validate
  if (!phone || phone.length < 11) {
    return { success: false, message: '请输入正确的11位手机号' }
  }
  if (!password || password.length < 6) {
    return { success: false, message: '密码至少需要6位' }
  }

  const users = getUsers()

  if (users.some((u) => u.phone === phone)) {
    return { success: false, message: '该手机号已注册，请直接登录' }
  }

  const newUser: StoredUser = {
    phone,
    password, // Demo only — real apps must hash passwords
    nickname: `用户${phone.slice(-4)}`,
    createdAt: new Date().toISOString(),
  }

  users.push(newUser)
  saveUsers(users)
  return { success: true, message: '注册成功，请登录' }
}

/**
 * Verify login credentials against stored users.
 * Returns { success, message }
 */
export function verifyLogin(
  phone: string,
  password: string,
): { success: boolean; message: string } {
  if (!phone || !password) {
    return { success: false, message: '请输入手机号和密码' }
  }

  const users = getUsers()
  const user = users.find((u) => u.phone === phone)

  if (!user) {
    return { success: false, message: '该手机号未注册，请先注册' }
  }
  if (user.password !== password) {
    return { success: false, message: '密码错误，请重试' }
  }

  return { success: true, message: '登录成功' }
}
