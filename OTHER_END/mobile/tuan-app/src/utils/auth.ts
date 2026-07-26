/**
 * Auth composable — shared reactive login state (module-level singleton).
 *
 * Usage:
 *   const { isLoggedIn, login, register, logout, checkAuth, isLoading } = useAuth()
 *
 * All callers share the same refs — no need for Pinia at this scale.
 */

import { ref, computed } from 'vue'
import { getToken, setToken, removeToken } from './storage'
import { verifyLogin, registerUser } from './userStore'

// ---- module-level singleton state ----
const SIMULATED_LATENCY_MS = 400

function simulateLatency(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, SIMULATED_LATENCY_MS + Math.random() * SIMULATED_LATENCY_MS))
}

const token = ref<string | null>(getToken())
const isLoading = ref(false)

/** Extract phone from token (format: token-138xxxx1234-timestamp) */
function getPhoneFromToken(): string {
  const t = token.value || ''
  const parts = t.split('-')
  return parts.length >= 2 ? parts[1] : ''
}

export function useAuth() {
  const isLoggedIn = computed(() => !!token.value)
  const currentPhone = computed(() => getPhoneFromToken())

  /**
   * Login — verifies credentials against locally stored users.
   * Simulates a 400–800ms network round-trip.
   */
  async function login(
    phone: string,
    password: string,
  ): Promise<{ success: boolean; message: string }> {
    isLoading.value = true
    try {
      await simulateLatency()

      const result = verifyLogin(phone, password)

      if (result.success) {
        const loginToken = 'token-' + phone + '-' + Date.now()
        token.value = loginToken
        setToken(loginToken)
      }

      return result
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Register a new account.
   */
  async function register(
    phone: string,
    password: string,
  ): Promise<{ success: boolean; message: string }> {
    isLoading.value = true
    try {
      await simulateLatency()
      return registerUser(phone, password)
    } finally {
      isLoading.value = false
    }
  }

  /** Clear token and navigate to login. */
  function logout(): void {
    token.value = null
    removeToken()
    uni.reLaunch({ url: '/pages/login/index' })
  }

  /**
   * Called by App.vue onLaunch.
   * Returns true if a valid token already exists in storage (auto-login).
   */
  function checkAuth(): boolean {
    const stored = getToken()
    if (stored) {
      token.value = stored
      return true
    }
    return false
  }

  return {
    token,
    isLoggedIn,
    isLoading,
    currentPhone,
    login,
    register,
    logout,
    checkAuth,
  }
}
