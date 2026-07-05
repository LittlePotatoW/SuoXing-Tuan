// ============================================================
// frontend/src/constants/colors.ts
// 全局颜色常量 — 所有颜色集中管理，禁止在组件中写死颜色值
// ============================================================

/**
 * 全局颜色常量
 * 所有涉及颜色的地方统一从此文件引用，禁止在组件中写死颜色值
 */

// ==================== 检测框颜色（按缺陷类别） ====================
// 每个缺陷类别对应一个颜色，检测时用类别名索引
export const DETECTION_COLORS: Record<string, string> = {
  scratch:      '#FF4444', // 划痕 — 红色
  dent:         '#44AAFF', // 凹陷 — 蓝色
  crack:        '#FFAA00', // 裂纹 — 橙色
  stain:        '#AA44FF', // 污渍 — 紫色
  deformation:  '#44FFAA', // 变形 — 青色
  default:      '#FF4444', // 未知缺陷 — 默认红色
}

// ==================== Mask 叠加色 ====================
export const MASK_OVERLAY_COLOR = '#FF0000'    // mask 区域填充色
export const MASK_OVERLAY_ALPHA = 0.35          // mask 透明度 (0~1)

// ==================== UI 背景色 ====================
export const BG_PRIMARY    = '#1A1A1A'  // 主背景（深色）
export const BG_SECONDARY  = '#2D2D2D'  // 次级背景（面板）
export const BG_TERTIARY   = '#3D3D3D'  // 三级背景（输入框、卡片）

// ==================== UI 文字色 ====================
export const TEXT_PRIMARY   = '#E0E0E0'  // 主文字
export const TEXT_SECONDARY = '#A0A0A0'  // 次要文字（标签、说明）
export const TEXT_ACCENT    = '#4FC3F7'  // 强调文字（数值、链接）

// ==================== UI 边框色 ====================
export const BORDER_DEFAULT = '#555555'  // 默认边框
export const BORDER_ACTIVE  = '#4FC3F7'  // 激活/聚焦边框
export const BORDER_ERROR   = '#FF4444'  // 错误状态边框

// ==================== 状态指示色 ====================
export const STATUS_ONLINE   = '#4CAF50'  // 已连接 / 就绪 — 绿色
export const STATUS_OFFLINE  = '#FF4444'  // 未连接 / 错误 — 红色
export const STATUS_LOADING  = '#FFAA00'  // 加载中 / 推理中 — 橙色
export const STATUS_IDLE     = '#A0A0A0'  // 空闲 — 灰色

// ==================== 拖拽区域 ====================
export const DROPZONE_BG         = '#2A2A2A'  // 拖拽区背景
export const DROPZONE_BG_HOVER   = '#3A3A3A'  // 拖拽悬停时背景
export const DROPZONE_BORDER     = '#555555'  // 拖拽区边框
export const DROPZONE_BORDER_HOVER = '#4FC3F7' // 拖拽悬停时边框

// ==================== 按钮色 ====================
export const BTN_PRIMARY_BG   = '#4FC3F7'  // 主按钮背景
export const BTN_PRIMARY_TEXT = '#1A1A1A'  // 主按钮文字
export const BTN_DANGER_BG    = '#FF4444'  // 危险按钮背景
export const BTN_DANGER_TEXT  = '#FFFFFF'  // 危险按钮文字
