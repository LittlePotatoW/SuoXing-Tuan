// ============================================================
// frontend/src/services/renderer/point-cloud.ts
// 点云渲染：PLY 解析 + BufferGeometry + THREE.Points
//
// 设计与用法:
//   导出 parsePlyText(text) → Float32Array [x,y,z,...]
//   导出 fetchAndParsePly(url) → Promise<Float32Array>
//   导出 createPointCloud(points, sceneMgr) — 坐标变换+渲染
// ============================================================

import * as THREE from 'three'
import type { SceneManager } from './three-scene'

/** 解析 ASCII PLY 文件, 返回扁平 Float32Array [x,y,z, x,y,z, ...] */
export function parsePlyText(text: string): Float32Array {
  const lines = text.split('\n')
  let vertexCount = 0
  let inHeader = true
  const points: number[] = []

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue
    if (inHeader) {
      if (trimmed.startsWith('element vertex')) {
        vertexCount = parseInt(trimmed.split(/\s+/)[2], 10)
      }
      if (trimmed === 'end_header') {
        inHeader = false
      }
      continue
    }
    const parts = trimmed.split(/\s+/)
    if (parts.length >= 3) {
      points.push(parseFloat(parts[0]), parseFloat(parts[1]), parseFloat(parts[2]))
    }
  }

  return new Float32Array(points)
}

/** fetch PLY 文件并解析 */
export async function fetchAndParsePly(url: string): Promise<Float32Array> {
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`PLY fetch failed: ${resp.status}`)
  const text = await resp.text()
  return parsePlyText(text)
}

/**
 * 创建点云 THREE.Points 并加入 sceneManager.cloudGroup
 *
 * 坐标变换: 后端 Z-up (X前 Y左 Z上) → Three.js Y-up (X右 Y上 Z前)
 *   (x, y, z) → (x, z, -y)
 */
export function createPointCloud(
  points: Float32Array,
  sceneMgr: SceneManager,
  color = 0x4fc3f7,
  size = 0.015,
): THREE.Points {
  // 清旧点云
  sceneMgr.cloudGroup.traverse((child) => {
    if (child instanceof THREE.Points) {
      child.geometry?.dispose()
      if (Array.isArray(child.material)) {
        child.material.forEach((m) => m.dispose())
      } else {
        child.material?.dispose()
      }
    }
  })
  sceneMgr.cloudGroup.clear()

  // 坐标变换: (x, y, z) → (x, z, -y)
  const verts = new Float32Array(points.length)
  for (let i = 0; i < points.length; i += 3) {
    verts[i]     = points[i]         // X → X
    verts[i + 1] = points[i + 2]     // Z → Y (up)
    verts[i + 2] = -points[i + 1]    // Y → -Z (水平)
  }

  const geo = new THREE.BufferGeometry()
  geo.setAttribute('position', new THREE.BufferAttribute(verts, 3))

  const mat = new THREE.PointsMaterial({ color, size })
  const cloud = new THREE.Points(geo, mat)
  sceneMgr.cloudGroup.add(cloud)
  return cloud
}
