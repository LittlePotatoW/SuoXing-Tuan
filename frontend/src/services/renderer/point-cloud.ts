// ============================================================
// frontend/src/services/renderer/point-cloud.ts
// 点云 / Mesh 渲染：PLY 解析 + 自适应渲染
//
// 设计与用法:
//   导出 parsePlyText(text) → { vertices, faces | null }
//   导出 fetchAndParsePly(url) → Promise<PlyData>
//   导出 addToScene(plyData, sceneMgr) — 点云用 Points, mesh 用 Mesh
// ============================================================

import * as THREE from 'three'
import { httpClient } from '@/network/http-client'
import type { SceneManager } from './three-scene'

export interface PlyData {
  vertices: Float32Array   // 扁平 [x,y,z, ...], N*3
  faces: Uint32Array | null // 扁平 [v1,v2,v3, ...], M*3, 点云模式为 null
}

/** 解析 PLY 文件，自动识别点云或 mesh */
export function parsePlyText(text: string): PlyData {
  const lines = text.split('\n')

  let vertexCount = 0
  let faceCount = 0
  let inHeader = true

  const verts: number[] = []
  const faces: number[] = []

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) continue

    if (inHeader) {
      if (trimmed.startsWith('element vertex')) {
        vertexCount = parseInt(trimmed.split(/\s+/)[2], 10)
      }
      if (trimmed.startsWith('element face')) {
        faceCount = parseInt(trimmed.split(/\s+/)[2], 10)
      }
      if (trimmed === 'end_header') {
        inHeader = false
      }
      continue
    }

    // body: 顶点在前, 面在后
    if (verts.length / 3 < vertexCount) {
      const parts = trimmed.split(/\s+/)
      if (parts.length >= 3) {
        verts.push(parseFloat(parts[0]), parseFloat(parts[1]), parseFloat(parts[2]))
      }
    } else if (faceCount > 0 && faces.length / 3 < faceCount) {
      const parts = trimmed.split(/\s+/)
      // PLY face 格式: "3 v1 v2 v3" 或 "4 v1 v2 v3 v4"
      const count = parseInt(parts[0], 10)
      if (count >= 3) {
        // 三角剖分四边形
        faces.push(parseInt(parts[1]), parseInt(parts[2]), parseInt(parts[3]))
        if (count === 4) {
          faces.push(parseInt(parts[1]), parseInt(parts[3]), parseInt(parts[4]))
        }
      }
    }
  }

  return {
    vertices: new Float32Array(verts),
    faces: faces.length > 0 ? new Uint32Array(faces) : null,
  }
}

/** fetch PLY 文件并解析 */
export async function fetchAndParsePly(url: string): Promise<PlyData> {
  const fullUrl = url.startsWith('http') ? url : (httpClient.defaults.baseURL ?? '') + url
  const resp = await fetch(fullUrl)
  if (!resp.ok) throw new Error(`PLY fetch failed: ${resp.status}`)
  const text = await resp.text()
  return parsePlyText(text)
}

/**
 * 添加数据到场景，自动选择渲染模式:
 *   mesh (有 faces) → indexed BufferGeometry + MeshStandardMaterial + wireframe
 *   点云 (无 faces) → Points
 *
 * 坐标变换: (x, y, z) → (x, z, -y)
 */
export function addToScene(ply: PlyData, sceneMgr: SceneManager): void {
  // 清旧数据
  sceneMgr.cloudGroup.traverse((child) => {
    if (child instanceof THREE.Points || child instanceof THREE.Mesh) {
      child.geometry?.dispose()
      const mats = Array.isArray(child.material) ? child.material : [child.material]
      mats.forEach((m) => (m as THREE.Material).dispose())
    }
  })
  sceneMgr.cloudGroup.clear()

  // 坐标变换
  const verts = new Float32Array(ply.vertices.length)
  for (let i = 0; i < ply.vertices.length; i += 3) {
    verts[i]     = ply.vertices[i]
    verts[i + 1] = ply.vertices[i + 2]
    verts[i + 2] = -ply.vertices[i + 1]
  }

  if (ply.faces && ply.faces.length > 0) {
    // === Mesh 模式 ===
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(verts, 3))
    geo.setIndex(new THREE.BufferAttribute(ply.faces, 1))
    geo.computeVertexNormals()

    const matSolid = new THREE.MeshStandardMaterial({
      color: 0x4fc3f7, side: THREE.DoubleSide, flatShading: true,
    })
    const mesh = new THREE.Mesh(geo, matSolid)
    sceneMgr.cloudGroup.add(mesh)

    // 线框覆盖层
    const matWire = new THREE.MeshBasicMaterial({
      color: 0x1a1a2e, wireframe: true,
    })
    const wire = new THREE.Mesh(geo, matWire)
    sceneMgr.cloudGroup.add(wire)
  } else {
    // === 点云模式 ===
    const geo = new THREE.BufferGeometry()
    geo.setAttribute('position', new THREE.BufferAttribute(verts, 3))
    const mat = new THREE.PointsMaterial({ color: 0xaaaaaa, size: 0.015 })
    const cloud = new THREE.Points(geo, mat)
    sceneMgr.cloudGroup.add(cloud)
  }
}
