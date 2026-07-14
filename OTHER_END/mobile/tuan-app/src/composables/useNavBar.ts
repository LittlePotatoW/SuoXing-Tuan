import { ref, computed, onMounted } from 'vue'

/**
 * 统一导航栏测量逻辑（IBM Carbon 风格）
 * 自动适配微信小程序胶囊按钮，返回导航栏各尺寸引用。
 *
 * 用法：
 *   const { statusBarH, navH, navPad, navTotalH } = useNavBar()
 *
 * 模板中：
 *   <view class="nav-bar" :style="{ paddingTop: statusBarH + 'px' }">
 *     <view class="nav-inner" :style="{ height: navH + 'px', paddingRight: navPad + 'px' }">
 */

const DEFAULT_NAV_H = 44
const DEFAULT_NAV_PAD = 100
const NAV_BOTTOM_GAP = 8
const FALLBACK_STATUS_BAR_H = 20
const FALLBACK_WINDOW_W = 375
const CAPSULE_EXTRA_PAD = 12
const MIN_NAV_PAD = 90

export function useNavBar() {
  const statusBarH = ref(0)
  const navH = ref(DEFAULT_NAV_H)
  const navPad = ref(DEFAULT_NAV_PAD)
  const navTotalH = computed(() => statusBarH.value + navH.value + NAV_BOTTOM_GAP)

  onMounted(() => {
    const sys = uni.getSystemInfoSync()
    statusBarH.value = sys.statusBarHeight || FALLBACK_STATUS_BAR_H

    // #ifdef MP-WEIXIN
    try {
      const mb = uni.getMenuButtonBoundingClientRect()
      navH.value = (mb.bottom - statusBarH.value) + (mb.height / 2)
      navPad.value = Math.max((sys.windowWidth || FALLBACK_WINDOW_W) - mb.left + CAPSULE_EXTRA_PAD, MIN_NAV_PAD)
    } catch (e) {
      navH.value = DEFAULT_NAV_H
      navPad.value = DEFAULT_NAV_PAD
    }
    // #endif
  })

  return { statusBarH, navH, navPad, navTotalH }
}
