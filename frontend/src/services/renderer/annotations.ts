// ============================================================
// frontend/src/services/renderer/annotations.ts
// 3D 缺陷标注：按类型着色球体，固定大小
//
// 设计与用法:
//   导出 CRACK_COLORS — 缺陷类型 → 颜色映射
//   导出 addCracks(cracks, sceneMgr) — 渲染标注球
//   导出 clearCracks(sceneMgr) — 清理标注
// ============================================================

import * as THREE from 'three'
import type { SceneManager } from './three-scene'
import type { DetectionItem } from '@/types/api'

/** 缺陷类型 → 颜色 */
export const CRACK_COLORS: Record<string, number> = {
  '裂缝': 0xef5350,
  'crack': 0xef5350,
  '渗水': 0x42a5f5,
  '渗漏': 0x42a5f5,
  'leakage': 0x42a5f5,
  '剥落': 0xffa726,
  'spalling': 0xffa726,
}

const DEFAULT_COLOR = 0xffa726
const SPHERE_SIZE = 0.04
const SPHERE_SEGMENTS = 8

let _lastCrackHash = ''

/**
 * 添加缺陷标注球体
 *
 * cracks: API 返回的检测结果，需带 center_3d 字段
 * 坐标变换: 后端 Z-up → Three.js Y-up: (x, y, z) → (x, z, -y)
 */
export function addCracks(
  cracks: DetectionItem[],
  sceneMgr: SceneManager,
): void {
  // 数据未变则跳过，避免每轮轮询裂缝球闪烁
  const hash = JSON.stringify(cracks.map(c => [c.id, c.class_name, c.confidence, c.center_3d]))
  if (hash === _lastCrackHash) return
  _lastCrackHash = hash

  clearCracks(sceneMgr)
  if (!cracks || cracks.length === 0) return

  for (const c of cracks) {
    const center = c.center_3d
    if (!center || center.length < 3 || (center[0] === 0 && center[1] === 0 && center[2] === 0)) {
      continue // 无有效 3D 位置，跳过
    }

    const color = CRACK_COLORS[c.class_name] ?? DEFAULT_COLOR
    const geo = new THREE.SphereGeometry(SPHERE_SIZE, SPHERE_SEGMENTS, SPHERE_SEGMENTS)
    const mat = new THREE.MeshBasicMaterial({ color })
    const sphere = new THREE.Mesh(geo, mat)

    // (x, y, z) → (x, z, -y)
    sphere.position.set(center[0], center[2], -center[1])
    sceneMgr.crackGroup.add(sphere)
  }
}

/** 清理所有缺陷标注 */
export function clearCracks(sceneMgr: SceneManager): void {
  sceneMgr.crackGroup.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      child.geometry?.dispose()
      if (Array.isArray(child.material)) {
        child.material.forEach((m) => m.dispose())
      } else {
        child.material?.dispose()
      }
    }
  })
  sceneMgr.crackGroup.clear()
}
