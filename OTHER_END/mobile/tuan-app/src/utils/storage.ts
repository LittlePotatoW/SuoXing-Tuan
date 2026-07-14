/**
 * Storage utility — typed wrappers around uni.storage APIs.
 * Centralizes all storage keys so they are never duplicated as string literals.
 */

export const STORAGE_KEYS = {
  TOKEN: 'token',
  USER_INFO: 'userInfo',
} as const

/** Get the stored auth token, or null if absent / empty. */
export function getToken(): string | null {
  const val = uni.getStorageSync(STORAGE_KEYS.TOKEN)
  return val ? String(val) : null
}

export function setToken(token: string): void {
  uni.setStorageSync(STORAGE_KEYS.TOKEN, token)
}

export function removeToken(): void {
  uni.removeStorageSync(STORAGE_KEYS.TOKEN)
}

/** Generic typed getter — returns null when the key is missing, undefined, or empty string. */
export function getStorage<T = unknown>(key: string): T | null {
  const val = uni.getStorageSync(key)
  if (val === '' || val === undefined || val === null) return null
  return val as T
}

export function setStorage(key: string, value: unknown): void {
  uni.setStorageSync(key, value)
}

export function removeStorage(key: string): void {
  uni.removeStorageSync(key)
}
