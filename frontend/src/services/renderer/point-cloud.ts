// ============================================================
// frontend/src/services/renderer/point-cloud.ts
// 3D 渲染：接收后端 MeshData JSON → Three.js BufferGeometry
//
// 设计与用法:
//   导出 addToScene(meshData, sceneMgr) — 点云用 Points, mesh 用 Mesh
//   坐标变换: 后端 Z-up → Three.js Y-up: (x, y, z) → (x, z, -y)
// ============================================================

import * as THREE from 'three'
import type { SceneManager } from './three-scene'

export interface MeshData {
  vertices: number[]
  faces: number[]
  vertex_count: number
  face_count: number
  vertex_colors: number[]
}

/**
 * 添加数据到场景，自动选择渲染模式
 * 坐标变换: (x, y, z) → (x, z, -y)
 */
export function addToScene(data: MeshData, sceneMgr: SceneManager): void {
  if (!data || !data.vertices || data.vertices.length < 3) return

  const rawLen = data.vertices.length / 3
  const cleanV: number[] = []
  const cleanC: number[] = []
  for (let i = 0; i < rawLen; i++) {
    const x = data.vertices[i * 3]
    const y = data.vertices[i * 3 + 1]
    const z = data.vertices[i * 3 + 2]
    if (!isFinite(x) || !isFinite(y) || !isFinite(z)) continue
    cleanV.push(x, z, -y)
    if (data.vertex_colors && data.vertex_colors.length >= (i + 1) * 3) {
      cleanC.push(data.vertex_colors[i * 3], data.vertex_colors[i * 3 + 1], data.vertex_colors[i * 3 + 2])
    }
  }
  if (cleanV.length < 3) return
  const verts = new Float32Array(cleanV)

  const hasFaces = data.faces && data.faces.length > 0

  // 清旧数据
  sceneMgr.cloudGroup.traverse((child) => {
    if (child instanceof THREE.Points || child instanceof THREE.Mesh) {
      child.geometry?.dispose()
      const mats = Array.isArray(child.material) ? child.material : [child.material]
      mats.forEach((m) => (m as THREE.Material).dispose())
    }
  })
  sceneMgr.cloudGroup.clear()

  console.log('[point-cloud] 收到 mesh: verts=%d colors=%d faces=%d',
    data.vertices.length, data.vertex_colors?.length || 0, data.faces?.length || 0)

  if (hasFaces) {
    // === Mesh 模式 ===
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(verts, 3))
    geo.setIndex(new THREE.BufferAttribute(new Uint32Array(data.faces), 1))
    geo.computeVertexNormals()

    const hasVC = cleanC.length > 0
    if (hasVC) {
      geo.setAttribute('color', new THREE.BufferAttribute(new Uint8Array(cleanC), 3, true))
    }

    const matSolid = new THREE.MeshStandardMaterial({
      color: hasVC ? 0xffffff : 0x808080,
      side: THREE.DoubleSide,
      roughness: 0.6,
      metalness: 0.0,
      vertexColors: !!hasVC,
    })
    sceneMgr.cloudGroup.add(new THREE.Mesh(geo, matSolid))

    const matWire = new THREE.MeshBasicMaterial({
      color: 0x666666, wireframe: true,
    })
    sceneMgr.cloudGroup.add(new THREE.Mesh(geo, matWire))
  } else {
    // === 点云模式 ===
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(verts, 3))
    const hasVC = cleanC.length > 0
    if (hasVC) {
      geo.setAttribute('color', new THREE.BufferAttribute(new Uint8Array(cleanC), 3, true))
    }
    console.log('[point-cloud] 渲染: cleanV=%d cleanC=%d hasVC=%s',
      cleanV.length, cleanC.length, hasVC)
    const mat = new THREE.PointsMaterial({
      color: hasVC ? 0xffffff : 0xaaaaaa,
      size: 0.015,
      vertexColors: !!hasVC,
    })
    sceneMgr.cloudGroup.add(new THREE.Points(geo, mat))
  }
}
